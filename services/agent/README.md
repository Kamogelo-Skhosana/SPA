# Agent workstream

The agent converts labeled invoice text into a schema-validated \`PaymentRequest\`, asks for clarification when required fields are missing or ambiguous, then sends a validated proposal to the deterministic policy gateway. It explains the gateway's exact decision and records each processing step.

The extractor handles text already copied or OCR'd from an invoice; it does not perform OCR. Supported fields are explicit labels: Supplier, Supplier ID (optional), Invoice Number, Amount/Amount Due/Total Due, Currency, and Destination. Supplier ID is deterministically derived from the supplier name only when no ID is supplied. A missing or ambiguous field stops the run before the policy call.

Example:

\`\`\`python
from services.agent import run_text
from services.agent.agent import http_policy_gateway

result = run_text(
    invoice_text,
    http_policy_gateway("http://localhost:8000"),
)
print(result.model_dump(by_alias=True, mode="json"))
\`\`\`

An allowed gateway result is only a proposal and sets \`nextAction\` to \`operator_confirmation\`. A protected result records that no settlement was requested. The agent package has no signing key or settlement method; the API gateway remains authoritative.

For independent development, inject a callable into \`run_agent(request, policy_gateway)\`. The callable receives the shared contract and must return a gateway Decision. A gateway error is recorded as an error trace and never becomes an approval.

Install the package requirements and run its contract fixtures with:

\`\`\`sh
python -m pip install -r services/agent/requirements.txt
python -m pytest services/agent/tests
\`\`\`
