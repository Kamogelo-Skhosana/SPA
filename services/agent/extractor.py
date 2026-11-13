"""Deterministic extraction of labeled payable fields from invoice text.

This module intentionally avoids guessing when required fields are missing or
ambiguous. It handles text that has already been copied or OCR'd from an invoice;
it does not perform OCR or submit payments.
"""
from datetime import datetime, timezone
import hashlib
import re
from typing import Any

from pydantic import BaseModel, ConfigDict

from .models import PaymentRequest


_LABELS: dict[str, re.Pattern[str]] = {
    "supplierName": re.compile(r"^\s*(?:supplier\s+name|supplier)\s*:\s*(.*?)\s*$", re.I | re.M),
    "supplierId": re.compile(r"^\s*supplier\s+id\s*:\s*(.*?)\s*$", re.I | re.M),
    "invoiceNumber": re.compile(r"^\s*(?:invoice\s+(?:number|no\.?)|invoice)\s*:\s*(.*?)\s*$", re.I | re.M),
    "amount": re.compile(r"^\s*(?:amount\s+due|total\s+due|amount|total)\s*:\s*(.*?)\s*$", re.I | re.M),
    "currency": re.compile(r"^\s*currency\s*:\s*([A-Za-z0-9_-]+)\s*$", re.I | re.M),
    "destination": re.compile(r"^\s*(?:payment\s+)?(?:destination|wallet\s+address|xrpl\s+address)\s*:\s*(.*?)\s*$", re.I | re.M),
}
_NUMBER = re.compile(r"(?<![A-Za-z0-9])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![A-Za-z0-9])")
_CURRENCY = re.compile(r"\b(RLUSD)\b", re.I)


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: PaymentRequest | None = None
    needs_clarification: bool = False
    uncertain_fields: list[str]
    questions: list[str]


def _matches(pattern: re.Pattern[str], text: str) -> list[str]:
    return [value.strip() for value in pattern.findall(text) if value.strip()]


def _slug(value: str) -> str:
    ascii_text = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def _question(field: str) -> str:
    prompts = {
        "supplierName": "Which supplier issued this invoice?",
        "supplierId": "Which approved supplier ID should be used for this supplier?",
        "invoiceNumber": "What is the invoice number?",
        "amount": "What is the single final amount due?",
        "currency": "Is the payable amount in RLUSD?",
        "destination": "What is the supplier's XRPL destination address?",
    }
    return prompts.get(field, f"Please clarify {field}.")


def _valid_positive_amount(value: str) -> bool:
    from decimal import Decimal, InvalidOperation

    try:
        number = Decimal(value.replace(",", ""))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return number.is_finite() and number > 0


def extract_payment_request(
    text: str,
    *,
    request_id: str | None = None,
    created_at: datetime | None = None,
) -> ExtractionResult:
    """Extract a strict SPA PaymentRequest or return clarification questions.

    The extractor understands explicitly labeled fields. It will not choose
    between multiple values on an amount line or invent required payment data.
    """
    if not isinstance(text, str) or not text.strip():
        fields = ["supplierName", "invoiceNumber", "amount", "currency", "destination"]
        return ExtractionResult(
            needs_clarification=True,
            uncertain_fields=fields,
            questions=[_question(field) for field in fields],
        )

    values: dict[str, Any] = {}
    uncertain: list[str] = []
    for field, pattern in _LABELS.items():
        matches = _matches(pattern, text)
        if len(matches) > 1 and len(set(matches)) > 1:
            uncertain.append(field)
        elif matches:
            values[field] = matches[0]

    amount_text = values.get("amount")
    if amount_text is not None:
        numbers = _NUMBER.findall(amount_text)
        if len(numbers) != 1 or not _valid_positive_amount(numbers[0]):
            uncertain.append("amount")
        else:
            values["amount"] = numbers[0].replace(",", "")
        if "currency" not in values:
            currency_matches = _CURRENCY.findall(amount_text)
            if currency_matches:
                values["currency"] = currency_matches[0].upper()

    supplier_name = values.get("supplierName")
    if supplier_name and "supplierId" not in values:
        generated_supplier_id = _slug(supplier_name)
        if generated_supplier_id:
            values["supplierId"] = generated_supplier_id
        else:
            uncertain.append("supplierId")

    required = ("supplierName", "invoiceNumber", "amount", "currency", "destination")
    for field in required:
        if not values.get(field) and field not in uncertain:
            uncertain.append(field)

    uncertain = list(dict.fromkeys(uncertain))
    if uncertain:
        return ExtractionResult(
            needs_clarification=True,
            uncertain_fields=uncertain,
            questions=[_question(field) for field in uncertain],
        )

    normalized_text = " ".join(text.split()).casefold()
    identifier = request_id or f"pay-{hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()[:12]}"
    timestamp = created_at or datetime.now(timezone.utc)
    values.update({"id": identifier, "createdAt": timestamp.isoformat()})
    try:
        request = PaymentRequest.model_validate(values)
    except Exception as error:
        detail = str(error).lower()
        field = "currency" if "currency" in detail else "amount"
        return ExtractionResult(
            needs_clarification=True,
            uncertain_fields=[field],
            questions=[_question(field)],
        )
    return ExtractionResult(
        request=request,
        needs_clarification=False,
        uncertain_fields=[],
        questions=[],
    )
