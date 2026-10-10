import calendar
import time
from datetime import UTC, datetime
from decimal import Decimal, localcontext

from .models import RES_SECONDS


def dec(value) -> Decimal:
    d = Decimal(str(value))
    if not d.is_finite():
        raise ValueError("Non-finite market data")
    return d


def fmt(value):
    if value is None:
        return None
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def book_levels(book: dict):
    sides = []
    for side in ("asks", "bids"):
        levels = [(dec(p), dec(q)) for p, q in book.get(side, [])]
        if not levels or any(p <= 0 or q <= 0 for p, q in levels):
            raise ValueError("Order book is empty or contains invalid levels")
        prices = [p for p, _ in levels]
        if prices != sorted(prices, reverse=side == "bids"):
            raise ValueError("Order book levels are unsorted")
        sides.append(levels)
    if sides[0][0][0] <= sides[1][0][0]:
        raise ValueError("Order book is crossed or locked")
    return sides


def summarize_book(book: dict) -> dict:
    asks, bids = book_levels(book)
    ask, bid = asks[0][0], bids[0][0]
    bid_depth = sum(p * q for p, q in bids)
    ask_depth = sum(p * q for p, q in asks)
    return {
        "best_bid": fmt(bid),
        "best_ask": fmt(ask),
        "mid": fmt((ask + bid) / 2),
        "spread_bps": fmt((ask - bid) / ((ask + bid) / 2) * 10000),
        "bid_notional": fmt(bid_depth),
        "ask_notional": fmt(ask_depth),
        "depth_imbalance": fmt((bid_depth - ask_depth) / (bid_depth + ask_depth)),
        "scope": "Only the returned book levels (Bitpin documents up to 20 per side)",
    }


def estimate_execution(book: dict, side: str, *, base_amount=None, quote_amount=None) -> dict:
    asks, bids = book_levels(book)
    if side not in {"buy", "sell"} or (base_amount is None) == (quote_amount is None):
        raise ValueError("A side and exactly one amount are required")
    levels = asks if side == "buy" else bids
    remaining = dec(base_amount if base_amount is not None else quote_amount)
    if remaining <= 0:
        raise ValueError("Amount must be positive")
    base = quote = Decimal(0)
    with localcontext() as context:
        context.prec = 60
        for price, quantity in levels:
            take = min(remaining, quantity) if base_amount is not None else min(remaining / price, quantity)
            base += take
            quote += take * price
            remaining -= take if base_amount is not None else take * price
            if remaining <= 0:
                break
        average = quote / base
        return {
            "gross_base": fmt(base),
            "gross_quote": fmt(quote),
            "average_price": fmt(average),
            "slippage_bps": fmt(abs(average / levels[0][0] - 1) * 10000),
            "remaining": fmt(max(remaining, Decimal(0))),
            "fully_covered": remaining <= 0,
            "fees_included": False,
            "guaranteed": False,
        }


def _ema(values: list[Decimal], period: int) -> list[Decimal]:
    if len(values) < period:
        return []
    values_out = [sum(values[:period]) / period]
    alpha = Decimal(2) / (period + 1)
    for value in values[period:]:
        values_out.append(value * alpha + values_out[-1] * (1 - alpha))
    return values_out


def candle_end(ts: int, resolution: str) -> int:
    if resolution != "1M":
        return ts + RES_SECONDS[resolution]
    date = datetime.fromtimestamp(ts, UTC)
    year, month = (date.year + 1, 1) if date.month == 12 else (date.year, date.month + 1)
    return int(
        date.replace(
            year=year, month=month, day=min(date.day, calendar.monthrange(year, month)[1])
        ).timestamp()
    )


def analyze_candles(candles: list[dict], resolution: str, *, now: float | None = None) -> dict:
    if resolution not in RES_SECONDS:
        raise ValueError("Unsupported resolution")
    now = time.time() if now is None else now
    if any(c.get("resolution") != resolution for c in candles):
        raise ValueError("Exchange candle resolution differs from the requested resolution")
    ordered = sorted(candles, key=lambda c: dec(c["ts"]))
    timestamps = [int(dec(c["ts"])) for c in ordered]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("Duplicate candle timestamps")
    rows = [c for c in ordered if candle_end(int(dec(c["ts"])), resolution) <= now]
    if not rows:
        raise ValueError("No completed candles in the requested range")
    for c in rows:
        o, h, low, close, volume = (dec(c[k]) for k in ("open", "high", "low", "close", "volume"))
        if min(o, h, low, close) <= 0 or volume < 0 or not low <= min(o, close) <= max(o, close) <= h:
            raise ValueError("Invalid OHLCV values")
    closes = [dec(c["close"]) for c in rows]
    gaps = sum(
        candle_end(int(dec(a["ts"])), resolution) != int(dec(b["ts"]))
        for a, b in zip(rows, rows[1:], strict=False)
    )
    rsi = None
    if len(closes) >= 15:
        changes = [b - a for a, b in zip(closes, closes[1:], strict=False)]
        gains = [max(c, Decimal(0)) for c in changes]
        losses = [max(-c, Decimal(0)) for c in changes]
        gain, loss = sum(gains[:14]) / 14, sum(losses[:14]) / 14
        for next_gain, next_loss in zip(gains[14:], losses[14:], strict=True):
            gain, loss = (gain * 13 + next_gain) / 14, (loss * 13 + next_loss) / 14
        rsi = (
            Decimal(50) if gain == loss == 0 else Decimal(100) if loss == 0 else 100 - 100 / (1 + gain / loss)
        )
    sma = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    bands = None
    if sma is not None:
        sd = (sum((c - sma) ** 2 for c in closes[-20:]) / 20).sqrt()
        bands = {"middle": fmt(sma), "upper": fmt(sma + 2 * sd), "lower": fmt(sma - 2 * sd)}
    ema12, ema26 = _ema(closes, 12), _ema(closes, 26)
    macd = None
    if len(closes) >= 34:
        line = [a - b for a, b in zip(ema12[14:], ema26, strict=True)]
        signal = _ema(line, 9)[-1]
        macd = {"line": fmt(line[-1]), "signal": fmt(signal), "histogram": fmt(line[-1] - signal)}
    atr = None
    if len(rows) >= 15:
        tr = [
            max(
                dec(b["high"]) - dec(b["low"]),
                abs(dec(b["high"]) - dec(a["close"])),
                abs(dec(b["low"]) - dec(a["close"])),
            )
            for a, b in zip(rows, rows[1:], strict=False)
        ]
        atr = sum(tr[:14]) / 14
        for value in tr[14:]:
            atr = (atr * 13 + value) / 14
    return {
        "bars_used": len(rows),
        "excluded_unfinished": len(candles) - len(rows),
        "gaps": gaps,
        "resolution": resolution,
        "last_closed_ts": int(dec(rows[-1]["ts"])),
        "last_close": fmt(closes[-1]),
        "sma_20": fmt(sma),
        "ema_12": fmt(ema12[-1]) if ema12 else None,
        "ema_26": fmt(ema26[-1]) if ema26 else None,
        "rsi_14": fmt(rsi),
        "macd": macd,
        "bollinger_20_2": bands,
        "atr_14": fmt(atr),
        "return_pct": fmt((closes[-1] / closes[0] - 1) * 100),
        "method": "Completed bars only; SMA-seeded EMA; Wilder RSI/ATR; population Bollinger deviation. Null means insufficient warmup. Gaps are reported, never filled.",
    }
