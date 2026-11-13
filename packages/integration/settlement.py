"""Policy-to-settlement boundary for SPA.

The gateway owns durable reservations and idempotency. The adapter only receives
an authorized reservation, never an agent instruction.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Reservation:
    request_id: str
    idempotency_key: str
    status: str
    authorization_token: str | None = None
    transaction_hash: str | None = None


class PolicyGateway(Protocol):
    def reserve(self, request_id: str, idempotency_key: str) -> Reservation:
        """Atomically recheck mandate and budget and return a durable reservation."""

    def record_submission(self, reservation: Reservation, transaction_hash: str) -> None:
        """Persist the transaction hash before awaiting ledger validation."""

    def record_validation(self, reservation: Reservation, result: dict) -> None:
        """Persist validated or failed ledger outcome."""


class SettlementAdapter(Protocol):
    def submit(self, reservation: Reservation) -> str:
        """Submit once using the reservation's stable idempotency key."""

    def lookup(self, transaction_hash: str) -> dict:
        """Return ledger validation status for an existing submission."""


def settle(request_id: str, idempotency_key: str, gateway: PolicyGateway,
           adapter: SettlementAdapter) -> dict:
    if not idempotency_key:
        raise ValueError("Idempotency key required")
    reservation = gateway.reserve(request_id, idempotency_key)
    if reservation.status == "protected":
        return {"requestId": request_id, "status": "protected"}
    if reservation.status == "validated":
        return {"requestId": request_id, "status": "validated",
                "txHash": reservation.transaction_hash}
    if reservation.status not in ("reserved", "submitted"):
        raise ValueError(f"Unsupported reservation status: {reservation.status}")

    transaction_hash = reservation.transaction_hash
    if reservation.status == "reserved":
        if not reservation.authorization_token:
            raise ValueError("Reservation lacks authorization")
        transaction_hash = adapter.submit(reservation)
        gateway.record_submission(reservation, transaction_hash)

    result = adapter.lookup(transaction_hash)
    if result.get("validated"):
        gateway.record_validation(reservation, result)
        return {"requestId": request_id, "status": "validated",
                "txHash": transaction_hash, "ledgerIndex": result.get("ledger_index")}
    return {"requestId": request_id, "status": "pending",
            "txHash": transaction_hash}
