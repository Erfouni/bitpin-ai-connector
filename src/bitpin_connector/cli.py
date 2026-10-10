import argparse
import asyncio
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn

from .client import BitpinClient, BitpinError
from .config import Settings
from .network import print_public_ips, public_ips
from .server import create_server, http_app
from .storage import Store


def load_settings() -> Settings:
    values = {}
    raw = Path(".secrets.env")
    if raw.exists():
        for line in raw.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                key, sep, value = line.partition("=")
                if not sep:
                    raise ValueError("Invalid raw secrets file")
                if key not in os.environ:
                    values[key.lower()] = value
    return Settings(**values)


async def doctor(settings, private):
    client = BitpinClient(settings, Store(settings.data_dir / "connector.sqlite3"))
    try:
        markets = await client.markets()
        print(json.dumps({"public_api": "ok", "markets": len(markets)}, ensure_ascii=False))
        if private:
            rows = await client.request(
                "GET", "/api/v1/wlt/wallets/", private=True, params={"limit": 1, "service": "main"}
            )
            print(json.dumps({"private_api": "ok", "wallet_endpoint_responded": isinstance(rows, list)}))
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(description="Bitpin AI Connector")
    parser.add_argument(
        "--directory",
        type=Path,
        help="Configuration working directory (use an absolute path in desktop clients)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start MCP transport")
    serve.add_argument("--transport", choices=["stdio", "http"], default="http")
    check = commands.add_parser("doctor", help="Read-only Bitpin connectivity check")
    check.add_argument(
        "--private",
        action="store_true",
        help="Also authenticate and check wallet access without printing balances",
    )
    commands.add_parser(
        "revoke-sessions", help="Revoke all connector OAuth sessions; API bearer key is separate"
    )
    commands.add_parser(
        "url", help="Print the connector URL privately in this terminal; treat it as a password"
    )
    commands.add_parser(
        "check-https", help="Check domain routing, TLS certificate and public health endpoint"
    )
    commands.add_parser("ip", help="Show public outbound IPv4/IPv6 for the Bitpin API IP allowlist")
    args = parser.parse_args()
    if args.directory:
        os.chdir(args.directory)
    logging.basicConfig(
        stream=sys.stderr, level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        settings = load_settings()
        if args.command == "ip":
            print_public_ips(asyncio.run(public_ips()))
        elif args.command == "url":
            print(settings.resource_url)
        elif args.command == "check-https":
            for attempt in range(12):
                try:
                    with urllib.request.urlopen(settings.public_url + "/healthz", timeout=5) as response:
                        result = json.load(response)
                    if result.get("status") != "ok" or "version" not in result:
                        raise ValueError("Unexpected health response")
                    print("Public HTTPS and connector health verified.")
                    break
                except (OSError, ValueError, urllib.error.URLError):
                    if attempt == 11:
                        raise BitpinError(
                            "HTTPS verification failed. Check DNS A/AAAA, TCP 80/443 and Caddy logs; services remain running."
                        ) from None
                    time.sleep(3)
        elif args.command == "doctor":
            asyncio.run(doctor(settings, args.private))
        elif args.command == "revoke-sessions":
            store = Store(settings.data_dir / "connector.sqlite3")
            with store.connection() as db:
                db.execute(
                    "DELETE FROM kv WHERE kind IN ('oauth-grant','oauth-code','oauth-pending','oauth-access','oauth-refresh')"
                )
            print(
                "OAuth sessions revoked. Restart is not required. Rotate CONNECTOR_API_TOKEN separately if needed."
            )
        else:
            server, provider, client = create_server(settings, stdio=args.transport == "stdio")
            if args.transport == "stdio":

                async def local():
                    try:
                        await server.run_stdio_async()
                    finally:
                        await client.close()

                asyncio.run(local())
            else:
                app = http_app(server, provider, settings)

                async def remote():
                    config = uvicorn.Config(
                        app,
                        host=settings.host,
                        port=settings.port,
                        access_log=False,
                        log_level="warning",
                        proxy_headers=False,
                    )
                    try:
                        await uvicorn.Server(config).serve()
                    finally:
                        await client.close()

                asyncio.run(remote())
    except (BitpinError, ValueError) as error:
        # Pydantic errors may contain supplied configuration values; don't echo them.
        print(
            str(error)
            if isinstance(error, BitpinError)
            else "Invalid connector configuration. Check .env and .secrets.env against README.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
