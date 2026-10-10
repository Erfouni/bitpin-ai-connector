import time

from .analysis import estimate_execution, summarize_book
from .client import ORDERS, BitpinClient, BitpinError, UnknownOutcome
from .config import Settings
from .models import Order, validate_market
from .storage import Store


class TradingService:
    def __init__(self, client: BitpinClient, store: Store, settings: Settings):
        self.client, self.store, self.settings = client, store, settings

    def require_trading(self):
        if not self.settings.trading_enabled:
            raise ValueError("Trading is disabled on this server (TRADING_ENABLED=false)")

    async def market(self, order: Order):
        rows = await self.client.markets()
        match = next((m for m in rows if m.get("symbol") == order.symbol), None)
        if match is None:
            raise ValueError("Unknown Bitpin market")
        validate_market(order, match)
        return match

    async def preview(self, order: Order) -> dict:
        market = await self.market(order)
        result = {
            "submitted": False,
            "payload": order.payload(),
            "market": market,
            "observed_at": time.time(),
            "notes": [
                "IRT denotes toman; no rial conversion is applied.",
                "Preview is indicative, not a reservation, balance check or execution guarantee.",
                "Fees are not deducted: exchange fee-unit examples differ; inspect get_commissions.",
            ],
        }
        if order.type == "market":
            book = await self.client.request("GET", f"/api/v1/mth/orderbook/{order.symbol}/")
            result["estimate"] = estimate_execution(
                book, order.side, base_amount=order.base_amount, quote_amount=order.quote_amount
            )
            result["book"] = summarize_book(book)
        return result

    async def place(self, order: Order) -> dict:
        self.require_trading()
        payload, account = order.payload(), self.client.account
        old = self.store.receipt(account, order.identifier)
        if old:
            self.store.reserve(account, order.identifier, payload)  # checks conflicting payloads
            return await self.resolve(order.identifier)
        await self.market(order)
        await self.client.token()  # do not reserve before a known preflight credential failure
        if not self.store.reserve(account, order.identifier, payload):
            return await self.resolve(order.identifier)
        try:
            found = await self.client.find_order(order.identifier)
        except BitpinError as error:
            result = {"status": "not_sent", "identifier": order.identifier, "message": str(error)}
            self.store.finish(account, order.identifier, "not_sent", result)
            return result
        if found:
            result = {
                "status": "existing",
                "identifier": order.identifier,
                "order": found,
                "message": "Identifier was already present at Bitpin; nothing was submitted. Inspect the returned order.",
            }
            self.store.finish(account, order.identifier, "existing", result)
            return result
        try:
            response = await self.client.request("POST", ORDERS, private=True, body=payload)
            if (
                not isinstance(response, dict)
                or not response.get("id")
                or response.get("identifier") != order.identifier
            ):
                raise UnknownOutcome("Unexpected order receipt; reconcile by identifier")
            result = {
                "status": "accepted",
                "identifier": order.identifier,
                "order": response,
                "message": "Accepted by exchange; inspect state and fills to determine execution.",
            }
            self.store.finish(account, order.identifier, "accepted", result)
            return result
        except UnknownOutcome:
            result = {
                "status": "unknown",
                "identifier": order.identifier,
                "message": "The order may exist. Do not submit a replacement or change identifier. Use resolve_order.",
            }
            self.store.finish(account, order.identifier, "unknown", result)
            return await self.resolve(order.identifier)
        except BitpinError as error:
            result = {"status": "rejected", "identifier": order.identifier, "message": str(error)}
            self.store.finish(account, order.identifier, "rejected", result)
            return result
        # Unexpected exceptions/cancellation leave the durable pending reservation in place.

    async def resolve(self, identifier: str) -> dict:
        receipt = self.store.receipt(self.client.account, identifier)
        if receipt and receipt["status"] in {"accepted", "existing", "rejected", "not_sent"}:
            return {**receipt["result"], "replayed": True}
        try:
            found = await self.client.find_order(identifier)
        except BitpinError:
            found = None
        if found:
            result = {"status": "accepted", "identifier": identifier, "order": found, "reconciled": True}
            if receipt:
                self.store.finish(self.client.account, identifier, "accepted", result)
            return result
        return {
            "status": "unknown" if receipt else "not_found",
            "identifier": identifier,
            "message": "No verified result. Never resubmit an uncertain order; current order API only retains closed orders for seven days. Check history and the exchange account.",
        }

    async def cancel(self, *, order_id: int | None = None, identifier: str | None = None):
        self.require_trading()
        if (order_id is None) == (identifier is None):
            raise ValueError("Specify exactly one of order_id and identifier")
        path = ORDERS + (f"{order_id}/" if order_id is not None else f"identifier/{identifier}/")
        try:
            await self.client.request("DELETE", path, private=True)
        except UnknownOutcome:
            return {
                "status": "unknown",
                "order_id": order_id,
                "identifier": identifier,
                "message": "Cancellation outcome unknown. Inspect the order and fills before retrying.",
            }
        return {
            "status": "cancel_requested",
            "order_id": order_id,
            "identifier": identifier,
            "message": "Cancellation accepted for processing; the order may already be partially or fully filled. Verify with get_order.",
        }
