"""FastAPI routes for mandate reads, updates, and deterministic policy evaluation."""
import os
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .policy import evaluate_payment
from .lifecycle import PaymentLifecycle, StubSettlementAdapter, create_router
from .xrpl_bridge import create_xrpl_settlement_bridge

app = FastAPI(title="SPA policy API", version="0.1.0")
_lock = RLock()

# In-memory fixture for the independently developed MVP. Persistence and
# atomic budget reservation belong to the payable lifecycle workstream.
_mandate: dict[str, Any] = {
    "version": 1,
    "active": True,
    "perPaymentLimit": "5000.00",
    "totalBudget": "20000.00",
    "spent": "0.00",
    "approvedSupplierIds": ["northstar-imports"],
    "expiresAt": "2027-01-01T00:00:00Z",
}


class MandateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    active: bool
    per_payment_limit: str = Field(alias="perPaymentLimit")
    total_budget: str = Field(alias="totalBudget")
    spent: str
    approved_supplier_ids: list[str] = Field(alias="approvedSupplierIds")
    expires_at: str = Field(alias="expiresAt")
    confirmed: bool = False

    @field_validator("per_payment_limit", "total_budget", "spent")
    @classmethod
    def valid_nonnegative_decimal(cls, value: str) -> str:
        from decimal import Decimal, InvalidOperation
        try:
            number = Decimal(value)
        except (InvalidOperation, TypeError):
            raise ValueError("must be a decimal string")
        if not number.is_finite() or number < 0:
            raise ValueError("must be a finite non-negative decimal")
        return format(number, "f")

    @field_validator("expires_at")
    @classmethod
    def valid_expiry(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("must be an ISO 8601 timestamp")
        return value

    @field_validator("approved_supplier_ids")
    @classmethod
    def unique_supplier_ids(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value) or len(value) != len(set(value)):
            raise ValueError("supplier IDs must be non-empty and unique")
        return value


# A local launch without a Testnet seed is explicitly simulated. Live signing
# requires XRPL_WALLET_SEED and the XRPL adapter in the same backend process.
_use_xrpl = bool(os.getenv("XRPL_WALLET_SEED")) or os.getenv(
    "XRPL_SIMULATED", ""
).lower() in {"1", "true", "yes"}
_settlement = create_xrpl_settlement_bridge() if _use_xrpl else StubSettlementAdapter()
_lifecycle = PaymentLifecycle(_mandate, evaluate_payment, _settlement, lock=_lock)
app.include_router(create_router(_lifecycle))


@app.get("/overview")
def get_overview() -> dict[str, Any]:
    with _lock:
        mandate = deepcopy(_mandate)
    payables = _lifecycle.list_requests()
    return {
        "mandate": mandate,
        "payables": payables,
        "budgetUsed": mandate["spent"],
        "simulated": isinstance(_settlement, StubSettlementAdapter)
            or os.getenv("XRPL_SIMULATED", "").lower() in {"1", "true", "yes"},
        "network": "XRPL Testnet",
    }


@app.get("/mandate")
def get_mandate() -> dict[str, Any]:
    with _lock:
        return deepcopy(_mandate)


@app.put("/mandate")
def update_mandate(update: MandateUpdate) -> dict[str, Any]:
    if not update.confirmed:
        raise HTTPException(status_code=409, detail="Operator confirmation is required.")
    values = update.model_dump(by_alias=True, exclude={"confirmed"})
    if Decimal(values["spent"]) > Decimal(values["totalBudget"]):
        raise HTTPException(status_code=422, detail="Spent amount cannot exceed total budget.")
    with _lock:
        values["version"] = _mandate["version"] + 1
        _mandate.clear()
        _mandate.update(values)
        return deepcopy(_mandate)


@app.post("/agent/runs")
def run_policy(request: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        mandate = deepcopy(_mandate)
    return evaluate_payment(request, mandate, now=datetime.now(timezone.utc))
