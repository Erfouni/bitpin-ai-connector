import httpx
from test_auth import app_for, login


async def test_standard_basic_client_token_and_revocation(tmp_path):
    app, provider, bitpin = app_for(tmp_path)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000"
    ) as http:
        response = await http.post(
            "/register",
            json={
                "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_basic",
            },
        )
        assert response.status_code == 201
        registered = response.json()
        auth = httpx.BasicAuth(registered["client_id"], registered["client_secret"])
        code, verifier = await login(http, registered["client_id"])
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
        }
        mismatch = await http.post("/token", data={**payload, "client_id": "wrong"}, auth=auth)
        assert mismatch.status_code == 401
        result = await http.post("/token", data=payload, auth=auth)
        assert result.status_code == 200, result.text
        tokens = result.json()
        revoked = await http.post("/revoke", data={"token": tokens["refresh_token"]}, auth=auth)
        assert revoked.status_code == 200, revoked.text
        assert await provider.load_access_token(tokens["access_token"]) is None
    await bitpin.close()
