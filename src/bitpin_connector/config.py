import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bitpin_api_key: SecretStr = SecretStr("")
    bitpin_secret_key: SecretStr = SecretStr("")
    bitpin_base_url: str = "https://api.bitpin.org"
    public_url: str = "http://localhost:8000"
    connector_password_hash: SecretStr = SecretStr("")
    connector_api_token: SecretStr = SecretStr("")
    auth_mode: Literal["oauth", "secret_path"] = "oauth"
    mcp_secret_path: SecretStr = SecretStr("")
    trading_enabled: bool = False
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8000
    request_timeout: float = 20
    # JSON array of HTTPS callback origins; exact origins, never substring matching.
    oauth_redirect_origins: list[str] = [
        "https://chatgpt.com",
        "https://chat.openai.com",
        "https://claude.ai",
        "https://claude.com",
    ]

    @field_validator("bitpin_base_url")
    @classmethod
    def bitpin_origin(cls, value: str) -> str:
        if value.rstrip("/") not in {"https://api.bitpin.org", "https://api.bitpin.ir"}:
            raise ValueError("Only official Bitpin API origins are allowed")
        return value.rstrip("/")

    @field_validator("public_url")
    @classmethod
    def public_origin(cls, value: str) -> str:
        u = urlsplit(value)
        if u.username or u.password or u.query or u.fragment or u.path not in {"", "/"}:
            raise ValueError("PUBLIC_URL must be an origin without credentials or a path")
        if not u.hostname or (
            u.scheme != "https" and not (u.scheme == "http" and u.hostname in {"localhost", "127.0.0.1"})
        ):
            raise ValueError("PUBLIC_URL requires HTTPS (HTTP allowed only on loopback)")
        return value.rstrip("/")

    @property
    def mcp_path(self) -> str:
        if self.auth_mode == "oauth":
            return "/mcp"
        value = self.mcp_secret_path.get_secret_value()
        if not re.fullmatch(r"/mcp-[A-Za-z0-9_-]{43,128}", value):
            raise ValueError("Secret-path mode requires a randomly generated MCP_SECRET_PATH")
        return value

    @property
    def resource_url(self) -> str:
        return self.public_url + self.mcp_path
