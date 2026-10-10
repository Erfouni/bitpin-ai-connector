# Verification record

2026-10-10, initial implementation.

- 36 offline tests pass on Windows/Python 3.12 and inside the Linux Docker image. These use HTTP boundary mocks;
  no exchange orders or private credentials are required.
- Real MCP initialization, discovery, calls, resource discovery and scope enforcement
  verified over stdio and Streamable HTTP.
- Container image builds; runs as UID 10001 with read-only root, temporary /tmp,
  dropped capabilities and a persistent /data volume.
- Docker Compose configuration with raw secret values validates; Linux bash syntax validates.
- Caddy 2.11 configuration validates. An intentional unavailable upstream returned 502;
  captured runtime logs contained neither the dummy secret URI nor the dummy
  Authorization, Cookie or Referer values.
- Live public tools passed through the running container: connector_status, list_markets,
  list_currencies, get_tickers, get_orderbook, get_recent_trades, analyze_market.
  MCP discovery returned 22 tools. Network catalog's unauthenticated probe returned 401;
  authentication was added and verified offline.
- Egress-IP command ran inside the final image, returned a valid public IPv4 and
  reported unavailable IPv6 without inventing an address.
- Persian RTL landing and OAuth consent pages visually inspected at desktop and
  390×844 mobile sizes. Bundled Vazirmatn loaded; no horizontal overflow.
- Independent review findings addressed: journal stability during key rotation,
  persistent auth cooldown/shared lease, refresh replay family revocation,
  Basic client authentication compatibility, Caddy runtime-log secret redaction.

Not exercised: private Bitpin account access, real orders/cancellation, paid model API calls,
connection from a real ChatGPT/Claude account, or TLS issuance for the user's domain.
The installer checks public HTTPS and authenticated read access on the actual server.
GitHub Actions could not start its runner: GitHub reported failed recent account payments or
a spending limit requiring an increase. No workflow step ran. This is an account-level CI
blocker, separate from the successful local Windows and Linux-container tests.
[Initial run](https://github.com/Erfouni/bitpin-ai-connector/actions/runs/38046340373).
