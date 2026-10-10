import json
import sys
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from bitpin_connector.auth import hash_password
from bitpin_connector.config import Settings
from bitpin_connector.server import create_server, http_app


async def test_network_catalog_uses_authenticated_v2_endpoint(tmp_path):
    requests = []

    async def exchange(request):
        requests.append(request)
        if request.url.path.endswith("authenticate/"):
            return httpx.Response(200, json={"access": "network-test-access", "refresh": "refresh"})
        assert request.url.path == "/api/v2/wlt/networks/"
        assert request.headers.get("Authorization") == "Bearer network-test-access"
        return httpx.Response(200, json=[])

    settings = Settings(data_dir=tmp_path, bitpin_api_key="test-key", bitpin_secret_key="test-secret")
    server, _, client = create_server(settings, stdio=True, transport=httpx.MockTransport(exchange))
    await server.call_tool("list_networks", {})
    assert len(requests) == 2
    await client.close()


async def test_stdio_discovers_real_tools_and_refuses_disabled_trading(tmp_path):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "bitpin_connector.cli", "--directory", str(tmp_path), "serve", "--transport", "stdio"],
        env={"PYTHONPATH": str(Path(__file__).parents[1] / "src"), "TRADING_ENABLED": "false"},
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        result = await session.initialize()
        assert result.serverInfo.name == "Bitpin AI Connector"
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        assert {"place_order", "cancel_order", "get_order_history", "analyze_market"} <= tools.keys()
        assert tools["place_order"].annotations.destructiveHint is True
        assert tools["get_wallets"].annotations.readOnlyHint is True
        status = await session.call_tool("connector_status")
        assert not status.isError
        assert json.loads(status.content[0].text)["trading_enabled"] is False
        refused = await session.call_tool(
            "place_order",
            {
                "order": {
                    "symbol": "BTC_IRT",
                    "side": "buy",
                    "type": "market",
                    "quote_amount": "100000",
                    "identifier": "offline-test",
                }
            },
        )
        assert refused.isError
        assert "disabled" in refused.content[0].text


async def test_http_protocol_authentication_and_read_scope_enforcement(tmp_path):
    settings = Settings(
        data_dir=tmp_path, trading_enabled=True, connector_password_hash=hash_password("test-password-only")
    )
    server, provider, bitpin = create_server(settings)
    provider.store.put("oauth-grant", "grant", {"client_id": "test"}, 9999999999)
    tokens = provider._issue("test", ["bitpin:read"], "grant")
    app = http_app(server, provider, settings)
    async with server.session_manager.run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), headers={"Authorization": "Bearer " + tokens.access_token}
        ) as http:
            async with (
                streamable_http_client("http://localhost:8000/mcp", http_client=http) as (read, write, _),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                assert not (await session.call_tool("connector_status")).isError
                rejected = await session.call_tool("cancel_order", {"order_id": 1})
                assert rejected.isError
                assert "bitpin:trade" in rejected.content[0].text
                assert str((await session.list_resources()).resources[0].uri) == "bitpin://guide"
    await bitpin.close()
