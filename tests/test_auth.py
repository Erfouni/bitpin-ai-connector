import base64
import hashlib
import re
from urllib.parse import parse_qs, urlsplit

import httpx


def app_for(tmp_path):
    from bitpin_connector.auth import hash_password
    from bitpin_connector.config import Settings
    from bitpin_connector.server import create_server, http_app

    settings = Settings(
        data_dir=tmp_path,
        connector_password_hash=hash_password("correct-horse-battery"),
        connector_api_token="a" * 48,
        trading_enabled=True,
    )
    server, provider, client = create_server(settings)
    return http_app(server, provider, settings), provider, client


async def register(http):
    response = await http.post(
        "/register",
        json={
            "client_name": "Integration test",
            "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": "bitpin:read bitpin:trade",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["client_id"]


async def login(http, client_id, scope="bitpin:read bitpin:trade"):
    verifier = "x" * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    auth = await http.get(
        "/authorize",
        params={
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
            "scope": scope,
            "state": "original-state",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "resource": "http://localhost:8000/mcp",
        },
    )
    assert auth.status_code in {302, 303}, auth.text
    page = await http.get(auth.headers["location"])
    hidden = dict(re.findall(r'name="(ticket|csrf)" value="([^"]+)"', page.text))
    approved = await http.post(
        "/login", data={**hidden, "password": "correct-horse-battery", "decision": "approve"}
    )
    assert approved.status_code == 303, approved.text
    values = parse_qs(urlsplit(approved.headers["location"]).query)
    assert values["state"] == ["original-state"]
    return values["code"][0], verifier


async def test_oauth_pkce_replay_rotation_and_revocation(tmp_path):
    app, provider, bitpin = app_for(tmp_path)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
    ) as http:
        client_id = await register(http)
        code, verifier = await login(http, client_id)
        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "code_verifier": "wrong",
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
        }
        assert (await http.post("/token", data=payload)).status_code == 400
        payload["code_verifier"] = verifier
        response = await http.post("/token", data=payload)
        assert response.status_code == 200, response.text
        tokens = response.json()
        assert (
            await provider.load_access_token(tokens["access_token"])
        ).resource == "http://localhost:8000/mcp"
        assert (await http.post("/token", data=payload)).status_code == 400
        refresh_payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": tokens["refresh_token"],
        }
        newer = await http.post("/token", data=refresh_payload)
        assert newer.status_code == 200, newer.text
        assert (await http.post("/token", data=refresh_payload)).status_code == 400
        fresh = newer.json()
        assert await provider.load_access_token(fresh["access_token"]) is None
        assert (
            await http.post("/token", data={**refresh_payload, "refresh_token": fresh["refresh_token"]})
        ).status_code == 400
        # A new grant can be independently revoked.
        code, verifier = await login(http, client_id)
        fresh = (await http.post("/token", data={**payload, "code": code, "code_verifier": verifier})).json()
        revoked = await http.post("/revoke", data={"client_id": client_id, "token": fresh["refresh_token"]})
        assert revoked.status_code == 200, revoked.text
        assert await provider.load_access_token(fresh["access_token"]) is None
    await bitpin.close()


async def test_remote_is_private_and_rejects_untrusted_callbacks_and_resource(tmp_path):
    app, provider, bitpin = app_for(tmp_path)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
    ) as http:
        assert (await http.post("/mcp", json={})).status_code == 401
        assert (await http.get("/.well-known/oauth-authorization-server")).status_code == 200
        assert (await http.get("/.well-known/oauth-protected-resource/mcp")).status_code == 200
        bad = await http.post(
            "/register", json={"redirect_uris": ["https://claude.ai.evil.example/callback"]}
        )
        assert bad.status_code == 400
        client_id = await register(http)
        code, verifier = await login(http, client_id, scope="bitpin:read")
        bad = await http.post(
            "/token",
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
                "resource": "https://evil.example/mcp",
            },
        )
        assert bad.status_code == 400
        denied = await http.post(
            "/login",
            data={
                "ticket": "fake",
                "csrf": "fake",
                "password": "correct-horse-battery",
                "decision": "approve",
            },
        )
        assert denied.status_code == 400
        assert "correct-horse-battery" not in (await http.get("/")).text
    await bitpin.close()
