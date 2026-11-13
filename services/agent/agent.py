"""Policy-gateway adapter, operator explanations, and agent trace generation."""
from collections.abc import Callable, Mapping
from typing import Any

import httpx
from pydantic import ValidationError

from .extractor import extract_payment_request
from .models import AgentRunResult, AgentStep, Decision, PaymentRequest


PolicyGateway = Callable[[dict[str, Any]], Mapping[str, Any]]


class PolicyGatewayError(RuntimeError):
    """Raised when the deterministic policy gateway cannot be reached."""


def http_policy_gateway(base_url: str, *, timeout: float = 5.0) -> PolicyGateway:
    """Create a synchronous gateway callable for POST /agent/runs."""
    normalized_url = f"{base_url.rstrip('/')}/agent/runs"

    def evaluate(request: dict[str, Any]) -> Mapping[str, Any]:
        try:
            response = httpx.post(normalized_url, json=request, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise PolicyGatewayError("Policy gateway request failed.") from error
        if not isinstance(payload, Mapping):
            raise PolicyGatewayError("Policy gateway returned an invalid response.")
        return payload

    return evaluate


def explain_decision(decision: Decision) -> str:
    """Render the gateway's decision and reasons without changing its meaning."""
    reasons = " ".join(decision.reasons)
    if decision.outcome == "protected":
        return f"Protected by policy: {reasons} No settlement request was made."
    return (
        f"Policy allows this payment proposal: {reasons} "
        "An operator must confirm it before settlement."
    )


def _clarification_questions(error: ValidationError) -> list[str]:
    labels = {
        "id": "What is the payable request ID?",
        "supplier_id": "Which supplier ID should be used?",
        "supplierId": "Which supplier ID should be used?",
        "supplier_name": "Which supplier issued this invoice?",
        "supplierName": "Which supplier issued this invoice?",
        "invoice_number": "What is the invoice number?",
        "invoiceNumber": "What is the invoice number?",
        "amount": "What is the final amount due?",
        "currency": "Is the payable amount in RLUSD?",
        "destination": "What is the supplier's XRPL destination address?",
        "created_at": "When was this payable created?",
        "createdAt": "When was this payable created?",
    }
    questions: list[str] = []
    for detail in error.errors():
        location = str(detail["loc"][-1]) if detail.get("loc") else "request"
        question = labels.get(location)
        if question and question not in questions:
            questions.append(question)
    return questions or ["Please provide a complete payable request using the shared contract."]


def run_agent(
    request_data: PaymentRequest | Mapping[str, Any],
    policy_gateway: PolicyGateway,
) -> AgentRunResult:
    """Validate a proposal, ask the gateway, explain its decision, and trace steps.

    This agent has no settlement method. Even an allowed result only asks for
    operator confirmation; a protected result explicitly suppresses settlement.
    """
    steps = [AgentStep(name="validate_request", status="completed", detail="Checking the shared payable contract.")]
    try:
        request = request_data if isinstance(request_data, PaymentRequest) else PaymentRequest.model_validate(request_data)
    except ValidationError as error:
        questions = _clarification_questions(error)
        steps[0] = AgentStep(
            name="validate_request",
            status="blocked",
            detail="Required or valid payable fields are missing; policy was not called.",
        )
        return AgentRunResult(
            status="clarification",
            explanation="The request is incomplete or ambiguous. Please clarify the missing fields.",
            nextAction="clarify",
            clarificationQuestions=questions,
            steps=steps,
        )

    steps.append(AgentStep(name="request_policy", status="completed", detail="Sending the validated proposal to the deterministic policy gateway."))
    try:
        decision_payload = policy_gateway(request.model_dump(by_alias=True, mode="json"))
        decision = Decision.model_validate(decision_payload)
        if decision.request_id != request.id:
            raise ValueError("Gateway decision refers to a different request.")
    except Exception as error:
        steps.append(AgentStep(
            name="receive_policy_decision",
            status="failed",
            detail=f"Policy gateway did not return a valid decision ({type(error).__name__}).",
        ))
        return AgentRunResult(
            status="error",
            request=request,
            explanation="The policy decision is unavailable. No payment action was requested.",
            nextAction="retry",
            steps=steps,
        )

    steps.append(AgentStep(name="receive_policy_decision", status="completed", detail="Received the gateway's authoritative decision."))
    if decision.outcome == "protected":
        steps.append(AgentStep(
            name="settlement_boundary",
            status="blocked",
            detail="Protected decision; no settlement call or request was made.",
        ))
        status = "protected"
        next_action = "none"
    else:
        steps.append(AgentStep(
            name="settlement_boundary",
            status="completed",
            detail="Agent proposes no settlement; an operator confirmation is required next.",
        ))
        status = "ready"
        next_action = "operator_confirmation"

    return AgentRunResult(
        status=status,
        request=request,
        decision=decision,
        explanation=explain_decision(decision),
        nextAction=next_action,
        steps=steps,
    )


def run_text(
    text: str,
    policy_gateway: PolicyGateway,
    *,
    request_id: str | None = None,
) -> AgentRunResult:
    """Extract labeled invoice text, ask for clarification, or assess it."""
    extraction = extract_payment_request(text, request_id=request_id)
    if extraction.needs_clarification or extraction.request is None:
        return AgentRunResult(
            status="clarification",
            explanation="The payable details are incomplete or ambiguous. No policy or settlement request was made.",
            nextAction="clarify",
            clarificationQuestions=extraction.questions,
            steps=[
                AgentStep(
                    name="extract_payable",
                    status="blocked",
                    detail=f"Needs clarification for: {', '.join(extraction.uncertain_fields)}.",
                ),
                AgentStep(
                    name="settlement_boundary",
                    status="blocked",
                    detail="No policy or settlement request was made.",
                ),
            ],
        )
    result = run_agent(extraction.request, policy_gateway)
    result.steps.insert(0, AgentStep(
        name="extract_payable",
        status="completed",
        detail="Extracted and schema-validated the labeled payable fields.",
    ))
    return result
