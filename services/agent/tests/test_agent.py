from datetime import datetime, timezone

import pytest

from services.agent import extract_payment_request, run_agent, run_text
from services.agent.agent import PolicyGatewayError
from services.agent.models import PaymentRequest


INVOICE = """Supplier: Cape Meridian Foods
Invoice Number: INV-2026-1048
Amount Due: RLUSD 18,450.00
Destination: rTEST_APPROVED_SUPPLIER_ADDRESS
"""


def payment_request(**updates):
    value = {
        "id": "req-1048",
        "supplierId": "cape-meridian-foods",
        "supplierName": "Cape Meridian Foods",
        "invoiceNumber": "INV-2026-1048",
        "amount": "18450.00",
        "currency": "RLUSD",
        "destination": "rTEST_APPROVED_SUPPLIER_ADDRESS",
        "createdAt": "2026-11-13T08:42:00Z",
    }
    value.update(updates)
    return value


def test_extracts_a_schema_validated_request_from_labeled_invoice():
    result = extract_payment_request(
        INVOICE,
        request_id="req-1048",
        created_at=datetime(2026, 11, 13, 8, 42, tzinfo=timezone.utc),
    )
    assert result.needs_clarification is False
    assert result.uncertain_fields == []
    assert result.request is not None
    assert result.request.model_dump(by_alias=True, mode="json") == payment_request()


def test_extraction_derives_stable_supplier_id_and_request_id():
    first = extract_payment_request(INVOICE)
    second = extract_payment_request(INVOICE)
    assert first.request is not None and second.request is not None
    assert first.request.supplier_id == "cape-meridian-foods"
    assert first.request.id == second.request.id


@pytest.mark.parametrize(
    ("text", "field", "question_part"),
    [
        ("Supplier: Cape Meridian Foods\\nInvoice Number: INV-1\\nDestination: rTest", "amount", "amount"),
        (
            "Supplier: Cape Meridian Foods\\nInvoice Number: INV-1\\n"
            "Amount: 100.00 or 200.00 RLUSD\\nDestination: rTest",
            "amount",
            "amount",
        ),
        (
            "Supplier: Cape Meridian Foods\\nInvoice Number: INV-1\\n"
            "Amount: 100.00\\nDestination: rTest",
            "currency",
            "RLUSD",
        ),
    ],
)
def test_missing_or_ambiguous_fields_request_clarification_without_calling_gateway(text, field, question_part):
    calls = []
    result = run_text(text, lambda request: calls.append(request))
    assert result.status == "clarification"
    assert result.next_action == "clarify"
    assert calls == []
    assert any(question_part.lower() in question.lower() for question in result.clarification_questions)


def test_allowed_gateway_decision_is_explained_and_waits_for_operator_confirmation():
    gateway_calls = []
    def gateway(request):
        gateway_calls.append(request)
        return {
            "requestId": request["id"],
            "outcome": "allowed",
            "reasons": ["Payment complies with the active mandate."],
            "mandateVersion": 3,
        }

    result = run_agent(payment_request(), gateway)
    assert result.status == "ready"
    assert result.next_action == "operator_confirmation"
    assert result.decision is not None and result.decision.outcome == "allowed"
    assert "operator must confirm" in result.explanation
    assert [step.name for step in result.steps] == [
        "validate_request", "request_policy", "receive_policy_decision", "settlement_boundary"
    ]
    assert len(gateway_calls) == 1


def test_protected_gateway_decision_never_calls_settlement():
    calls = {"gateway": 0, "settlement": 0}
    def gateway(request):
        calls["gateway"] += 1
        return {
            "requestId": request["id"],
            "outcome": "protected",
            "reasons": ["Supplier is not on the approved supplier list."],
            "mandateVersion": 3,
        }

    result = run_agent(payment_request(), gateway)
    assert result.status == "protected"
    assert result.next_action == "none"
    assert result.decision is not None and result.decision.outcome == "protected"
    assert "No settlement request was made." in result.explanation
    assert calls == {"gateway": 1, "settlement": 0}
    assert result.steps[-1].status == "blocked"


def test_policy_gateway_error_is_traced_and_never_requests_settlement():
    def failing_gateway(_request):
        raise PolicyGatewayError("offline")

    result = run_agent(payment_request(), failing_gateway)
    assert result.status == "error"
    assert result.next_action == "retry"
    assert result.decision is None
    assert result.steps[-1].status == "failed"
    assert "No payment action was requested." in result.explanation


def test_gateway_decision_for_different_request_is_rejected():
    result = run_agent(
        payment_request(),
        lambda _request: {
            "requestId": "other-id",
            "outcome": "allowed",
            "reasons": ["ok"],
            "mandateVersion": 3,
        },
    )
    assert result.status == "error"
    assert result.decision is None


def test_invalid_currency_is_not_sent_to_policy_gateway():
    calls = []
    result = run_agent(payment_request(currency="USD"), lambda request: calls.append(request))
    assert result.status == "clarification"
    assert result.next_action == "clarify"
    assert calls == []


def test_payment_request_contract_rejects_extra_fields_and_bad_amounts():
    with pytest.raises(Exception):
        PaymentRequest.model_validate({**payment_request(), "secret": "never pass this"})
    with pytest.raises(Exception):
        PaymentRequest.model_validate(payment_request(amount="NaN"))
