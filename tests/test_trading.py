import asyncio
import json

import httpx
import pytest

MARKET = {
    "symbol": "BTC_IRT",
    "base": "BTC",
    "quote": "IRT",
    "tradable": True,
    "price_precision": 0,
    "base_amount_precision": 8,
    "quote_amount_precision": 0,
    "price_increment": "10",
}


def make_service(tmp_path, *, timeout=False, trading=True, key="key"):
    from bitpin_connector.client import BitpinClient
    from bitpin_connector.config import Settings
    from bitpin_connector.service import TradingService
    from bitpin_connector.storage import Store

    writes = []

    async def exchange(request):
        path = request.url.path
        if path.endswith("authenticate/"):
            return httpx.Response(200, json={"access": "access", "refresh": "refresh"})
        if path.endswith("markets/"):
            return httpx.Response(200, json=[MARKET])
        if path.endswith("orderbook/BTC_IRT/"):
            return httpx.Response(200, json={"asks": [["100000000", "0.1"]], "bids": [["99900000", "0.1"]]})
        if request.method == "GET":
            return httpx.Response(200, json=[])
        payload = json.loads(request.content)
        writes.append(payload)
        await asyncio.sleep(0.01)
        if timeout:
            raise httpx.ReadTimeout("lost response", request=request)
        return httpx.Response(201, json={**payload, "id": 42, "state": "active"})

    settings = Settings(
        bitpin_api_key=key, bitpin_secret_key="secret", trading_enabled=trading, data_dir=tmp_path
    )
    db = Store(tmp_path / "s.db")
    client = BitpinClient(settings, db, transport=httpx.MockTransport(exchange))
    return TradingService(client, db, settings), writes


def order(**kwargs):
    from bitpin_connector.models import Order

    return Order(
        symbol="BTC_IRT", side="buy", type="market", quote_amount="100000", identifier="order-1", **kwargs
    )


async def test_concurrent_and_restarted_clients_never_duplicate_orders(tmp_path):
    service, writes = make_service(tmp_path)
    results = await asyncio.gather(service.place(order()), service.place(order()))
    assert len(writes) == 1
    assert any(r["status"] == "accepted" for r in results)
    restarted, other_writes = make_service(tmp_path)
    assert (await restarted.place(order()))["order"]["id"] == 42
    assert not other_writes
    await service.client.close()
    await restarted.client.close()


async def test_uncertain_order_stays_unknown_on_repeat_and_restart(tmp_path):
    service, writes = make_service(tmp_path, timeout=True)
    assert (await service.place(order()))["status"] == "unknown"
    assert (await service.place(order()))["status"] == "unknown"
    restarted, second = make_service(tmp_path)
    assert (await restarted.place(order()))["status"] == "unknown"
    assert len(writes) == 1 and not second
    await service.client.close()
    await restarted.client.close()


async def test_key_rotation_preserves_order_journal(tmp_path):
    service, writes = make_service(tmp_path)
    await service.place(order())
    rotated, second_writes = make_service(tmp_path, key="new-key")
    assert (await rotated.place(order()))["order"]["id"] == 42
    assert len(writes) == 1 and not second_writes
    await service.client.close()
    await rotated.client.close()


async def test_read_only_mode_rejects_writes_but_allows_preview(tmp_path):
    service, writes = make_service(tmp_path, trading=False)
    with pytest.raises(ValueError, match="disabled"):
        await service.place(order())
    preview = await service.preview(order())
    assert preview["submitted"] is False
    assert preview["estimate"]["gross_base"] == "0.001"
    assert not writes
    await service.client.close()


def test_market_precision_and_increment_are_never_silently_rounded():
    from bitpin_connector.models import Order, validate_market

    with pytest.raises(ValueError, match="multiple"):
        validate_market(
            Order(symbol="BTC_IRT", side="sell", type="limit", base_amount="1", price="101", identifier="x"),
            MARKET,
        )
    with pytest.raises(ValueError, match="precision"):
        validate_market(
            Order(symbol="BTC_IRT", side="sell", type="market", base_amount="0.000000001", identifier="x"),
            MARKET,
        )


def test_analysis_reports_real_warmup_and_ignores_unclosed_bars():
    from bitpin_connector.analysis import analyze_candles

    candles = [
        {
            "ts": i * 3600,
            "resolution": "1h",
            "open": str(i + 1),
            "high": str(i + 2),
            "low": str(i + 1),
            "close": str(i + 2),
            "volume": "1",
        }
        for i in range(30)
    ]
    result = analyze_candles(candles, "1h", now=30 * 3600 - 1)
    assert result["bars_used"] == 29
    assert result["rsi_14"] == "100"
    assert result["sma_20"] == "20.5"
    assert result["macd"] is None
    with pytest.raises(ValueError, match="resolution"):
        analyze_candles(candles, "4h", now=999999)


def test_depth_estimate_refuses_to_invent_missing_liquidity():
    from bitpin_connector.analysis import estimate_execution

    book = {"asks": [["100", "1"]], "bids": [["99", "1"]]}
    result = estimate_execution(book, "buy", quote_amount="200")
    assert result["fully_covered"] is False
    assert result["remaining"] == "100"
    assert result["gross_base"] == "1"
