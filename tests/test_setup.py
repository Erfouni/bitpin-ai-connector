import runpy
import sys
from pathlib import Path

import pytest


def test_setup_preserves_existing_keys_and_escapes_compose_secrets(tmp_path):
    setup = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "setup.py"))
    write = setup["write_configuration"]
    from bitpin_connector.auth import check_password

    assert (
        write(
            tmp_path,
            domain="mcp.example.com",
            api_key="key$literal",
            secret_key="secret#literal",
            password="a-strong-password",
            email="owner@example.com",
        )
        is True
    )
    secret_text = (tmp_path / ".secrets.env").read_text()
    assert "a-strong-password" not in secret_text
    values = dict(line.split("=", 1) for line in secret_text.splitlines())
    assert values["BITPIN_API_KEY"] == "key$literal"
    assert check_password("a-strong-password", values["CONNECTOR_PASSWORD_HASH"])
    assert len(values["CONNECTOR_API_TOKEN"]) >= 40
    assert (
        write(
            tmp_path,
            domain="other.example.com",
            api_key="other",
            secret_key="other",
            password="other-password",
            email="owner@example.com",
        )
        is False
    )
    assert (tmp_path / ".secrets.env").read_text() == secret_text


def test_setup_rejects_domain_and_env_injection_before_writing(tmp_path):
    setup = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "setup.py"))
    with pytest.raises(ValueError):
        setup["write_configuration"](
            tmp_path,
            domain="example.com\nEVIL=true",
            api_key="k",
            secret_key="s",
            password="some-password",
            email="a@example.com",
        )
    assert not (tmp_path / ".env").exists()


def test_installer_shows_ip_before_keys_and_rotation_preserves_credentials(tmp_path, monkeypatch, capsys):
    setup = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "setup.py"))
    events = []

    async def fake_ips():
        events.append("ip-discovered")
        return {"ipv4": "8.8.8.8", "ipv6": None}

    answers = iter(["", "mcp.example.com"])

    def answer(prompt):
        events.append(prompt)
        return next(answers)

    keys = iter(["dummy-api-key", "dummy-secret-key"])

    def password(prompt):
        events.append(prompt)
        return next(keys)

    monkeypatch.setattr(sys, "argv", ["setup.py", "--directory", str(tmp_path)])
    monkeypatch.setattr("builtins.input", answer)
    monkeypatch.setattr("getpass.getpass", password)
    setup["main"].__globals__["public_ips"] = fake_ips
    setup["main"]()
    output = capsys.readouterr().out
    assert "IPV4: 8.8.8.8" in output
    assert "No authentication" in output
    assert events[0] == "ip-discovered"
    assert "After adding" in events[1]
    assert "API key" in events[3]
    assert len(events) == 5  # IP probe, pause, domain and the two hidden keys only.
    assert "dummy-api-key" not in output
    assert "dummy-secret-key" not in output
    assert "TRADING_ENABLED=true" in (tmp_path / ".env").read_text()
    path = tmp_path / ".secrets.env"
    before = dict(line.split("=", 1) for line in path.read_text().splitlines())
    assert before["CONNECTOR_PASSWORD_HASH"] == ""
    monkeypatch.setattr(sys, "argv", ["setup.py", "--directory", str(tmp_path), "--rotate-url"])
    setup["main"]()
    after = dict(line.split("=", 1) for line in path.read_text().splitlines())
    assert before.pop("MCP_SECRET_PATH") != after.pop("MCP_SECRET_PATH")
    assert before == after


@pytest.mark.parametrize("email", ["", "owner@example.com"])
def test_certificate_contact_is_optional_but_never_invented(tmp_path, email):
    setup = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "setup.py"))
    assert setup["write_configuration"](
        tmp_path, domain="mcp.example.com", api_key="test-key", secret_key="test-secret", email=email
    )
    assert f"ACME_EMAIL='{email}'" in (tmp_path / ".env").read_text()


def test_read_only_flag_does_not_add_an_interactive_prompt(tmp_path, monkeypatch):
    setup = runpy.run_path(str(Path(__file__).parents[1] / "scripts" / "setup.py"))

    async def fake_ips():
        return {"ipv4": "8.8.8.8", "ipv6": None}

    setup["main"].__globals__["public_ips"] = fake_ips
    answers = iter(["", "mcp.example.com"])
    keys = iter(["test-key", "test-secret"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda _: next(keys))
    monkeypatch.setattr(sys, "argv", ["setup.py", "--directory", str(tmp_path), "--read-only"])
    setup["main"]()
    assert "TRADING_ENABLED=false" in (tmp_path / ".env").read_text()
