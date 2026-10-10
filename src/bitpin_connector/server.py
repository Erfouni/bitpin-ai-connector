import base64
import binascii
import json
import time
from functools import wraps
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, HTMLResponse, JSONResponse

from . import __version__
from .analysis import analyze_candles, summarize_book
from .auth import SCOPES, OAuthProvider
from .client import ORDERS, BitpinClient, BitpinError
from .config import Settings
from .models import RES_SECONDS, Identifier, Order, OrderType, Resolution, Side, Symbol
from .service import TradingService
from .storage import Store
from .web import render_page

Limit100 = Annotated[int, Field(ge=1, le=100)]
Limit200 = Annotated[int, Field(ge=1, le=200)]
PositiveId = Annotated[int, Field(gt=0)]
ASSETS = Path(__file__).parent / "assets"


def create_server(settings: Settings, *, stdio: bool = False, transport=None):
    store = Store(settings.data_dir / "connector.sqlite3")
    provider = OAuthProvider(settings, store)
    client = BitpinClient(settings, store, transport=transport)
    service = TradingService(client, store, settings)
    auth = (
        None
        if stdio or settings.auth_mode == "secret_path"
        else AuthSettings(
            issuer_url=settings.public_url,
            resource_server_url=settings.resource_url,
            validate_token_resource=True,
            required_scopes=["bitpin:read"],
            client_registration_options=ClientRegistrationOptions(
                enabled=True, valid_scopes=SCOPES, default_scopes=SCOPES
            ),
            revocation_options=RevocationOptions(enabled=True),
        )
    )
    origin = urlsplit(settings.public_url)
    server = FastMCP(
        "Bitpin AI Connector",
        instructions=(
            "A single-account Bitpin trading connector. Amounts and prices are decimal strings in the market's native units; IRT is toman. "
            "Use list_markets to discover precision and availability. Supply a unique stable identifier for every intended order. "
            "Never submit a replacement for a pending/unknown outcome: use resolve_order and inspect order history. "
            "Accepted is not filled; cancellation is asynchronous. List tools return one page; use the supplied cursor/offset and repeat the same filters. "
            "Preview and analysis are descriptive snapshots, not executable reservations or investment decisions. No autonomous strategy runs here."
        ),
        auth=auth,
        auth_server_provider=provider if auth else None,
        host=settings.host,
        port=settings.port,
        stateless_http=True,
        json_response=True,
        streamable_http_path=settings.mcp_path,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[origin.netloc, "localhost:*", "127.0.0.1:*"],
            allowed_origins=[settings.public_url, *settings.oauth_redirect_origins],
        ),
    )

    def tool(*, write=False):
        def register(function):
            @wraps(function)
            async def wrapped(*args, **kwargs):
                token = get_access_token()
                if (
                    not stdio
                    and settings.auth_mode == "oauth"
                    and (
                        not token
                        or "bitpin:read" not in token.scopes
                        or (write and "bitpin:trade" not in token.scopes)
                    )
                ):
                    raise ToolError(
                        "This tool requires bitpin:trade scope" if write else "Authentication required"
                    )
                try:
                    result = await function(*args, **kwargs)
                    return json.loads(json.dumps(result, default=str))
                except (BitpinError, ValueError) as error:
                    raise ToolError(str(error)) from None
                except Exception:
                    raise ToolError(
                        "Internal operation failed. For writes, inspect the existing identifier before any retry."
                    ) from None

            return server.tool(
                annotations=ToolAnnotations(
                    readOnlyHint=not write,
                    destructiveHint=write,
                    idempotentHint=not write,
                    openWorldHint=True,
                )
            )(wrapped)

        return register

    def page(rows, limit):
        if not isinstance(rows, list):
            raise ValueError("Unexpected exchange page format")
        return {
            "items": rows,
            "next_offset": min(int(r["id"]) for r in rows) if len(rows) == limit else None,
            "possibly_more": len(rows) == limit,
            "pagination": "Request the next page with next_offset and the same filters.",
        }

    @tool()
    async def connector_status() -> dict:
        """Inspect connector capabilities and configured trading mode; never returns secrets or account balances."""
        return {
            "version": __version__,
            "trading_enabled": settings.trading_enabled,
            "bitpin_credentials_configured": bool(
                settings.bitpin_api_key.get_secret_value() and settings.bitpin_secret_key.get_secret_value()
            ),
            "order_types": ["market", "limit", "stop_limit", "oco"],
            "withdrawals_supported": False,
            "mode": "single account, user-directed MCP tools; no autonomous trading loop",
        }

    @tool()
    async def list_markets(quote: str | None = None, search: str | None = None) -> dict:
        """Discover Bitpin symbols, tradability, price increments and decimal precision. Optional quote: IRT or USDT."""
        rows = await client.markets()
        filtered = [
            r
            for r in rows
            if (not quote or r.get("quote") == quote.upper())
            and (
                not search
                or search.upper() in r.get("symbol", "")
                or search.casefold() in r.get("name", "").casefold()
            )
        ]
        return {"markets": filtered, "observed_at": time.time()}

    @tool()
    async def list_currencies() -> dict:
        """Read the public Bitpin currency catalog."""
        return {"currencies": await client.request("GET", "/api/v1/mkt/currencies/")}

    @tool()
    async def list_networks() -> dict:
        """Read Bitpin's authenticated v2 network catalog; does not initiate withdrawals or transfers."""
        return {"networks": await client.request("GET", "/api/v2/wlt/networks/", private=True)}

    @tool()
    async def get_tickers(symbol: Symbol | None = None) -> dict:
        """Get live public price/statistics snapshots; filter to one symbol to reduce response size."""
        rows = await client.request("GET", "/api/v1/mkt/tickers/")
        if not isinstance(rows, list):
            raise ValueError("Unexpected ticker format")
        return {
            "tickers": [r for r in rows if symbol is None or r.get("symbol") == symbol],
            "observed_at": time.time(),
        }

    @tool()
    async def get_orderbook(symbol: Symbol) -> dict:
        """Read up to 20 bid/ask levels and calculate spread and visible depth, in native quote units."""
        data = await client.request("GET", f"/api/v1/mth/orderbook/{symbol}/")
        return {
            "symbol": symbol,
            "orderbook": data,
            "analysis": summarize_book(data),
            "observed_at": time.time(),
        }

    @tool()
    async def get_recent_trades(symbol: Symbol) -> dict:
        """Read recent public matches for a market, separate from private account fills."""
        return {
            "symbol": symbol,
            "matches": await client.request("GET", f"/api/v1/mth/matches/{symbol}/"),
            "observed_at": time.time(),
        }

    async def candles(symbol, resolution, start, end):
        if not 0 <= start < end <= int(time.time()) + 60:
            raise ValueError("Use ordered Unix seconds, with end no later than now")
        if (end - start) // RES_SECONDS[resolution] + 1 > 10000:
            raise ValueError(
                "Requested range exceeds 10,000 candles; use a smaller range or larger timeframe"
            )
        result = await client.request(
            "GET",
            "/api/v1/mkt/candles/",
            params={"symbol": symbol, "res": resolution, "from": start, "to": end},
        )
        if not isinstance(result, list) or any(c.get("resolution") != resolution for c in result):
            raise ValueError("Bitpin returned an unexpected candle shape or a different resolution")
        return result

    @tool()
    async def get_candles(symbol: Symbol, start: int, end: int, resolution: Resolution = "1h") -> dict:
        """Read OHLCV. start/end are Unix SECONDS. 1m means minute; 1M means month. Maximum 10,000 bars."""
        data = await candles(symbol, resolution, start, end)
        return {
            "symbol": symbol,
            "resolution": resolution,
            "candles": data,
            "observed_at": time.time(),
            "note": "ts is candle-open time in seconds. time is a chart timestamp in milliseconds. The last bar may be unfinished.",
        }

    @tool()
    async def analyze_market(symbol: Symbol, start: int, end: int, resolution: Resolution = "1h") -> dict:
        """Calculate completed-bar RSI14, SMA20, EMA12/26, MACD12/26/9, Bollinger20/2, ATR14 and return. No trade decision."""
        return {
            "symbol": symbol,
            **analyze_candles(await candles(symbol, resolution, start, end), resolution),
            "observed_at": time.time(),
        }

    @tool()
    async def get_commissions(symbol: Symbol | None = None) -> dict:
        """Get authenticated maker/taker fee values. Return raw units; do not assume percentage vs fraction from examples."""
        rows = await client.request("GET", "/api/v1/mkt/commissions/", private=True)
        return {
            "commissions": [r for r in rows if symbol is None or r.get("symbol") == symbol],
            "units": "raw exchange values; no conversion",
        }

    @tool()
    async def get_wallets(
        assets: str | None = None,
        service_name: str = "main",
        offset: PositiveId | None = None,
        limit: Limit200 = 200,
    ) -> dict:
        """Read one wallet page. assets is comma-separated asset codes. balance is already AVAILABLE; frozen is separate. Never subtract frozen twice or assume RIAL means IRT."""
        rows = await client.request(
            "GET",
            "/api/v1/wlt/wallets/",
            private=True,
            params={"assets": assets, "service": service_name, "offset": offset, "limit": limit},
        )
        return {**page(rows, limit), "units": "Raw asset units; balance=available, frozen=locked"}

    @tool()
    async def list_orders(
        symbol: Symbol | None = None,
        state: Literal["initial", "active", "closed"] | None = None,
        side: Side | None = None,
        order_type: OrderType | None = None,
        identifier: Identifier | None = None,
        offset: PositiveId | None = None,
        limit: Limit100 = 100,
    ) -> dict:
        """Read one current-order page. Closed orders are kept here for 7 days; use get_order_history for older matched orders."""
        rows = await client.request(
            "GET",
            ORDERS,
            private=True,
            params={
                "symbol": symbol,
                "state": state,
                "side": side,
                "type": order_type,
                "identifier": identifier,
                "offset": offset,
                "limit": limit,
            },
        )
        return page(rows, limit)

    @tool()
    async def get_order(order_id: PositiveId) -> dict:
        """Read the current exchange status of an order by numeric ID; verify partial fills and cancellation state."""
        return {"order": await client.request("GET", f"{ORDERS}{order_id}/", private=True)}

    @tool()
    async def get_order_history(
        symbol: Symbol | None = None,
        side: Side | None = None,
        order_type: OrderType | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        cursor: str | None = None,
        limit: Limit200 = 50,
    ) -> dict:
        """Read closed orders having at least one fill. Time is Unix MILLISECONDS; max 3-month range. Repeat filters with next_cursor; history can lag live orders."""
        if not cursor and start_ms is not None and end_ms is not None and not 0 <= start_ms < end_ms:
            raise ValueError("start_ms must precede end_ms")
        return await client.request(
            "GET",
            "/api/v1/odr/order_history/",
            private=True,
            params={
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "start": start_ms,
                "end": end_ms,
                "cursor": cursor,
                "limit": limit,
            },
        )

    @tool()
    async def get_fills(
        symbol: Symbol | None = None,
        side: Side | None = None,
        offset: PositiveId | None = None,
        limit: Limit100 = 100,
    ) -> dict:
        """Read one page of actual account executions including price, amount, commission currency and order ID."""
        return page(
            await client.request(
                "GET",
                "/api/v1/odr/fills/",
                private=True,
                params={"symbol": symbol, "side": side, "offset": offset, "limit": limit},
            ),
            limit,
        )

    @tool()
    async def preview_order(order: Order) -> dict:
        """Validate an order and estimate visible-book execution without sending it. Not a balance check or reservation. Market estimate excludes fees."""
        return await service.preview(order)

    @tool(write=True)
    async def place_order(order: Order) -> dict:
        """Place a REAL market/limit/stop_limit/OCO order. Requires stable unique identifier; repeated identifiers never resubmit. Unknown means reconcile, never replace. Decimal strings only."""
        return await service.place(order)

    @tool(write=True)
    async def place_orders(orders: Annotated[list[Order], Field(min_length=1, max_length=10)]) -> dict:
        """Submit up to 10 explicit orders sequentially, each with its own identifier. NOT atomic. Stops at the first non-accepted result; preceding orders remain live."""
        service.require_trading()
        if len({o.identifier for o in orders}) != len(orders):
            raise ValueError("Every batch order needs a different identifier")
        for order in orders:
            await service.market(order)
        results = []
        for order in orders:
            try:
                result = await service.place(order)
            except (ValueError, BitpinError) as error:
                result = {"status": "not_sent", "identifier": order.identifier, "message": str(error)}
            results.append(result)
            if result["status"] not in {"accepted", "existing"}:
                break
        return {
            "atomic": False,
            "results": results,
            "not_attempted": [o.identifier for o in orders[len(results) :]],
        }

    @tool()
    async def resolve_order(identifier: Identifier) -> dict:
        """Reconcile a previously used client identifier without submitting another order. Cached acceptance is a receipt; get_order returns live state."""
        return await service.resolve(identifier)

    @tool()
    async def get_order_receipt(identifier: Identifier) -> dict:
        """Read the durable local submission journal for an identifier. Contains request and last verified outcome, not necessarily current exchange state."""
        return {"receipt": store.receipt(client.account, identifier)}

    @tool(write=True)
    async def cancel_order(order_id: PositiveId | None = None, identifier: Identifier | None = None) -> dict:
        """Cancel a REAL order by either numeric ID or identifier. Accepted cancellation does not prove no fills; always check final order state."""
        return await service.cancel(order_id=order_id, identifier=identifier)

    @tool(write=True)
    async def cancel_orders(
        order_ids: Annotated[list[PositiveId], Field(min_length=1, max_length=50)],
    ) -> dict:
        """Cancel explicitly listed order IDs one by one; returns individual outcomes. Does not cancel unspecified account orders."""
        service.require_trading()
        results = []
        for oid in dict.fromkeys(order_ids):
            try:
                results.append(await service.cancel(order_id=oid))
            except BitpinError as error:
                results.append({"order_id": oid, "status": "rejected", "message": str(error)})
        return {"atomic": False, "results": results}

    @server.resource("bitpin://guide")
    def guide() -> str:
        """Units, order semantics and pagination guide."""
        return server.instructions

    @server.prompt()
    def market_review(symbol: str = "BTC_IRT") -> str:
        """Analyze a Bitpin market using live data and completed candles."""
        return (
            f"Review {symbol} using list_markets, get_tickers, get_orderbook, get_candles and analyze_market. "
            "Choose explicit start/end timestamps. Explain observation time, units, missing bars, warmup, visible liquidity and fees. "
            "Separate observations from your interpretation; do not submit orders unless the user asks for them."
        )

    @server.custom_route("/", methods=["GET"])
    async def home(request):
        return HTMLResponse(render_page(settings))

    @server.custom_route("/healthz", methods=["GET"])
    async def health(request):
        return JSONResponse({"status": "ok", "version": __version__})

    @server.custom_route("/login", methods=["GET", "POST"])
    async def login(request):
        if settings.auth_mode != "oauth":
            return JSONResponse({"error": "not_found"}, status_code=404)
        return await (
            provider.login_get(request) if request.method == "GET" else provider.login_post(request)
        )

    @server.custom_route("/assets/{name}", methods=["GET"])
    async def asset(request):
        name = request.path_params["name"]
        if name not in {"style.css", "Vazirmatn.woff2"}:
            return JSONResponse({"error": "not_found"}, status_code=404)
        return FileResponse(ASSETS / name, media_type="text/css" if name.endswith("css") else "font/woff2")

    return server, provider, client


