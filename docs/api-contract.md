# Verified API contracts

Research date: 2026-10-10. Primary source: [Bitpin API documentation](https://docs.bitpin.ir/).
The documentation is a client-rendered application; contracts were read from rendered pages.
Connection reference only: [AI Trader API module](https://github.com/Erfouni/bitpin-ai-trader/blob/980c313eb80b291592cdf6100c306da8bcf6a1a1/bitpin/api.py).
No strategy, secrets or dependency on that repository is included.

## Endpoints

Origin: https://api.bitpin.org (https://api.bitpin.ir is also explicitly allowed).

| Method | Path | Contract |
|---|---|---|
| POST | /api/v1/usr/authenticate/ | api_key, secret_key → access + refresh |
| POST | /api/v1/usr/refresh_token/ | refresh → access; preserve old refresh if omitted |
| GET | /api/v1/mkt/markets/ | Symbols, tradability, precision, optional price increment |
| GET | /api/v1/mkt/currencies/ | Currency catalog |
| GET | /api/v1/mkt/tickers/ | Public market statistics |
| GET | /api/v1/mkt/candles/ | symbol, res, from/to in seconds; max 10,000 |
| GET | /api/v1/mkt/commissions/ | Authenticated fee data |
| GET | /api/v1/mth/orderbook/{symbol}/ | Up to 20 levels; [price, quantity] pairs |
| GET | /api/v1/mth/matches/{symbol}/ | Public matches |
| GET | /api/v2/wlt/networks/ | Authenticated network catalog migrated from v1 |
| GET | /api/v1/wlt/wallets/ | Authenticated; assets CSV, service, offset, limit ≤200 |
| GET, POST | /api/v1/odr/orders/ | Read page or place order |
| GET, DELETE | /api/v1/odr/orders/{id}/ | Current detail or async cancellation |
| DELETE | /api/v1/odr/orders/identifier/{identifier}/ | Async cancellation by client identifier |
| GET | /api/v1/odr/fills/ | Authenticated executions; offset, limit ≤100 |
| GET | /api/v1/odr/order_history/ | Matched closed orders, cursor pagination, times in ms, ≤3 months |

Access tokens last 15 minutes; refresh tokens last 7 days. Authentication and refresh share
an exchange limit of 200/day. This connector applies a persistent rolling cap of 150/day,
an exponential 30–1800 second outage cooldown, and an expiring SQLite lease.
Manual clients outside this connector can still consume the exchange's shared allowance.

Market orders choose exactly one base_amount or quote_amount. Other types require base_amount
and price; stop_limit requires stop_price; OCO also requires price_limit_oco.
Numbers are sent as exact decimal strings. HTTP 204 cancellation means accepted, not completed.
GET current orders retains closed orders for seven days; history contains only orders with fills
and may lag live state. Offset pagination selects IDs less than the cursor; history cursors must
be accompanied by the original filters.

## Explicit choices around ambiguous documentation

- The v2 network catalog returns HTTP 401 without credentials in the live public probe.
  It is therefore classified as an authenticated read, not a public-market call.

- Native bulk examples contain inconsistent paths/JSON. The exposed batch tools instead call
  documented single-order endpoints sequentially and state that they are not atomic.
- Commission examples and existing robot code use different apparent units. Return raw values;
  do not guess a conversion or include speculative fees in execution estimates.
- Wallet balance is already available, with frozen separate. Do not infer RIAL/IRT conversions.
- Candle ts is open time in seconds; time is chart time in milliseconds and can represent an end.
  Use ts for completion and chronology. Monthly completion uses a calendar month.
- Invalid candle resolutions may fall back to 30m upstream; validate input and response resolution.

## Arithmetic

All market arithmetic uses Decimal. SMA is the arithmetic mean; EMA uses alpha=2/(period+1)
with an initial SMA. RSI and ATR use Wilder smoothing. Flat RSI is 50. MACD is EMA12−EMA26
with an EMA9 signal. Bollinger bands are SMA20 ± 2 population standard deviations.
Incomplete bars are excluded; gaps are reported, never filled with invented prices.
Insufficient history returns null. Spread bps = (ask−bid)/midpoint × 10,000.
Book execution estimates walk visible levels and report uncovered quantity/value separately.

## MCP and authentication

- [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.30.0):
  pinned stable v1 SDK, Streamable HTTP and stdio. MCP schemas use native SDK validation.
- [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization):
  optional OAuth with PKCE, dynamic registration, exact resource binding and scoped tools.
- [OAuth Security BCP §4.14.2](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14.2):
  retain hashed consumed-refresh relationships and revoke the grant on replay.
- SDK 1.30 compatibility adapters: populate missing form client_id from a validated Basic header
  (the SDK still validates its secret and method); populate nullable client_secret for public
  revocation requests. Both paths are covered by HTTP integration tests.
- Default secret URL follows the user's [Mizito connector](https://github.com/Erfouni/mizito-ai-connector)
  connection pattern. It is a bearer capability, not OAuth. Generate 256 random bits, disable
  public disclosure, use HTTPS, omit access logs, redact proxy error request fields and support rotation.
- [Docker raw env_file](https://docs.docker.com/reference/compose-file/services/#env_file):
  Compose ≥2.30 preserves literal secret values without interpolation.
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https) and
  [log filters](https://caddyserver.com/docs/caddyfile/directives/log): TLS termination with URI/header redaction.
