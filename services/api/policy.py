"""Deterministic mandate evaluation for payable requests.

This module contains no signing or settlement logic. A protected decision must
be treated as non-submittable by every caller.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


def evaluate_payment(request: dict[str, Any], mandate: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Return the shared-contract Decision shape for one payment request."""
    reasons: list[str] = []
    instant = now or datetime.now(timezone.utc)

    if not mandate.get("active", False):
        reasons.append("Mandate is paused.")

    supplier_id = request.get("supplierId")
    approved = mandate.get("approvedSupplierIds") or []
    if supplier_id not in approved:
        reasons.append("Supplier is not on the approved supplier list.")

    try:
        amount = Decimal(str(request.get("amount", "")))
        per_payment_limit = Decimal(str(mandate["perPaymentLimit"]))
        total_budget = Decimal(str(mandate["totalBudget"]))
        spent = Decimal(str(mandate["spent"]))
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
        if not per_payment_limit.is_finite() or not total_budget.is_finite() or not spent.is_finite():
            raise InvalidOperation
        if amount > per_payment_limit:
            reasons.append("Payment exceeds the per-payment limit.")
        if spent + amount > total_budget:
            reasons.append("Payment exceeds the remaining mandate budget.")
    except (InvalidOperation, KeyError, TypeError, ValueError):
        reasons.append("Payment or mandate amount is invalid.")

    expiry_value = mandate.get("expiresAt")
    if expiry_value:
        try:
            expiry = datetime.fromisoformat(str(expiry_value).replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if instant.tzinfo is None:
                instant = instant.replace(tzinfo=timezone.utc)
            if expiry <= instant:
                reasons.append("Mandate has expired.")
        except ValueError:
            reasons.append("Mandate expiry is invalid.")

    return {
        "requestId": request.get("id", ""),
        "outcome": "protected" if reasons else "allowed",
        "reasons": reasons or ["Payment complies with the active mandate."],
        "mandateVersion": mandate.get("version", 0),
    }
