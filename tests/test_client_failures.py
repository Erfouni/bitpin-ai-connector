import asyncio
import json
import time

import httpx
import pytest

from bitpin_connector.client import BitpinClient, BitpinError, UnknownOutcome
from bitpin_connector.config import Settings
from bitpin_connector.models import Order
from bitpin_connector.storage import Store


@pytest.mark.parametrize("status", [301, 500, 502])
async def test_ambiguous_write_status_is_never_retried(tmp_path, status):
    requests = []

    async def exchange(request):
        if request.url.path.endswith("authenticate/"):
            return httpx.Response(200, json={"access": "A", "refresh": "R"})
        requests.append(request)
        return httpx.Response(
            status, json={"secret": "should not be shown"}, headers={"Location": "https://evil.example/"}
        )

    client = BitpinClient(
        Settings(bitpin_api_key="k", bitpin_secret_key="s"),
        Store(tmp_path / "s.db"),
        transport=httpx.MockTransport(exchange),
    )
    with pytest.raises(UnknownOutcome):
        await client.request("POST", "/api/v1/odr/orders/", body={}, private=True)
    assert len(requests) == 1
    await client.close()


async def test_expired_access_uses_refresh_and_retains_refresh_when_response_omits_it(tmp_path):
    calls = []

    async def exchange(request):
        calls.append((request.url.path, json.loads(request.content) if request.content else None))
        if request.url.path.endswith("refresh_token/"):
            return httpx.Response(200, json={"access": "new-access"})
        return httpx.Response(200, json=[])

    db = Store(tmp_path / "s.db")
    client = BitpinClient(
        Settings(bitpin_api_key="k", bitpin_secret_key="s"), db, transport=httpx.MockTransport(exchange)
    )
    db.put(
        "bitpin",
        client.auth_key,
        {
            "access": "old-access",
            "access_exp": 0,
            "refresh": "old-refresh",
            "refresh_exp": time.time() + 6000,
        },
        time.time() + 6000,
    )
    await client.request("GET", "/api/v1/wlt/wallets/", private=True)
    assert calls[0] == ("/api/v1/usr/refresh_token/", {"refresh": "old-refresh"})
    assert db.get("bitpin", client.auth_key)["refresh"] == "old-refresh"
    await client.close()


async def test_auth_outage_cooldown_and_budget_are_enforced(tmp_path):
    calls = []

    async def exchange(request):
        calls.append(request)
        return httpx.Response(503, json={})

    db = Store(tmp_path / "s.db")
    client = BitpinClient(
        Settings(bitpin_api_key="k", bitpin_secret_key="s"), db, transport=httpx.MockTransport(exchange)
    )
    for _ in range(5):
        with pytest.raises(BitpinError):
            await client.token()
    assert len(calls) == 1
    db.pop("bitpin-cooldown", client.account)
    for _ in range(149):
        db.limit("bitpin-auth:" + client.account, 150, 86400)
    with pytest.raises(BitpinError, match="budget"):
        await client.token()
    assert len(calls) == 1
    await client.close()


async def test_auth_cooldown_survives_restarts(tmp_path):
    calls = []

    async def exchange(request):
        calls.append(request)
        return httpx.Response(503, json={})

    settings = Settings(bitpin_api_key="key", bitpin_secret_key="secret")
    for _ in range(4):
        client = BitpinClient(
            settings, Store(tmp_path / "shared.db"), transport=httpx.MockTransport(exchange)
        )
        with pytest.raises(BitpinError):
            await client.token()
        await client.close()
    assert len(calls) == 1


async def test_multiple_clients_share_authentication_lease(tmp_path):
    calls = []

    async def exchange(request):
        calls.append(request)
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"access": "shared-access", "refresh": "shared-refresh"})

    settings = Settings(bitpin_api_key="key", bitpin_secret_key="secret")
    clients = [
        BitpinClient(settings, Store(tmp_path / "shared.db"), transport=httpx.MockTransport(exchange))
        for _ in range(4)
    ]
    assert await asyncio.gather(*(client.token() for client in clients)) == ["shared-access"] * 4
    assert len(calls) == 1
    for client in clients:
        await client.close()


@pytest.mark.parametrize(
    "kind,extra",
    [
        ("limit", {"price": "100"}),
        ("stop_limit", {"price": "100", "stop_price": "110"}),
        ("oco", {"price": "100", "stop_price": "110", "price_limit_oco": "120"}),
    ],
)
def test_conditional_orders_preserve_documented_field_names(kind, extra):
    order = Order(
        symbol="BTC_IRT", side="sell", type=kind, base_amount="0.10000000", identifier="test", **extra
    )
    assert order.payload() == {
        "symbol": "BTC_IRT",
        "side": "sell",
        "type": kind,
        "base_amount": "0.10000000",
        "identifier": "test",
        **extra,
    }
