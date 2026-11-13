"""Shared-contract models used by the agent workstream."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentRequest(BaseModel):
    """Validated payable proposal; all amounts remain decimal strings."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = Field(min_length=1)
    supplier_id: str = Field(alias="supplierId", min_length=1)
    supplier_name: str = Field(alias="supplierName", min_length=1)
    invoice_number: str = Field(alias="invoiceNumber", min_length=1)
    amount: str
    currency: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    created_at: datetime = Field(alias="createdAt")

    @field_validator("id", "supplier_id", "supplier_name", "invoice_number", "currency", "destination")
    @classmethod
    def trim_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized != "RLUSD":
            raise ValueError("only RLUSD payable requests are supported")
        return normalized

    @field_validator("amount")
    @classmethod
    def positive_decimal_string(cls, value: str) -> str:
        try:
            amount = Decimal(value.replace(",", "").strip())
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("must be a decimal amount") from error
        if not amount.is_finite() or amount <= 0:
            raise ValueError("must be a finite amount greater than zero")
        return format(amount, "f")


class Decision(BaseModel):
    """Deterministic result returned by the policy gateway."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    request_id: str = Field(alias="requestId", min_length=1)
    outcome: Literal["allowed", "protected"]
    reasons: list[str] = Field(min_length=1)
    mandate_version: int = Field(alias="mandateVersion", ge=0)

    @field_validator("reasons")
    @classmethod
    def non_blank_reasons(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("reasons must not contain blank entries")
        return cleaned


class AgentStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: Literal["completed", "blocked", "failed"]
    detail: str


class AgentRunResult(BaseModel):
    """Operator-facing decision explanation and an auditable agent trace."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    status: Literal["ready", "protected", "clarification", "error"]
    request: PaymentRequest | None = None
    decision: Decision | None = None
    explanation: str
    next_action: Literal["operator_confirmation", "none", "clarify", "retry"] = Field(alias="nextAction")
    clarification_questions: list[str] = Field(default_factory=list, alias="clarificationQuestions")
    steps: list[AgentStep]
