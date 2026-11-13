"""Connect the payable lifecycle's settlement protocol to the XRPL payment adapter.

The lifecycle rechecks policy and reserves budget before calling this bridge.
No agent route gets access to the signing seed.
"""
from typing import Any


class XRPLSettlementBridge:
    def __init__(self, payment_adapter: Any) -> None:
        self.payment_adapter = payment_adapter

    def submit(self, request: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        result = self.payment_adapter.submit_payment(
            request, idempotency_key=idempotency_key
        )
        if result.get("requestId") != request["id"]:
            raise ValueError("XRPL adapter returned a receipt for another request.")
        if result.get("status") not in {"pending", "validated", "failed"}:
            raise ValueError("XRPL adapter returned an invalid settlement status.")
        if result.get("status") == "validated" and not result.get("simulated"):
            if not result.get("txHash") or result.get("ledgerIndex") is None:
                raise ValueError("Real validation requires a hash and ledger index.")
        return result


def create_xrpl_settlement_bridge() -> XRPLSettlementBridge:
    """Load the Testnet adapter only when the integrated service starts."""
    from services.xrpl.payment import create_payment_adapter

    return XRPLSettlementBridge(create_payment_adapter())
