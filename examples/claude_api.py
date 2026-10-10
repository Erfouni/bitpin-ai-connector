"""Optional, billable Claude API example; enables only three public read tools."""

import json
import os
import urllib.request

server = {"type": "url", "url": os.environ["BITPIN_MCP_URL"], "name": "bitpin"}
if token := os.getenv("CONNECTOR_API_TOKEN"):
    server["authorization_token"] = token
payload = {
    "model": os.environ["ANTHROPIC_MODEL"],
    "max_tokens": 1200,
    "messages": [
        {
            "role": "user",
            "content": "Use Bitpin tools to report BTC_IRT price and spread with the observation time.",
        }
    ],
    "mcp_servers": [server],
    "tools": [
        {
            "type": "mcp_toolset",
            "mcp_server_name": "bitpin",
            "default_config": {"enabled": False},
            "configs": {
                name: {"enabled": True} for name in ["connector_status", "get_tickers", "get_orderbook"]
            },
        }
    ],
}
request = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps(payload).encode(),
    headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "mcp-client-2025-11-20",
        "Content-Type": "application/json",
    },
)
with urllib.request.urlopen(request, timeout=120) as response:
    print(response.read().decode())
