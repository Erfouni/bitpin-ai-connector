import re
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def symbol(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9]{1,24}_[A-Za-z0-9]{1,24}", value):
        raise ValueError("Use a Bitpin symbol such as BTC_IRT or BTC_USDT")
    return value.upper()


def positive(value: str) -> str:
    if not isinstance(value, str) or len(value) > 80 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("Amounts must be plain decimal strings, without exponent or separators")
    d = Decimal(value)
    if not d.is_finite() or d <= 0:
        raise ValueError("Amounts must be finite and greater than zero")
    return format(d, "f")


Symbol = Annotated[str, BeforeValidator(symbol)]
Amount = Annotated[str, BeforeValidator(positive)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop_limit", "oco"]
Resolution = Literal["1m", "5m", "15m", "30m", "1h", "3h", "4h", "6h", "1d", "1w", "1M"]
RES_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "3h": 10800,
    "4h": 14400,
    "6h": 21600,
    "1d": 86400,
    "1w": 604800,
    "1M": 2419200,
}


class Order(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Symbol
    side: Side
    type: OrderType
    identifier: Identifier
    base_amount: Amount | None = None
    quote_amount: Amount | None = None
    price: Amount | None = None
    stop_price: Amount | None = None
    price_limit_oco: Amount | None = None

    @model_validator(mode="after")
    def combinations(self):
        if (self.base_amount is None) == (self.quote_amount is None):
            raise ValueError("Supply exactly one of base_amount or quote_amount")
        if self.type == "market":
            if any(v is not None for v in (self.price, self.stop_price, self.price_limit_oco)):
                raise ValueError("Market orders do not accept price fields")
        else:
            if self.base_amount is None or self.price is None:
                raise ValueError("Non-market orders require base_amount and price")
            if (self.stop_price is not None) != (self.type in {"stop_limit", "oco"}):
                raise ValueError("stop_price is required only for stop_limit and oco")
            if (self.price_limit_oco is not None) != (self.type == "oco"):
                raise ValueError("price_limit_oco is required only for oco")
        return self

    def payload(self) -> dict:
        return self.model_dump(exclude_none=True)


def validate_market(order: Order, market: dict) -> None:
    if market.get("symbol") != order.symbol or market.get("tradable") is not True or market.get("suspended"):
        raise ValueError("Market is unavailable or suspended")
    for key in ("base_amount", "quote_amount", "price", "stop_price", "price_limit_oco"):
        value = getattr(order, key)
        if value is None:
            continue
        precision_key = key + "_precision" if key.endswith("amount") else "price_precision"
        precision = market.get(precision_key)
        if not isinstance(precision, int) or not 0 <= precision <= 30:
            raise ValueError(f"Market does not provide valid {precision_key}")
        d = Decimal(value)
        # Remainder avoids rounding even for values larger than the default decimal context.
        from decimal import localcontext

        with localcontext() as context:
            context.prec = 120
            if d % Decimal(1).scaleb(-precision):
                raise ValueError(f"{key} exceeds market precision ({precision}); no automatic rounding")
            if not key.endswith("amount") and market.get("price_increment") is not None:
                inc = Decimal(str(market["price_increment"]))
                if not inc.is_finite() or inc <= 0 or d % inc:
                    raise ValueError(f"{key} must be a multiple of price_increment")