class SecurityHeaders(BaseHTTPMiddleware):
    def __init__(self, app, provider, settings):
        super().__init__(app)
        self.provider, self.settings = provider, settings

    async def dispatch(self, request, call_next):
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                return JSONResponse({"error": "request_too_large"}, status_code=413)
        request._body = bytes(body)
        if request.url.path in {"/register", "/authorize", "/token", "/login"}:
            if not self.provider.store.limit("oauth-requests", 120, 60):
                return JSONResponse({"error": "rate_limited"}, status_code=429, headers={"Retry-After": "60"})
        if request.url.path == "/token" and request.method == "POST":
            values = parse_qs(bytes(body).decode("utf-8", errors="replace"))
            if values.get("resource", [self.settings.resource_url]) != [self.settings.resource_url]:
                return JSONResponse({"error": "invalid_target"}, status_code=400)
        if request.url.path in {"/token", "/revoke"} and request.method == "POST":
            values = parse_qs(bytes(body).decode("utf-8", errors="replace"), keep_blank_values=True)
            header = request.headers.get("authorization", "")
            if header.startswith("Basic "):
                try:
                    decoded = base64.b64decode(header[6:], validate=True).decode()
                    identifier, separator, _ = decoded.partition(":")
                    if not separator:
                        raise ValueError("Invalid Basic header")
                    identifier = unquote(identifier)
                except (ValueError, UnicodeError, binascii.Error):
                    return JSONResponse({"error": "invalid_client"}, status_code=401)
                if "client_id" in values and values["client_id"] != [identifier]:
                    return JSONResponse({"error": "invalid_client"}, status_code=401)
                if "client_id" not in values:
                    body.extend(("&" + urlencode({"client_id": identifier})).encode())
                    values["client_id"] = [identifier]
            request._body = bytes(body)
        if request.url.path == "/revoke" and request.method == "POST":
            # SDK 1.30's RevocationRequest makes nullable client_secret required.
            # Public clients correctly omit it. An empty value restores that contract;
            # SDK ClientAuthenticator still enforces confidential-client credentials.
            values = parse_qs(bytes(body).decode("utf-8", errors="replace"), keep_blank_values=True)
            if "client_secret" not in values:
                request._body = bytes(body) + b"&client_secret="
        response = await call_next(request)
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; style-src 'self'; font-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
            }
        )
        return response


def http_app(server, provider, settings):
    if settings.auth_mode == "oauth" and not settings.connector_password_hash.get_secret_value():
        raise ValueError("Set CONNECTOR_PASSWORD_HASH using the interactive setup before starting HTTP")
    app = server.streamable_http_app()
    app.add_middleware(SecurityHeaders, provider=provider, settings=settings)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[urlsplit(settings.public_url).hostname, "localhost", "127.0.0.1"],
    )
    return app
