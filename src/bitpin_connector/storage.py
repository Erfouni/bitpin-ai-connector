import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class Store:
    """Durable, atomic single-account grants and account-scoped idempotency receipts."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS kv (kind TEXT, key TEXT, value TEXT NOT NULL,
                  expires REAL NOT NULL, PRIMARY KEY(kind,key));
                CREATE TABLE IF NOT EXISTS orders (account TEXT, identifier TEXT, payload TEXT NOT NULL,
                  status TEXT NOT NULL, result TEXT, updated REAL NOT NULL, PRIMARY KEY(account,identifier));
                CREATE TABLE IF NOT EXISTS events (kind TEXT, at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS events_idx ON events(kind,at);
            """)
        os.chmod(path, 0o600)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def key(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def put(self, kind: str, key: str, value: dict, expires: float):
        with self.connection() as db:
            db.execute(
                "INSERT OR REPLACE INTO kv VALUES(?,?,?,?)", (kind, self.key(key), encode(value), expires)
            )

    def get(self, kind: str, key: str) -> dict | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT value FROM kv WHERE kind=? AND key=? AND expires>?",
                (kind, self.key(key), time.time()),
            ).fetchone()
            return json.loads(row[0]) if row else None

    def pop(self, kind: str, key: str) -> dict | None:
        with self.connection() as db:
            row = db.execute(
                "DELETE FROM kv WHERE kind=? AND key=? RETURNING value, expires", (kind, self.key(key))
            ).fetchone()
            return json.loads(row[0]) if row and row[1] > time.time() else None

    def journal_namespace(self) -> str:
        """One account per data directory; credential rotation never resets receipts."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            key = self.key("account")
            db.execute(
                "INSERT OR IGNORE INTO kv VALUES(?,?,?,?)",
                ("deployment", key, encode({"id": secrets.token_hex(24)}), 1e12),
            )
            row = db.execute("SELECT value FROM kv WHERE kind='deployment' AND key=?", (key,)).fetchone()
            return json.loads(row[0])["id"]

    def acquire_lease(self, key: str, owner: str, seconds: float) -> bool:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            digest, now = self.key(key), time.time()
            db.execute("DELETE FROM kv WHERE kind='lease' AND key=? AND expires<=?", (digest, now))
            return (
                db.execute(
                    "INSERT OR IGNORE INTO kv VALUES('lease',?,?,?)",
                    (digest, encode({"owner": owner}), now + seconds),
                ).rowcount
                == 1
            )

    def release_lease(self, key: str, owner: str):
        with self.connection() as db:
            db.execute(
                "DELETE FROM kv WHERE kind='lease' AND key=? AND value=?",
                (self.key(key), encode({"owner": owner})),
            )

    def consume_refresh(self, token: str, client_id: str) -> dict | None:
        """Move to a spent-token tombstone in the same transaction as consumption."""
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            key = self.key(token)
            row = db.execute(
                "SELECT value,expires FROM kv WHERE kind='oauth-refresh' AND key=?", (key,)
            ).fetchone()
            if not row or row[1] <= time.time():
                return None
            value = json.loads(row[0])
            if value["client_id"] != client_id:
                return None
            db.execute("DELETE FROM kv WHERE kind='oauth-refresh' AND key=?", (key,))
            db.execute("INSERT OR REPLACE INTO kv VALUES('oauth-spent',?,?,?)", (key, row[0], row[1]))
            return value

    def limit(self, kind: str, maximum: int, window: float) -> bool:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            now = time.time()
            db.execute("DELETE FROM events WHERE at<?", (now - max(window, 86400),))
            count = db.execute(
                "SELECT count(*) FROM events WHERE kind=? AND at>?", (kind, now - window)
            ).fetchone()[0]
            if count >= maximum:
                return False
            db.execute("INSERT INTO events VALUES(?,?)", (kind, now))
            return True

    def reserve(self, account: str, identifier: str, payload: dict) -> bool:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT payload FROM orders WHERE account=? AND identifier=?", (account, identifier)
            ).fetchone()
            if old:
                if old[0] != encode(payload):
                    raise ValueError("Identifier already belongs to a different order payload")
                return False
            db.execute(
                "INSERT INTO orders VALUES(?,?,?,'pending',NULL,?)",
                (account, identifier, encode(payload), time.time()),
            )
            return True

    def finish(self, account: str, identifier: str, status: str, result: dict):
        with self.connection() as db:
            db.execute(
                "UPDATE orders SET status=?,result=?,updated=? WHERE account=? AND identifier=?",
                (status, encode(result), time.time(), account, identifier),
            )

    def receipt(self, account: str, identifier: str) -> dict | None:
        with self.connection() as db:
            row = db.execute(
                "SELECT identifier,payload,status,result,updated FROM orders WHERE account=? AND identifier=?",
                (account, identifier),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        result["result"] = json.loads(result["result"]) if result["result"] else None
        return result
