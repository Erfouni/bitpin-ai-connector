"""Optional, billable OpenAI API example. Connector installation does not require an LLM key."""

import json
import os
import urllib.request

tool = {
    "type": "mcp",
    "server_label": "bitpin",
    "server_url": os.environ["BITPIN_MCP_URL"],
    "allowed_tools": ["connector_status", "get_tickers", "get_orderbook"],
    "require_approval": "never",  # Only the three non-private, read-only tools above.
}
if token := os.getenv("CONNECTOR_API_TOKEN"):
    tool["authorization"] = token  # Optional, for AUTH_MODE=oauth.
payload = {
    "model": os.environ["OPENAI_MODEL"],
    "input": "Use Bitpin tools to report the BTC_IRT price and visible spread. State the observation time.",
    "tools": [tool],
}
request = urllib.request.Request(
    "https://api.openai.com/v1/responses",
    data=json.dumps(payload).encode(),
    headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=120) as response:
    print(response.read().decode())
