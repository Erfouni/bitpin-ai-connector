import asyncio
import time

import httpx
import pytest


def test_order_requires_unambiguous_amounts_and_exact_values():
    from bitpin_connector.models import Order

    order = Order(symbol="btc_irt", side="buy", type="market", quote_amount="100000", identifier="test-1")
    assert order.payload() == {
        "symbol": "BTC_IRT",
        "side": "buy",
        "type": "market",
        "quote_amount": "100000",
        "identifier": "test-1",
    }
    for amount in ["0", "-1", "NaN", "Infinity", "1e5", "1,000"]:
        with pytest.raises(ValueError):
            Order(symbol="BTC_IRT", side="buy", type="market", quote_amount=amount, identifier="test-1")
    with pytest.raises(ValueError):
        Order(
            symbol="BTC_IRT",
            side="buy",
            type="market",
            quote_amount="1000",
            base_amount="1",
            identifier="test-1",
        )
    with pytest.raises(ValueError):
        Order(symbol="BTC_IRT", side="buy", type="limit", base_amount="1", identifier="test-1")


def test_journal_survives_restart_and_refuses_changed_payload(tmp_path):
    from bitpin_connector.storage import Store

    db = Store(tmp_path / "state.sqlite3")
    assert db.reserve("account", "test-1", {"side": "buy"}) is True
    other = Store(tmp_path / "state.sqlite3")
    assert other.reserve("account", "test-1", {"side": "buy"}) is False
    with pytest.raises(ValueError, match="different"):
        other.reserve("account", "test-1", {"side": "sell"})
    assert other.receipt("account", "test-1")["status"] == "pending"
    assert other.reserve("other-account", "test-1", {"side": "buy"}) is True


async def test_auth_refresh_is_shared_and_secrets_not_sent_to_public_endpoints(tmp_path):
    from bitpin_connector.client import BitpinClient
    from bitpin_connector.config import Settings
    from bitpin_connector.storage import Store

    calls = []

    async def exchange(request):
        calls.append((request.url.path, request.headers.get("Authorization"), request.content))
        if request.url.path.endswith("authenticate/"):
            return httpx.Response(200, json={"access": "private-access", "refresh": "private-refresh"})
        return httpx.Response(200, json=[])

    settings = Settings(bitpin_api_key="key", bitpin_secret_key="secret", data_dir=tmp_path)
    client = BitpinClient(
        settings, Store(tmp_path / "state.sqlite3"), transport=httpx.MockTransport(exchange)
    )
    await asyncio.gather(*(client.request("GET", "/api/v1/wlt/wallets/", private=True) for _ in range(4)))
    await client.request("GET", "/api/v1/mkt/markets/")
    assert len([c for c in calls if c[0].endswith("authenticate/")]) == 1
    assert calls[-1][1] is None
    assert all(c[1] == "Bearer private-access" for c in calls[1:-1])
    await client.close()


async def test_write_timeout_is_not_retried_and_errors_hide_secrets(tmp_path):
    from bitpin_connector.client import BitpinClient, BitpinError, UnknownOutcome
    from bitpin_connector.config import Settings
    from bitpin_connector.storage import Store

    posts = []

    async def exchange(request):
        if request.url.path.endswith("authenticate/"):
            return httpx.Response(200, json={"access": "SECRET", "refresh": "REFRESH"})
        posts.append(request)
        raise httpx.ReadTimeout("SECRET payload", request=request)

    client = BitpinClient(
        Settings(bitpin_api_key="key", bitpin_secret_key="secret", data_dir=tmp_path),
        Store(tmp_path / "s.db"),
        transport=httpx.MockTransport(exchange),
    )
    with pytest.raises(UnknownOutcome) as err:
        await client.request("POST", "/api/v1/odr/orders/", private=True, body={"identifier": "a"})
    assert len(posts) == 1
    assert "SECRET" not in str(err.value)
    with pytest.raises(BitpinError):
        await client.request("GET", "https://evil.example/wallets/", private=True)
    await client.close()


def test_expiring_records_are_atomic_and_single_use(tmp_path):
    from bitpin_connector.storage import Store

    db = Store(tmp_path / "s.db")
    db.put("code", "secret-code", {"client_id": "client"}, time.time() + 10)
    assert db.pop("code", "secret-code") == {"client_id": "client"}
    assert db.pop("code", "secret-code") is None
    db.put("code", "expired", {}, time.time() - 1)
    assert db.get("code", "expired") is None
    assert b"secret-code" not in (tmp_path / "s.db").read_bytes()
