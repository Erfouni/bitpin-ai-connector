import asyncio
import sys
from types import SimpleNamespace

import pytest

from bitpin_connector import cli


def test_private_doctor_requires_wallet_list(monkeypatch, capsys, tmp_path):
    class FakeClient:
        wallets = []

        def __init__(self, settings, store):
            pass

        async def markets(self):
            return []

        async def request(self, *args, **kwargs):
            return self.wallets

        async def close(self):
            pass

    monkeypatch.setattr(cli, "BitpinClient", FakeClient)
    settings = SimpleNamespace(data_dir=tmp_path)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    FakeClient.wallets = []
    asyncio.run(cli.doctor(settings, True))
    output = capsys.readouterr().out
    assert '"private_api": "ok"' in output
    assert '"wallet_endpoint_responded": true' in output

    FakeClient.wallets = {"balance": "sensitive"}
    monkeypatch.setattr(sys, "argv", ["bitpin-ai-connector", "doctor", "--private"])
    with pytest.raises(SystemExit) as error:
        cli.main()
    captured = capsys.readouterr()
    assert error.value.code == 1
    assert '"private_api": "ok"' not in captured.out
    assert "Unexpected wallet response" in captured.err
    assert "sensitive" not in captured.err
