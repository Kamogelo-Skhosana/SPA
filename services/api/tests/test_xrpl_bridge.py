from services.api.xrpl_bridge import XRPLSettlementBridge


class FakePaymentAdapter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def submit_payment(self, request, *, idempotency_key):
        self.calls.append((request, idempotency_key))
        return self.result


def test_bridge_passes_stable_key_and_validated_receipt():
    request = {"id": "pay-1"}
    adapter = FakePaymentAdapter({
        "requestId": "pay-1", "status": "validated", "simulated": False,
        "txHash": "ABC123", "ledgerIndex": 77,
    })
    result = XRPLSettlementBridge(adapter).submit(request, idempotency_key="pay-1")
    assert result["txHash"] == "ABC123"
    assert adapter.calls == [(request, "pay-1")]


def test_bridge_preserves_ambiguous_pending_result():
    adapter = FakePaymentAdapter({
        "requestId": "pay-1", "status": "pending", "simulated": False,
    })
    result = XRPLSettlementBridge(adapter).submit(
        {"id": "pay-1"}, idempotency_key="pay-1"
    )
    assert result["status"] == "pending"


def test_bridge_rejects_mismatched_receipt():
    import pytest
    adapter = FakePaymentAdapter({"requestId": "other", "status": "validated",
                                  "simulated": True})
    with pytest.raises(ValueError, match="another request"):
        XRPLSettlementBridge(adapter).submit({"id": "pay-1"}, idempotency_key="pay-1")


def test_real_validation_requires_ledger_evidence():
    import pytest
    adapter = FakePaymentAdapter({"requestId": "pay-1", "status": "validated",
                                  "simulated": False, "txHash": "ABC123"})
    with pytest.raises(ValueError, match="ledger index"):
        XRPLSettlementBridge(adapter).submit({"id": "pay-1"}, idempotency_key="pay-1")
