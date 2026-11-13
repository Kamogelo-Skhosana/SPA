"""In-memory payable lifecycle with atomic reservations and idempotent settlement.

The service is intentionally adapter-based: production XRPL signing and ledger
verification belong in services/xrpl. Stub results are explicitly marked
simulated and must never be represented as live-ledger evidence.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from threading import RLock
from typing import Any, Callable, Protocol


class SettlementAdapter(Protocol):
    def submit(self, request: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        """Submit once and return the Settlement contract shape."""


class StubSettlementAdapter:
    """Deterministic local adapter; it makes no network or ledger calls."""

    def __init__(self, result_status: str = "validated") -> None:
        if result_status not in {"pending", "validated", "failed"}:
            raise ValueError("unsupported stub settlement status")
        self.result_status = result_status
        self._results: dict[str, dict[str, Any]] = {}
        self._lock = RLock()
        self.submission_count = 0

    def submit(self, request: dict[str, Any], *, idempotency_key: str) -> dict[str, Any]:
        with self._lock:
            if idempotency_key in self._results:
                return deepcopy(self._results[idempotency_key])
            self.submission_count += 1
            digest = sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
            result: dict[str, Any] = {
                "requestId": request["id"],
                "status": self.result_status,
                "simulated": True,
            }
            if self.result_status == "validated":
                result["txHash"] = f"SIMULATED-{digest}"
            if self.result_status == "failed":
                result["error"] = "Simulated settlement failure."
            self._results[idempotency_key] = result
            return deepcopy(result)


class PaymentLifecycle:
    """Manage request records, policy rechecks, reservations, and settlement."""

    def __init__(
        self,
        mandate: dict[str, Any],
        evaluate: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
        adapter: SettlementAdapter | None = None,
        lock: Any | None = None,
    ) -> None:
        self.mandate = mandate
        self.evaluate = evaluate
        self.adapter = adapter or StubSettlementAdapter()
        # Share the API's mandate lock so confirmation and mandate updates are
        # atomic with respect to one another as well as payable reservations.
        self._lock = lock or RLock()
        self._records: dict[str, dict[str, Any]] = {}
        self._reservations: dict[str, Decimal] = {}
        self._reserved_total = Decimal("0")

    @staticmethod
    def _amount(request: dict[str, Any]) -> Decimal:
        try:
            amount = Decimal(str(request["amount"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Payment amount must be a positive decimal string.") from error
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Payment amount must be a positive decimal string.")
        return amount

    def create_request(self, request: dict[str, Any]) -> dict[str, Any]:
        required = {"id", "supplierId", "supplierName", "invoiceNumber", "amount",
                    "currency", "destination", "createdAt"}
        missing = required.difference(request)
        if missing:
            raise ValueError(f"Missing payment request fields: {', '.join(sorted(missing))}")
        self._amount(request)
        request_id = str(request["id"])
        if not request_id:
            raise ValueError("Payment request id cannot be empty.")
        with self._lock:
            existing = self._records.get(request_id)
            if existing:
                if existing["request"] != request:
                    raise ValueError("A request with this id already exists with different data.")
                return deepcopy(existing)
            record = {
                "request": deepcopy(request),
                "status": "pending",
                "decision": None,
                "settlement": None,
            }
            self._records[request_id] = record
            return deepcopy(record)

    def list_requests(self) -> list[dict[str, Any]]:
        with self._lock:
            return [deepcopy(record) for record in self._records.values()]

    def get_payment(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records.get(request_id)
            if record is None:
                raise KeyError(request_id)
            return deepcopy(record)

    def confirm_payment(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records.get(request_id)
            if record is None:
                raise KeyError(request_id)

            # A terminal or pending settlement is replayed exactly; it is never
            # submitted a second time for the same request.
            if record["settlement"] is not None:
                return deepcopy(record)

            request = record["request"]
            amount = self._amount(request)
            effective_mandate = deepcopy(self.mandate)
            try:
                effective_mandate["spent"] = str(
                    Decimal(str(self.mandate["spent"])) + self._reserved_total
                )
            except (KeyError, InvalidOperation, TypeError, ValueError) as error:
                raise ValueError("Mandate spent amount is invalid.") from error

            decision = self.evaluate(request, effective_mandate)
            record["decision"] = deepcopy(decision)
            if decision.get("outcome") != "allowed":
                record["status"] = "protected"
                return deepcopy(record)

            # The policy check and reservation share the lifecycle lock. This
            # prevents concurrent approvals from both consuming the same budget.
            self._reservations[request_id] = amount
            self._reserved_total += amount
            record["status"] = "pending"
            try:
                settlement = self.adapter.submit(request, idempotency_key=request_id)
            except Exception:
                # An exception can occur after the network accepted the payment.
                # Keep the reservation and never submit this request again blindly.
                settlement = {
                    "requestId": request_id,
                    "status": "pending",
                    "simulated": False,
                    "error": "Settlement outcome unknown; reconcile on the ledger.",
                }

            status = settlement.get("status")
            if status not in {"pending", "validated", "failed"}:
                settlement = {
                    "requestId": request_id,
                    "status": "pending",
                    "simulated": False,
                    "error": "Settlement status unknown; reconcile on the ledger.",
                }
                status = "pending"

            record["settlement"] = deepcopy(settlement)
            if status == "validated":
                self._reserved_total -= self._reservations.pop(request_id)
                self.mandate["spent"] = str(Decimal(str(self.mandate["spent"])) + amount)
                record["status"] = "paid"
            elif status == "failed":
                self._reserved_total -= self._reservations.pop(request_id)
                record["status"] = "failed"
            else:
                record["status"] = "pending"

            return deepcopy(record)


def create_router(service: PaymentLifecycle):
    """Build the contract routes around a configured lifecycle service."""
    from fastapi import APIRouter, HTTPException

    router = APIRouter()

    @router.get("/payables")
    def list_payables() -> list[dict[str, Any]]:
        return service.list_requests()

    @router.post("/payables", status_code=201)
    def create_payable(request: dict[str, Any]) -> dict[str, Any]:
        try:
            return service.create_request(request)
        except ValueError as error:
            status_code = 409 if "already exists" in str(error) else 422
            raise HTTPException(status_code=status_code, detail=str(error)) from error

    @router.get("/payments/{request_id}")
    def get_payment(request_id: str) -> dict[str, Any]:
        try:
            return service.get_payment(request_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Payment not found.") from error

    @router.post("/payments/{request_id}/confirm")
    def confirm_payment(request_id: str) -> dict[str, Any]:
        try:
            return service.confirm_payment(request_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Payment not found.") from error

    return router
