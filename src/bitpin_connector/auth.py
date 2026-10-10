import asyncio
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlsplit

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from .config import Settings
from .storage import Store
from .web import render_page

SCOPES = ["bitpin:read", "bitpin:trade"]


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 256:
        raise ValueError("Use a connector password with 12 to 256 characters")
    salt = secrets.token_bytes(16)
    result = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt:{salt.hex()}:{result.hex()}"


def check_password(password: str, encoded: str) -> bool:
    if len(password) > 256:
        return False
    try:
        scheme, salt, digest = encoded.split(":")
        if scheme != "scrypt":
            return False
        result = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(result.hex(), digest)
    except (ValueError, TypeError):
        return False


class GrantAccess(AccessToken):
    grant_id: str


class GrantRefresh(RefreshToken):
    grant_id: str


class OAuthProvider:
    """Single-owner OAuth authorization server. Protocol validation is handled by the MCP SDK."""

    def __init__(self, settings: Settings, store: Store):
        self.settings, self.store = settings, store

    async def get_client(self, client_id: str):
        data = self.store.get("oauth-client", client_id)
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def register_client(self, client_info: OAuthClientInformationFull):
        if not client_info.redirect_uris or len(client_info.redirect_uris) > 10:
            raise RegistrationError("invalid_redirect_uri", "One to ten callback URLs are required")
        for uri in client_info.redirect_uris:
            u = urlsplit(str(uri))
            origin = f"{u.scheme}://{u.netloc}"
            if (
                u.username
                or u.password
                or u.fragment
                or u.scheme != "https"
                or origin not in self.settings.oauth_redirect_origins
            ):
                raise RegistrationError(
                    "invalid_redirect_uri", "Callback origin is not in OAUTH_REDIRECT_ORIGINS"
                )
        if client_info.token_endpoint_auth_method not in {
            "none",
            "client_secret_post",
            "client_secret_basic",
        }:
            raise RegistrationError("invalid_client_metadata", "Unsupported client authentication method")
        self.store.put(
            "oauth-client",
            client_info.client_id,
            client_info.model_dump(mode="json"),
            time.time() + 365 * 86400,
        )

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams):
        if not self.settings.connector_password_hash.get_secret_value():
            raise AuthorizeError("access_denied", "Owner login has not been configured")
        if params.resource not in {None, self.settings.resource_url}:
            raise AuthorizeError("invalid_request", "Incorrect resource")
        scopes = params.scopes or SCOPES
        if "bitpin:read" not in scopes or not set(scopes) <= set(SCOPES):
            raise AuthorizeError("invalid_scope", "Use bitpin:read and optionally bitpin:trade")
        ticket = secrets.token_urlsafe(32)
        value = {
            "client_id": client.client_id,
            "client_name": client.client_name or "MCP Client",
            "params": params.model_dump(mode="json"),
        }
        value["params"]["scopes"] = scopes
        self.store.put("oauth-pending", ticket, value, time.time() + 600)
        return self.settings.public_url + "/login?ticket=" + ticket

    async def load_authorization_code(self, client, authorization_code):
        data = self.store.get("oauth-code", authorization_code)
        if not data or data["client_id"] != client.client_id:
            return None
        return AuthorizationCode(code=authorization_code, **data)

    def _issue(self, client_id, scopes, grant_id):
        now = int(time.time())
        access, refresh = secrets.token_urlsafe(40), secrets.token_urlsafe(48)
        common = {
            "client_id": client_id,
            "scopes": scopes,
            "resource": self.settings.resource_url,
            "subject": "owner",
            "grant_id": grant_id,
        }
        self.store.put("oauth-access", access, {**common, "expires_at": now + 3600}, now + 3600)
        self.store.put("oauth-refresh", refresh, {**common, "expires_at": now + 30 * 86400}, now + 30 * 86400)
        return OAuthToken(
            access_token=access,
            refresh_token=refresh,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(scopes),
        )

    async def exchange_authorization_code(self, client, authorization_code):
        data = self.store.pop("oauth-code", authorization_code.code)
        if not data or data["client_id"] != client.client_id:
            raise TokenError("invalid_grant", "Code has expired or was already used")
        grant = secrets.token_urlsafe(32)
        self.store.put("oauth-grant", grant, {"client_id": client.client_id}, time.time() + 30 * 86400)
        return self._issue(client.client_id, authorization_code.scopes, grant)

    async def load_refresh_token(self, client, refresh_token):
        data = self.store.get("oauth-refresh", refresh_token)
        if not data:
            self._revoke_reused_refresh(client, refresh_token)
        if (
            not data
            or data["client_id"] != client.client_id
            or not self.store.get("oauth-grant", data["grant_id"])
        ):
            return None
        return GrantRefresh(token=refresh_token, **data)

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        data = self.store.consume_refresh(refresh_token.token, client.client_id)
        if not data:
            self._revoke_reused_refresh(client, refresh_token.token)
        if (
            not data
            or data["client_id"] != client.client_id
            or not self.store.get("oauth-grant", data["grant_id"])
        ):
            raise TokenError("invalid_grant", "Refresh token has expired or was already used")
        if not set(scopes) <= set(data["scopes"]):
            raise TokenError("invalid_scope", "Scope escalation refused")
        return self._issue(client.client_id, scopes, data["grant_id"])

    def _revoke_reused_refresh(self, client, token):
        spent = self.store.get("oauth-spent", token)
        if spent and spent["client_id"] == client.client_id:
            self.store.pop("oauth-grant", spent["grant_id"])

    async def load_access_token(self, token):
        static = self.settings.connector_api_token.get_secret_value()
        if static and hmac.compare_digest(token, static):
            return AccessToken(
                token=token,
                client_id="owner-api-key",
                scopes=SCOPES,
                resource=self.settings.resource_url,
                subject="owner",
            )
        data = self.store.get("oauth-access", token)
        if not data or not self.store.get("oauth-grant", data["grant_id"]):
            return None
        return GrantAccess(token=token, **data)

    async def revoke_token(self, token):
        if isinstance(token, (GrantAccess, GrantRefresh)):
            self.store.pop("oauth-grant", token.grant_id)

    async def login_get(self, request: Request):
        ticket = request.query_params.get("ticket", "")
        pending = self.store.get("oauth-pending", ticket)
        if not pending:
            return HTMLResponse(
                render_page(
                    self.settings,
                    error="این درخواست منقضی شده است. اتصال را از برنامهٔ هوش مصنوعی دوباره آغاز کنید.",
                ),
                status_code=400,
            )
        csrf = secrets.token_urlsafe(32)
        pending["csrf_hash"] = Store.key(csrf)
        self.store.put("oauth-pending", ticket, pending, time.time() + 600)
        response = HTMLResponse(render_page(self.settings, pending=pending, ticket=ticket, csrf=csrf))
        response.set_cookie(
            "connector_csrf",
            csrf,
            httponly=True,
            secure=self.settings.public_url.startswith("https:"),
            samesite="lax",
            max_age=600,
            path="/login",
        )
        return response

    async def login_post(self, request: Request):
        form = await request.form()
        ticket, csrf = str(form.get("ticket", "")), str(form.get("csrf", ""))
        pending = self.store.get("oauth-pending", ticket)
        if (
            not pending
            or not csrf
            or not hmac.compare_digest(csrf, request.cookies.get("connector_csrf", ""))
            or not hmac.compare_digest(Store.key(csrf), pending.get("csrf_hash", ""))
        ):
            return HTMLResponse(
                render_page(self.settings, error="درخواست نامعتبر یا منقضی شده است."), status_code=400
            )
        origin = request.headers.get("origin")
        if origin and origin != self.settings.public_url:
            return HTMLResponse("Invalid origin", status_code=403)
        params = AuthorizationParams.model_validate(pending["params"])
        if form.get("decision") == "deny":
            self.store.pop("oauth-pending", ticket)
            return RedirectResponse(
                construct_redirect_uri(str(params.redirect_uri), error="access_denied", state=params.state),
                status_code=303,
            )
        if not self.store.limit("owner-login", 10, 300):
            return HTMLResponse(
                render_page(self.settings, error="تلاش‌های ورود زیاد است. پنج دقیقه دیگر تلاش کنید."),
                status_code=429,
            )
        valid = await asyncio.to_thread(
            check_password,
            str(form.get("password", "")),
            self.settings.connector_password_hash.get_secret_value(),
        )
        if not valid:
            return HTMLResponse(
                render_page(
                    self.settings, pending=pending, ticket=ticket, csrf=csrf, error="رمز اتصال درست نیست."
                ),
                status_code=401,
            )
        if not self.store.pop("oauth-pending", ticket):
            return HTMLResponse("Request already used", status_code=400)
        code = secrets.token_urlsafe(32)
        record = AuthorizationCode(
            code=code,
            scopes=params.scopes,
            expires_at=time.time() + 120,
            client_id=pending["client_id"],
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=self.settings.resource_url,
            subject="owner",
        )
        self.store.put(
            "oauth-code", code, record.model_dump(mode="json", exclude={"code"}), record.expires_at
        )
        response = RedirectResponse(
            construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state), status_code=303
        )
        response.delete_cookie("connector_csrf", path="/login")
        return response
