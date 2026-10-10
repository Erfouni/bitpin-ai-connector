import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from bitpin_connector.config import Settings
from bitpin_connector.server import create_server, http_app


async def test_secret_url_is_the_only_mcp_route_and_never_disclosed_publicly(tmp_path):
    path = "/mcp-" + "aB9_" * 12
    settings = Settings(data_dir=tmp_path, auth_mode="secret_path", mcp_secret_path=path)
    server, provider, client = create_server(settings)
    app = http_app(server, provider, settings)
    async with (
        server.session_manager.run(),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=settings.public_url) as http,
    ):
        for url in [
            "/",
            "/healthz",
            "/mcp",
            "/mcp-wrong",
            "/.well-known/oauth-authorization-server",
            "/login",
        ]:
            response = await http.get(url)
            assert path not in response.text
        assert (await http.post("/mcp", json={})).status_code == 404
        assert (await http.post(path + "x", json={})).status_code == 404
        assert (await http.get("/.well-known/oauth-authorization-server")).status_code == 404
        assert (await http.post(path, json={}, headers={"Origin": "https://evil.example"})).status_code == 403
        async with (
            streamable_http_client(settings.public_url + path, http_client=http) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            assert not (await session.call_tool("connector_status")).isError
            assert len((await session.list_tools()).tools) >= 20
            denied = await session.call_tool("cancel_order", {"order_id": 1})
            assert denied.isError and "disabled" in denied.content[0].text
    await client.close()


def test_secret_mode_fails_closed_without_a_strong_path(tmp_path):
    for value in ["", "/mcp", "/mcp-short", "/mcp-" + "x" * 43 + "?a=b"]:
        with pytest.raises(ValueError):
            settings = Settings(data_dir=tmp_path, auth_mode="secret_path", mcp_secret_path=value)
            create_server(settings)
