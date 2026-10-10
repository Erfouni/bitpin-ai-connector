import asyncio
import base64
import hashlib
import json
import re
import secrets
import time
from decimal import Decimal

import httpx

from .config import Settings
from .storage import Store

AUTH = "/api/v1/usr/authenticate/"
REFRESH = "/api/v1/usr/refresh_token/"
ORDERS = "/api/v1/odr/orders/"
READ_PATHS = re.compile(
    r"^/api/(?:v1/(?:mkt/(?:markets|tickers|currencies|commissions|candles)/|mth/(?:orderbook|matches)/[A-Z0-9]+_[A-Z0-9]+/|wlt/wallets/|odr/(?:orders/(?:[0-9]+/)?|fills/|order_history/))|v2/wlt/networks/)$"
)
CANCEL_PATHS = re.compile(r"^/api/v1/odr/orders/(?:[0-9]+|identifier/[A-Za-z0-9_-]{1,64})/$")


class BitpinError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class UnknownOutcome(BitpinError):
    pass


def expiry(token: str, fallback: int) -> float:
    now = time.time()
    try:
        part = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        return now + min(float(claims["exp"]) - float(claims["iat"]), fallback)
    except (ValueError, KeyError, IndexError, TypeError):
        return now + fallback


class BitpinClient:
    def __init__(self, settings: Settings, store: Store, transport=None):
        self.settings, self.store = settings, store
        self.account = store.journal_namespace()
        self.auth_key = hashlib.sha256(
            json.dumps(
                [
                    settings.bitpin_base_url,
                    settings.bitpin_api_key.get_secret_value(),
                    settings.bitpin_secret_key.get_secret_value(),
                ]
            ).encode()
        ).hexdigest()
        self.http = httpx.AsyncClient(
            base_url=settings.bitpin_base_url,
            timeout=settings.request_timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"User-Agent": "bitpin-ai-connector/0.1"},
        )
        self.auth_lock = asyncio.Lock()
        self._cache: dict[str, tuple[float, object]] = {}

    async def close(self):
        await self.http.aclose()

    async def _wire(self, method, path, *, params=None, body=None, token=None):
        try:
            response = await self.http.request(
                method,
                path,
                params=params,
                json=body,
                headers={"Authorization": f"Bearer {token}"} if token else {},
            )
        except httpx.HTTPError:
            error = (
                UnknownOutcome
                if method in {"POST", "DELETE"} and path not in {AUTH, REFRESH}
                else BitpinError
            )
            raise error("Bitpin connection failed; a write may already have reached the exchange") from None
        if response.status_code == 204:
            return response.status_code, None, response.headers
        try:
            data = json.loads(response.content, parse_float=Decimal)
        except (ValueError, UnicodeError):
            data = None
        return response.status_code, data, response.headers

    async def token(self, invalidate: str | None = None) -> str:
        async with self.auth_lock:
            owner = secrets.token_hex(16)
            lease_seconds = 2 * self.settings.request_timeout + 10
            deadline = time.monotonic() + lease_seconds
            while not self.store.acquire_lease(self.account, owner, lease_seconds):
                if time.monotonic() >= deadline:
                    raise BitpinError("Another Bitpin authentication is in progress; retry shortly")
                await asyncio.sleep(0.1)
            try:
                return await self._token_locked(invalidate)
            finally:
                self.store.release_lease(self.account, owner)

    async def _token_locked(self, invalidate):
        now = time.time()
        cached = self.store.get("bitpin", self.auth_key) or {}
        if cached.get("access_exp", 0) > now + 60 and cached.get("access") != invalidate:
            return cached["access"]
        cooldown = self.store.get("bitpin-cooldown", self.account) or {}
        if now < cooldown.get("until", 0):
            raise BitpinError("Bitpin authentication temporarily unavailable; retry after cooldown")
        if (
            not self.settings.bitpin_api_key.get_secret_value()
            or not self.settings.bitpin_secret_key.get_secret_value()
        ):
            raise BitpinError("Configure BITPIN_API_KEY and BITPIN_SECRET_KEY on the server")
        try:
            if cached.get("refresh") and cached.get("refresh_exp", 0) > now + 60:
                path, body = REFRESH, {"refresh": cached["refresh"]}
            else:
                path, body = (
                    AUTH,
                    {
                        "api_key": self.settings.bitpin_api_key.get_secret_value(),
                        "secret_key": self.settings.bitpin_secret_key.get_secret_value(),
                    },
                )
            for _ in range(2):
                if not self.store.limit("bitpin-auth:" + self.account, 150, 86400):
                    raise BitpinError(
                        "Daily authentication budget reached; wait for the rolling 24-hour window"
                    )
                try:
                    status, data, _headers = await asyncio.wait_for(
                        self._wire("POST", path, body=body), timeout=self.settings.request_timeout
                    )
                except TimeoutError:
                    raise BitpinError("Bitpin authentication timed out") from None
                if path == REFRESH and 400 <= status < 500 and status != 429:
                    cached = {}
                    path, body = (
                        AUTH,
                        {
                            "api_key": self.settings.bitpin_api_key.get_secret_value(),
                            "secret_key": self.settings.bitpin_secret_key.get_secret_value(),
                        },
                    )
                    continue
                if (
                    not 200 <= status < 300
                    or not isinstance(data, dict)
                    or not isinstance(data.get("access"), str)
                ):
                    raise BitpinError(
                        f"Bitpin authentication failed (HTTP {status}); check keys and server IP allowlist",
                        status,
                    )
                cached.update(access=data["access"], access_exp=expiry(data["access"], 900))
                if data.get("refresh"):
                    cached.update(refresh=data["refresh"], refresh_exp=expiry(data["refresh"], 604800))
                self.store.put("bitpin", self.auth_key, cached, now + 604800)
                self.store.pop("bitpin-cooldown", self.account)
                return cached["access"]
            raise BitpinError("Bitpin authentication failed")
        except BitpinError:
            delay = cooldown.get("delay", 30)
            self.store.put(
                "bitpin-cooldown",
                self.account,
                {"until": time.time() + delay, "delay": min(delay * 2, 1800)},
                time.time() + 86400,
            )
            raise

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        body: dict | None = None,
        private: bool = False,
    ):
        allowed = (
            (method == "GET" and READ_PATHS.fullmatch(path))
            or (method == "POST" and path == ORDERS)
            or (method == "DELETE" and CANCEL_PATHS.fullmatch(path))
        )
        if not allowed:
            raise BitpinError("Endpoint is not allowed by this connector")
        if method != "GET" and not private:
            raise BitpinError("Private authentication is required for writes")
        params = {k: v for k, v in (params or {}).items() if v is not None}
        token = await self.token() if private else None
        for attempt in range(3 if method == "GET" else 1):
            try:
                status, data, headers = await self._wire(method, path, params=params, body=body, token=token)
            except BitpinError:
                if method != "GET" or attempt == 2:
                    raise
                await asyncio.sleep(0.25 * 2**attempt)
                continue
            if 200 <= status < 300:
                if status != 204 and data is None:
                    if method != "GET":
                        raise UnknownOutcome(
                            "Bitpin returned an unreadable write response; reconcile before doing anything else"
                        )
                    raise BitpinError("Bitpin returned an unreadable response")
                return data
            if method != "GET" and (status >= 500 or 300 <= status < 400):
                raise UnknownOutcome(f"Bitpin write outcome unknown (HTTP {status}); do not resubmit")
            if method == "GET" and status == 401 and private and attempt < 2:
                token = await self.token(invalidate=token)
                continue
            if method == "GET" and (status == 429 or status >= 500) and attempt < 2:
                try:
                    delay = min(max(float(headers.get("Retry-After", "1")), 0.25), 5)
                except ValueError:
                    delay = 1
                await asyncio.sleep(delay)
                continue
            # Never reflect an upstream body: it can contain keys or arbitrary HTML/instructions.
            hints = {
                401: "authentication expired",
                403: "access denied or IP not allowed",
                406: "exchange rejected the parameters or action",
                429: "rate limit reached",
            }
            raise BitpinError(f"Bitpin HTTP {status}: {hints.get(status, 'request failed')}", status)
        raise BitpinError("Bitpin read failed after bounded retries")

    async def markets(self) -> list[dict]:
        cached = self._cache.get("markets")
        if cached and cached[0] > time.time():
            return cached[1]
        result = await self.request("GET", "/api/v1/mkt/markets/")
        if not isinstance(result, list):
            raise BitpinError("Unexpected market response")
        self._cache["markets"] = (time.time() + 30, result)
        return result

    async def find_order(self, identifier: str) -> dict | None:
        rows = await self.request(
            "GET", ORDERS, params={"identifier": identifier, "limit": 100}, private=True
        )
        if not isinstance(rows, list):
            raise BitpinError("Unexpected order-list response")
        matches = [r for r in rows if isinstance(r, dict) and r.get("identifier") == identifier]
        if len(matches) > 1:
            raise BitpinError("More than one order has this identifier; inspect the account manually")
        return matches[0] if matches else None
