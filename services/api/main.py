"""FastAPI routes for mandate reads, updates, and deterministic policy evaluation."""
import os
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from threading import RLock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .policy import evaluate_payment
from .lifecycle import PaymentLifecycle, StubSettlementAdapter, create_router
from .xrpl_bridge import create_xrpl_settlement_bridge

app = FastAPI(title="SPA policy API", version="0.1.0")
_allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "SPA_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)
_lock = RLock()
_wallet_adapter_lock = RLock()
_wallet_adapter: Any | None = None

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


class TrustlineSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: bool = False


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
    balance = None
    balance_error = None
    try:
        wallet_adapter = _get_wallet_adapter()
        if wallet_adapter is not None:
            wallet_balance = wallet_adapter.rlusd_balance()
            balance = {
                "amount": str(wallet_balance.get("balance", "0")),
                "currency": "RLUSD",
                "source": "simulated" if wallet_balance.get("simulated") else "testnet",
            }
    except Exception:
        # Keep the payables dashboard available while Setup reports wallet errors.
        balance_error = "XRPL balance is temporarily unavailable."
    return {
        "mandate": mandate,
        "payables": payables,
        "budgetUsed": mandate["spent"],
        "balance": balance,
        "balanceError": balance_error,
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


def _get_wallet_adapter():
    """Load the wallet reader only when setup is configured."""
    global _wallet_adapter
    simulated = os.getenv("XRPL_SIMULATED", "").strip().lower() in {"1", "true", "yes"}
    if not os.getenv("XRPL_WALLET_SEED") and not simulated:
        return None
    with _wallet_adapter_lock:
        if _wallet_adapter is None:
            from services.xrpl.adapter import create_xrpl_adapter
            _wallet_adapter = create_xrpl_adapter()
        return _wallet_adapter


@app.get("/xrpl/status")
def xrpl_status() -> dict[str, Any]:
    adapter = _get_wallet_adapter()
    if adapter is None:
        return {
            "network": "testnet",
            "configured": False,
            "simulated": False,
            "message": "Configure XRPL_WALLET_SEED in the backend environment.",
        }
    try:
        wallet = adapter.wallet_status()
        balance = adapter.rlusd_balance()
        simulated = bool(wallet.get("simulated", False))
        if bool(balance.get("simulated", False)) != simulated:
            raise ValueError("Wallet and balance sources do not match.")
        return {
            "network": "testnet",
            "configured": True,
            "simulated": simulated,
            "wallet": wallet,
            "balance": balance,
        }
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"XRPL Testnet status could not be verified: {error}",
        ) from error


@app.post("/xrpl/trustline")
def setup_xrpl_trustline(update: TrustlineSetup) -> dict[str, Any]:
    if not update.confirmed:
        raise HTTPException(status_code=409, detail="Operator confirmation is required.")
    adapter = _get_wallet_adapter()
    if adapter is None:
        raise HTTPException(
            status_code=503,
            detail="Configure XRPL_WALLET_SEED in the backend environment first.",
        )
    try:
        result = adapter.setup_rlusd_trustline()
        if not result.get("simulated") and not result.get("txHash"):
            raise ValueError("Validated trustline setup did not return a transaction hash.")
        return result
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"RLUSD trustline setup failed: {error}",
        ) from error
