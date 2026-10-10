"""Interactive setup for the installed connector. Secrets are never shell-evaluated."""

import argparse
import asyncio
import getpass
import hashlib
import os
import re
import secrets
from pathlib import Path

from bitpin_connector.network import print_public_ips, public_ips


def _private_write(path: Path, text: str):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
        file.write(text)


def write_configuration(
    directory: Path,
    *,
    domain: str,
    api_key: str,
    secret_key: str,
    password: str = "",
    email: str = "",
    local=False,
    trading=True,
    auth_mode="secret_path",
) -> bool:
    directory.mkdir(parents=True, exist_ok=True)
    config, secret_file = directory / ".env", directory / ".secrets.env"
    if config.exists() and secret_file.exists():
        return False
    if config.exists() or secret_file.exists():
        raise ValueError(
            "Incomplete configuration exists; restore the missing .env or .secrets.env from backup before rerunning"
        )
    if not re.fullmatch(
        r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", domain
    ):
        raise ValueError("Enter a domain such as mcp.example.com, without https:// or a path")
    if auth_mode not in {"secret_path", "oauth"}:
        raise ValueError("Invalid authentication mode")
    if (password or auth_mode == "oauth") and not 12 <= len(password) <= 256:
        raise ValueError("Password must contain 12 to 256 characters")
    for value in (api_key, secret_key):
        if not value or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError("Keys must be nonempty single-line values without whitespace")
    if email and not re.fullmatch(r"[A-Za-z0-9.!#$%&*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email):
        raise ValueError("Enter a valid certificate contact email")
    password_hash = ""
    if password:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()
        password_hash = f"scrypt:{salt.hex()}:{digest}"
    token = secrets.token_urlsafe(48)
    public_url = "http://localhost:8000" if local else f"https://{domain.lower()}"
    # Public config is a normal dotenv file. Sensitive values use Compose's raw env_file format.
    _private_write(
        config,
        f"CONNECTOR_DOMAIN={domain.lower()}\nACME_EMAIL='{email}'\nPUBLIC_URL={public_url}\nTRADING_ENABLED={'true' if trading else 'false'}\nAUTH_MODE={auth_mode}\n",
    )
    _private_write(
        secret_file,
        f"BITPIN_API_KEY={api_key}\nBITPIN_SECRET_KEY={secret_key}\nCONNECTOR_PASSWORD_HASH={password_hash}\nCONNECTOR_API_TOKEN={token}\nMCP_SECRET_PATH=/mcp-{secrets.token_urlsafe(32)}\n",
    )
    return True


def main():
    parser = argparse.ArgumentParser(description="Bitpin AI Connector setup")
    parser.add_argument("--directory", type=Path, default=Path.cwd())
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--email", default="", help="Optional certificate contact email (no prompt)")
    parser.add_argument("--read-only", action="store_true", help="Disable trading on a fresh installation")
    parser.add_argument(
        "--oauth", action="store_true", help="Use password + OAuth instead of the default secret URL"
    )
    parser.add_argument(
        "--rotate-url",
        action="store_true",
        help="Replace only the secret URL; recreate the service afterward",
    )
    args = parser.parse_args()
    if args.rotate_url:
        path = args.directory / ".secrets.env"
        lines = path.read_text(encoding="utf-8").splitlines()
        lines = [line for line in lines if not line.startswith("MCP_SECRET_PATH=")]
        lines.append("MCP_SECRET_PATH=/mcp-" + secrets.token_urlsafe(32))
        temporary = path.with_name(".secrets.env.new")
        _private_write(temporary, "\n".join(lines) + "\n")
        os.replace(temporary, path)
        print("Secret URL rotated. Recreate the connector service and update all clients.")
        return
    if (args.directory / ".env").exists() and (args.directory / ".secrets.env").exists():
        print("Existing configuration preserved. No keys or passwords changed.")
        return
    print("\nBITPIN AI CONNECTOR\nIndependent MCP connection for ChatGPT and Claude\n")
    print(
        "Whitelist this server's PUBLIC outbound IP in Bitpin. Enable account-read and trading permissions."
    )
    print("Keys stay on this server. No OpenAI or Anthropic API key is needed.\n")
    print(
        "Trading: "
        + (
            "disabled (read-only)."
            if args.read_only
            else "enabled for real order placement and cancellation."
        )
    )
    print("Detecting server public outbound IP (IPv4 / IPv6)…")
    print_public_ips(asyncio.run(public_ips()))
    input("After adding the displayed outbound IP in Bitpin, press Enter to continue: ")
    domain = "local.example.com" if args.local else input("Domain (example: mcp.example.com): ").strip()
    api_key = getpass.getpass("Bitpin API key (hidden): ").strip()
    secret_key = getpass.getpass("Bitpin secret key (hidden): ").strip()
    password = ""
    if args.oauth:
        password = getpass.getpass("Choose connector login password (12+ characters, hidden): ")
        if password != getpass.getpass("Repeat connector password: "):
            raise SystemExit("Passwords did not match; no configuration written.")
    try:
        write_configuration(
            args.directory,
            domain=domain,
            email=args.email,
            api_key=api_key,
            secret_key=secret_key,
            password=password,
            local=args.local,
            trading=not args.read_only,
            auth_mode="oauth" if args.oauth else "secret_path",
        )
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print("\nConfiguration saved with private file permissions.")
    values = dict(line.split("=", 1) for line in (args.directory / ".secrets.env").read_text().splitlines())
    endpoint = "/mcp" if args.oauth else values["MCP_SECRET_PATH"]
    print(
        "MCP URL (keep private): "
        + ("http://localhost:8000" if args.local else f"https://{domain.lower()}")
        + endpoint
    )
    print(
        "Authentication: OAuth; use your connector password."
        if args.oauth
        else "Authentication: No authentication; the random URL itself is the access credential."
    )
    print(
        "The optional bearer token for API clients is stored in .secrets.env; never share Bitpin keys with a model."
    )


if __name__ == "__main__":
    main()
