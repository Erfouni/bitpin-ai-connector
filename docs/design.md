# Bitpin AI Connector — design, 2026-10-10

Deliver a separate repository under Erfouni, independent of AI Trader. The existing robot's API client is a read-only reference (commit 980c313eb80b291592cdf6100c306da8bcf6a1a1); no strategy, credentials, data or autonomous scheduler is copied.

## Runtime
Python 3.12+, official MCP Python SDK 1.30.0, HTTPX, SQLite. Standard stdio for local clients; Streamable HTTP for remote clients. A Docker application and Caddy terminate HTTPS. The public GitHub repository supports one-command installation on fresh Ubuntu 22.04/24.04/26.04 and Debian 12/13 systemd hosts (amd64/arm64). The bootstrap installs prerequisites and uses /opt/bitpin-ai-connector by default; Docker comes from its signed official apt repository. Setup pauses for outbound IP registration and collects only the domain and two Bitpin keys. Trading is enabled by default; --read-only and --email are optional fresh-install flags. Repeated installation preserves configuration and volumes. No LLM keys or AWS resources are required.

## Authentication and interface
Single Bitpin account per deployment. Per the user's Mizito-connector preference, default authentication is a 256-bit random secret URL, configured as No authentication in clients. Only that exact MCP route exists; public pages and discovery never reveal it. Global proxy log filters redact URI and sensitive headers; access logs are disabled. Installer supports rotating the path. Optional --oauth setup enables a password consent page, S256 PKCE, dynamic registration, resource-bound short-lived tokens, rotating refresh tokens and family revocation on reuse. SQLite persists clients, grants and order receipts; token lookup keys are hashed. Local stdio relies on OS access. Public Persian RTL page uses bundled Vazirmatn and responsive accessible controls. No account data on the public page.

## Tools
Markets, currencies, networks, tickers, 20-level order books, recent matches, OHLCV, commissions, wallets, current orders, order details, historic orders, fills. Market, limit, stop_limit and OCO placement; preview; identifier reconciliation; cancel by ID/identifier; explicit batches with individual results (not atomic). Analysis: arithmetic indicators and order-book execution estimates; the LLM decides what to do. No embedded trading strategy or withdrawal/transfer tools.

## Correctness
Fixed Bitpin origin and endpoint allowlist; no redirects or proxy inheritance. Decimal strings, finite positive quantities, market precision and price increment checks; never round an order silently. Token caching/refresh with persisted daily renewal budget and outage cooldown. Reads may retry bounded 429/5xx; write requests are never retried. Persist account-scoped order identifier + payload before sending; repeat calls cannot resubmit; an uncertain write is reconciled by exact identifier and remains unknown until verified. A cancel response is acceptance, not proof of zero fills. Cursor/offset pagination remains explicit and bounded. No inferred IRT/RIAL conversion or fee-unit conversion.

Order-journal identity persists independently of API credentials; auth-token caches are credential-specific. SQLite leases coordinate auth across processes; cooldown and rolling auth budget survive restarts. Separate accounts require separate data directories.

## Verification
Offline HTTP-boundary contract tests, persistent/concurrent order journal tests, exact Decimal and precision cases, unknown outcome handling, token expiry/refresh, OAuth PKCE/replay/expiry/resource/scopes/CSRF, MCP stdio and real HTTP handshake, deployment config checks, actual rendered desktop/mobile UI. Read-only public Bitpin smoke check. Live private account or real orders require deployment credentials and are not claimed tested here.
