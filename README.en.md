# Bitpin AI Connector

[![Tests](https://github.com/Erfouni/bitpin-ai-connector/actions/workflows/tests.yml/badge.svg)](https://github.com/Erfouni/bitpin-ai-connector/actions/workflows/tests.yml)

[فارسی](README.md) · **English**

Connect **Bitpin to ChatGPT, Claude and MCP clients** to read balances, analyze markets, place buy/sell orders and manage orders.

This project is independent of AI Trader. It provides tools for your conversations with a model; it does not run a trading strategy or scheduler. **No OpenAI or Anthropic API key is required** when connecting through ChatGPT or Claude.

## Shortest installation path

If your Linux server has `git` and `curl`, its domain already points to it, and ports 80/443 are available, run this single command from a directory where you have not already cloned the project:

```bash
git clone https://github.com/Erfouni/bitpin-ai-connector.git && cd bitpin-ai-connector && bash install.sh
```

The installer offers to install Docker, displays the outbound IP, collects configuration and sets up HTTPS. When it pauses, **register the IP in Bitpin**; when it finishes, **add the secret URL to ChatGPT and Claude**. DNS changes and account confirmations remain manual. Follow the detailed steps below if the prerequisites are missing or this is your first installation. For an existing installation, run `bash install.sh` from the project directory without cloning again.

## Step-by-step server installation

This guide uses **Ubuntu/Debian, a public domain and the default secret-URL setup**. The server must reach Bitpin and be accessible from the internet to ChatGPT and Claude. You will prepare the Bitpin API credentials in step 4.

[1. Domain](#en-domain) · [2. SSH](#en-ssh) · [3. Install](#en-install) · [4. Register the IP in Bitpin](#en-bitpin-ip) · [5. Configure](#en-setup) · [6. ChatGPT](#en-chatgpt) · [7. Claude](#en-claude) · [8. Test](#en-test)

<a id="en-domain"></a>

### 1. Point your domain to the server

For an address such as `mcp.example.com`, create this DNS record. Replace `example.com` with your own domain:

| Setting | Value |
|---|---|
| Type | `A` |
| Name | `mcp` |
| Value | Your server's public inbound IPv4 address |

If you have an `AAAA` record, it must point to the correct IPv6 address of this server. Allow inbound **TCP ports 80 and 443** in both the server firewall and the hosting provider's firewall; preserve SSH access. The default deployment uses these ports. If Nginx or another web server already owns them, read [Existing reverse proxies](#en-troubleshooting) before proceeding.

<a id="en-ssh"></a>

### 2. Sign in to the server

In your computer's terminal, replace the username and IP address:

```bash
ssh USER@SERVER_IP
```

Run all remaining shell commands **on the server**. Install the prerequisites:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
```

If you are signed in as `root` and `sudo` is unavailable, run these commands without `sudo`.

<a id="en-install"></a>

### 3. Download the project and run the installer

The repository is public. No GitHub sign-in or token is needed to download it.

```bash
cd ~
git clone https://github.com/Erfouni/bitpin-ai-connector.git
cd bitpin-ai-connector
bash install.sh
```

If Docker is missing, the installer offers to install it using Docker's official installation script; enter `Y` to continue. Docker Compose **2.30 or later** is required. Building the application may take a few minutes.

The installer then displays the server's outbound IP addresses and waits:

```text
SERVER PUBLIC OUTBOUND IP · IP مجاز بیت‌پین
  IPV4: <detected-public-ipv4>
  IPV6: <detected-public-ipv6-or-unavailable>

After adding the displayed outbound IP in Bitpin, press Enter to continue:
```

The values inside `<...>` above are explanatory placeholders. The installer displays actual detected addresses or an unavailable message. **Do not press Enter yet; complete step 4 first.**

<a id="en-bitpin-ip"></a>

### 4. Register the server IP in Bitpin and prepare your API keys

1. Sign in to Bitpin in your browser and open **API management / API keys** (`مدیریت API / کلیدهای API`). The exact menu label may vary.
2. Create a key dedicated to this connector, for example `Bitpin AI Connector`, or edit the intended existing key.
3. Add the actual address shown beside `IPV4` to that key's **allowed IP addresses**.
4. Enable permissions to **read the account and orders** and, for buying/selling, **trade and manage orders**. Withdrawal permission is not needed.
5. If an IPv6 address is also detected and the connection uses it, that outbound path must also be allowed.
6. Save the settings and complete Bitpin's required confirmations. Keep the **API Key and Secret Key** ready for the next step.
7. Return to the server terminal and press Enter.

**Register this server's public outbound IP.** Do not use your laptop's address, a Docker internal address such as `172.x.x.x`, or the domain name. Behind NAT, the outbound IP can differ from the inbound IP used in DNS. Update the allowlist if you move servers or the outbound address changes.

IP detection runs inside a container using [ipify](https://www.ipify.org/) without sending any Bitpin credentials. If detection fails, obtain the outbound IP from your hosting provider; the installer does not invent an address. Destination-dependent routing/NAT can make the address seen by Bitpin different. The `doctor --private` check verifies actual access to Bitpin.

<a id="en-setup"></a>

### 5. Answer the setup questions

| Prompt | What to enter |
|---|---|
| `Domain` | For example `mcp.example.com`, without `https://` or a `/` |
| `Email for TLS certificate notices` | Your certificate contact email |
| `Bitpin API key` | Your Bitpin API Key |
| `Bitpin secret key` | Your Bitpin Secret Key |
| `Enable REAL order placement and cancellation? [Y/n]` | `Y` or Enter enables real trading; `n` enables read-only use |

The terminal does not display characters while you enter the keys. The installer starts the application with automatic HTTPS and checks authenticated account reads and public HTTPS **without placing any trade**. After success, it prints your full connector URL:

```text
https://mcp.example.com/mcp-<random-secret>
```

This uses the same simple approach as [Mizito AI Connector](https://github.com/Erfouni/mizito-ai-connector): **the entire URL is an access credential**. Enter it only in connector settings, not in a chat, issue, screenshot or public link. Anyone holding it can use the enabled tools; this mode has no separate sessions or permissions per model. The public landing page does not reveal it. [OAuth](#optional-oauth) is available if you need separate authorization.

For steps 6 and 7, copy the actual generated URL, not the example above. Do not replace its random path with `/mcp`. Enter Bitpin keys only on the server, never in the model's connection form.

<a id="en-chatgpt"></a>

### 6. Connect ChatGPT

1. Open [ChatGPT Plugins](https://chatgpt.com/plugins); select `+`, then **Add custom MCP server**.
2. Name it `Bitpin` and enter the **complete secret URL** as Server URL.
3. Select **No authentication**; the URL itself provides access.
4. Review the access notice and choose **Create as a plugin**.
5. Install it, start a new chat, type `@` and select `Bitpin`.

Menus and availability can vary by account or workspace. [Official OpenAI instructions](https://developers.openai.com/plugins/build/app-quickstart#connect-your-mcp-server-in-chatgpt).

<a id="en-claude"></a>

### 7. Connect Claude

1. Open **Customize → Connectors**, then `+ Add` → **Add custom connector**.
2. Enter `Bitpin` and the **complete secret URL**, then select `Continue`.
3. Choose **No sign in**; leave OAuth and Request headers empty.
4. Select `Add`, then enable Bitpin in your chat through `+ → Connectors`.

Organization accounts may require an administrator to add the connector first. [Official Claude instructions](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

<a id="en-test"></a>

### 8. Test the connection without trading

With Bitpin enabled in either model, first ask:

> Use the Bitpin connector to check the connection status and BTC_IRT price. Do not place any orders.

Then verify private account access:

> Show my Bitpin wallet balances and open orders. Do not make any changes.

Successful responses to both check market and account access. If you enabled trading in step 5, order placement and cancellation tools are available too. ChatGPT and Claude retain their own approval requirements and restrictions; enabling trading does not guarantee that a host platform will execute every request.

To diagnose a problem, run these commands from the project directory on the server:

```bash
docker compose ps
docker compose exec connector bitpin-ai-connector doctor --private
docker compose logs --tail 100
```

If Docker reports permission denied, use `sudo docker ...`. For Bitpin authorization errors, check the IP allowlist, keys and API permissions. For HTTPS errors, check DNS, the `AAAA` record, ports and Caddy logs. See [Troubleshooting](#en-troubleshooting).

Display the outbound IP of the **running service** and your secret connection URL again:

```bash
docker compose exec connector bitpin-ai-connector ip
docker compose exec connector bitpin-ai-connector url
```

Rerunning `bash install.sh` preserves existing settings and does not prompt for keys again. Before Docker is installed, `curl -4 https://api.ipify.org` and, where available, `curl -6 https://api6.ipify.org` provide an initial check. The container's outbound route and Bitpin's acceptance are the final checks.

## Tools

| Purpose | MCP tools |
|---|---|
| Status and market metadata | `connector_status`, `list_markets`, `list_currencies`, `list_networks` |
| Prices and liquidity | `get_tickers`, `get_orderbook`, `get_recent_trades` |
| Candles and analysis | `get_candles`, `analyze_market` |
| Account and fees | `get_wallets`, `get_commissions` |
| Orders and fills | `list_orders`, `get_order`, `get_order_history`, `get_fills` |
| Preview and placement | `preview_order`, `place_order`, `place_orders` |
| Submission tracking | `resolve_order`, `get_order_receipt` |
| Cancellation | `cancel_order`, `cancel_orders` |

The server exposes 22 tools, the `bitpin://guide` resource and a `market_review` prompt. MCP supplies each tool's input schema to the model.

Buy and sell orders support **Market, Limit, Stop Limit and OCO**. Analysis includes RSI14, SMA20, EMA12/26, MACD12/26/9, Bollinger20/2, ATR14, returns and order-book depth. These calculations describe data; there is no prediction engine or autonomous strategy. No tools support withdrawals, transfers, account changes or API-key administration.

## Order contract

Amounts and prices must be **decimal strings**, without separators or scientific notation, for example `"0.001"`. Use `list_markets` for symbols and precision; the server does not silently round. Bitpin enforces minimum amounts, available funds and final acceptance.

| Type | Amount and price fields |
|---|---|
| `market` | Exactly one of `base_amount` or `quote_amount` |
| `limit` | `base_amount`, `price` |
| `stop_limit` | `base_amount`, `price`, `stop_price` |
| `oco` | `base_amount`, `price`, `stop_price`, `price_limit_oco` |

Example input for `preview_order`; sending the same structure to `place_order` creates a real order:

```json
{
  "order": {
    "symbol": "BTC_IRT",
    "side": "buy",
    "type": "market",
    "quote_amount": "100000",
    "identifier": "my-btc-buy-20261010-001"
  }
}
```

Use a stable, unique `identifier` for each intended order. The request is journaled in SQLite before submission. Reusing an identifier with the same database does not submit another order; changing its amount is rejected. Rotating keys or the official API origin does not reset the journal.

- `accepted` / `existing`: accepted or already found, not necessarily filled. Read live status with `get_order`.
- `unknown`: the request may have reached Bitpin. Use `resolve_order` and history; do not replace it with a new identifier.
- `rejected` / `not_sent`: definite rejection or no submission; inspect the reason.
- `cancel_requested`: cancellation is asynchronous; an order can partially fill before cancellation finishes.

Batch operations are sequential and **not atomic**. Placement supports up to 10 orders and stops at the first uncertain or unsuccessful result; earlier orders remain. Cancellation accepts up to 50 specific order IDs.

Each installation serves **one Bitpin account**. Preserve its data when rotating keys for that account. Use a separate installation and volume for another account. Deleting the volume, restoring an old backup or running separate databases loses the local deduplication guarantee. Do not assume Bitpin's identifier provides permanent deduplication.

## Units, time and data limits

- Market `IRT` means toman. Wallet values named `RIAL` are returned without a guessed conversion. `balance` is available balance; `frozen` is separate and must not be subtracted again.
- Candle input timestamps are **Unix seconds**; order history uses **Unix milliseconds** with a maximum three-month range.
- Timeframes: `1m 5m 15m 30m 1h 3h 4h 6h 1d 1w 1M`; uppercase `M` means month. Up to 10,000 candle rows per request.
- Analysis uses closed candles, reports gaps and returns `null` indicators when data is insufficient.
- Order books contain up to 20 levels. Execution estimates cover only that depth, exclude fees and do not guarantee price or available funds. Fees are returned in raw API units.
- Lists return one page. Continue with `next_offset` or `next_cursor` and the same filters. Closed orders remain in the current list for seven days; older history covers orders with fills and can lag.

## Server management

Run commands in the project directory. Update while preserving settings:

```bash
git pull --ff-only
bash install.sh
```

Restart with `docker compose restart`. Stop while preserving data with `docker compose down`, **without `-v`**.

To disable trading, set `TRADING_ENABLED=false` in `.env`, then run `docker compose up -d --force-recreate connector`. This does not cancel previously open orders.

Secrets are stored in `.secrets.env` as literal `KEY=value` entries. Do not source this file or quote values; `$` and `#` remain literal characters. Configuration and data are excluded from Git and the Docker image.

To replace a disclosed secret URL:

```bash
bash install.sh --rotate-url
```

Update both clients with the new URL. The old URL stops working; the order journal is preserved.

### Backups

The database contains the order journal and authentication data. Create a consistent snapshot with SQLite's backup API:

```bash
docker compose exec connector python -c "import sqlite3; a=sqlite3.connect('/data/connector.sqlite3'); b=sqlite3.connect('/data/backup.sqlite3'); a.backup(b); b.close(); a.close()"
docker compose cp connector:/data/backup.sqlite3 ./connector-backup.sqlite3
chmod 600 connector-backup.sqlite3
```

Keep the backup, `.env` and `.secrets.env` private and preferably encrypted. To restore, stop the connector, restore the database to `/data/connector.sqlite3` in the same volume, and preserve ownership `10001:10001` and mode `600`. Reconcile orders submitted after the backup before enabling trading.

## Optional OAuth

On a **fresh installation**, use `bash install.sh --oauth` instead of the default command for password login and separate permissions. Choose a connector password; the endpoint becomes `https://your-domain/mcp`. Select OAuth in ChatGPT and Claude; automatic client registration is supported. Never enter Bitpin keys in the model's sign-in or consent forms.

OAuth includes S256 PKCE, restricted callback origins, resource validation, `bitpin:read` / `bitpin:trade` scopes, one-hour access tokens, refresh-token rotation and family revocation on replay. Grants last at most 30 days. Passwords use scrypt; login attempts are limited.

Changing Bitpin keys does not revoke model sessions. Revoke all OAuth sessions with:

```bash
docker compose exec connector bitpin-ai-connector revoke-sessions
```

The optional static `CONNECTOR_API_TOKEN` is separate and applies only in OAuth mode. Replace it in the secrets file and recreate the connector to revoke it. For secret-URL mode, use `--rotate-url`.

Rerunning the installer with `--oauth` does not change an existing installation's mode. To switch manually, set `AUTH_MODE=oauth` in `.env`, generate a password hash without putting the password in shell history, store it as `CONNECTOR_PASSWORD_HASH` in `.secrets.env`, and recreate the connector:

```bash
docker compose run --rm --no-deps connector python -c "import getpass; from bitpin_connector.auth import hash_password; print(hash_password(getpass.getpass('Connector password: ')))"
```

If a trusted client's callback domain changes, set `OAUTH_REDIRECT_ORIGINS` in `.secrets.env` to a JSON array of exact HTTPS origins. Wildcards and substring matching are not accepted.

## Local execution

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/):

```bash
uv sync --frozen
uv run python scripts/setup.py --local
uv run bitpin-ai-connector serve --transport stdio
```

Use the [Claude Desktop example](examples/claude-desktop.json) or [Codex TOML example](examples/codex.toml), replacing paths with absolute paths. On Windows the executable is `.venv\Scripts\bitpin-ai-connector.exe`. Stdio reserves stdout for the protocol; logs go to stderr. Local access uses operating-system permissions.

For local HTTP, use `serve --transport http`. Cloud ChatGPT/Claude connectors cannot reach your localhost; they need a publicly reachable HTTPS domain.

## Model API examples

The [OpenAI Responses example](examples/openai_api.py) and [Claude Messages example](examples/claude_api.py) need no additional libraries. Configure `BITPIN_MCP_URL`, a model you can access (`OPENAI_MODEL` or `ANTHROPIC_MODEL`) and the corresponding provider API key in the example's environment. Set `CONNECTOR_API_TOKEN` only for OAuth mode; omit it for secret-URL mode.

These examples make paid API calls and allow only three public read-only tools. To add trading, deliberately expand the allowlist and implement your application's approval policy. Bitpin keys remain on the connector. See the [OpenAI MCP guide](https://developers.openai.com/api/docs/guides/tools-connectors-mcp) and [Claude MCP guide](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector).

<a id="en-troubleshooting"></a>

## Deployment details and troubleshooting

The application container runs as a non-root user with a read-only root filesystem and a separate data volume. Only Caddy exposes public ports. Raw access logging is disabled; sensitive URI/header fields are removed or masked in Caddy's structured logs. Mask or disable secret-path logging in any additional CDN or proxy.

**Existing reverse proxies:** if another web server owns ports 80/443, do not run the default Caddy service on those ports too. Adapt the deployment to use your existing HTTPS proxy, preserving Host and Streamable HTTP support when forwarding to the connector. Do not expose port 8000 directly to the internet.

| Problem | Check |
|---|---|
| Clone fails | Public repository URL, DNS and HTTPS access to GitHub; no login/token is required |
| TLS or `check-https` fails | DNS/AAAA, firewall, ports 80/443, Caddy logs and certificate-authority access |
| Model cannot connect | Full URL including the random path, public server reachability and No authentication / No sign in |
| Bitpin 401/403 | API Key/Secret validity, permissions and allowed outbound IP |
| Trading is disabled | `TRADING_ENABLED` and recreation of the connector container |
| `bitpin:trade` error | In OAuth mode, grant trading scope when connecting the model |
| 429 or authentication cooldown | Wait for the cooldown/rate-limit window; restarting does not clear it |
| Order result is `unknown` | Resolve the same identifier; do not automatically send a replacement |

Bitpin credentials/tokens are stored in private files/SQLite on the server without separate encryption at rest. Administrative access to the server or volume provides access to the connected account.

## Development and verification

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
docker build -t bitpin-ai-connector:local .
```

Tests cover real MCP protocol exchanges over stdio/HTTP, secret paths, OAuth/PKCE/CSRF and revocation, concurrent/restarted/key-rotated orders, disconnects after submission, exact decimals, incomplete candles and preservation of setup secrets. The Linux CI workflow runs tests, lint and a Docker build.

Private account access, live trading, connection from actual ChatGPT/Claude accounts and certificate issuance for your domain require deployment credentials and are not claimed as live-account development tests. The installer checks read-only account access and public HTTPS on your server.

[API contract and sources](docs/api-contract.md) · [Technical design](docs/design.md) · [Verification record](docs/verification.md)

This independent, unofficial project is not affiliated with Bitpin, OpenAI or Anthropic. Code is MIT-licensed; the bundled Vazirmatn font is distributed under the OFL.
