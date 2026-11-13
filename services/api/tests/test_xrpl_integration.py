from services.api.lifecycle import PaymentLifecycle
from services.api.policy import evaluate_payment
from services.api.xrpl_bridge import XRPLSettlementBridge
from services.xrpl.payment import SimulatedXRPLPaymentAdapter


def mandate():
    return {
        "version": 1, "active": True, "perPaymentLimit": "100.00",
        "totalBudget": "100.00", "spent": "0.00",
        "approvedSupplierIds": ["supplier-a"], "expiresAt": "2027-01-01T00:00:00Z",
    }


def request(request_id, supplier="supplier-a"):
    return {
        "id": request_id, "supplierId": supplier, "supplierName": "Supplier A",
        "invoiceNumber": request_id, "amount": "40.00", "currency": "RLUSD",
        "destination": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
        "createdAt": "2026-11-13T12:00:00Z",
    }


def test_actual_simulated_xrpl_adapter_runs_only_after_policy_recheck():
    class CountingAdapter(SimulatedXRPLPaymentAdapter):
        calls = 0

        def submit_payment(self, payment, *, idempotency_key):
            self.calls += 1
            return super().submit_payment(payment, idempotency_key=idempotency_key)

    adapter = CountingAdapter()
    policy = mandate()
    service = PaymentLifecycle(policy, evaluate_payment, XRPLSettlementBridge(adapter))
    service.create_request(request("protected", supplier="other"))
    assert service.confirm_payment("protected")["status"] == "protected"
    assert adapter.calls == 0

    service.create_request(request("allowed"))
    first = service.confirm_payment("allowed")
    assert first["status"] == "paid"
    assert first["settlement"]["simulated"] is True
    assert first["settlement"]["txHash"].startswith("SIMULATED-")
    assert service.confirm_payment("allowed") == first
    assert adapter.calls == 1
    assert policy["spent"] == "40.00"


def test_pending_ledger_reconciliation_updates_budget_once_without_resubmission():
    class PendingAdapter:
        calls = 0
        lookups = 0

        def submit_payment(self, payment, *, idempotency_key):
            self.calls += 1
            return {"requestId": payment["id"], "status": "pending",
                    "simulated": False, "txHash": "ABC123"}

        def lookup_transaction(self, tx_hash):
            self.lookups += 1
            return {"status": "validated", "simulated": False,
                    "txHash": tx_hash, "ledgerIndex": 77}

    adapter = PendingAdapter()
    policy = mandate()
    service = PaymentLifecycle(policy, evaluate_payment, XRPLSettlementBridge(adapter))
    service.create_request(request("reconcile"))
    assert service.confirm_payment("reconcile")["status"] == "pending"
    assert policy["spent"] == "0.00"
    result = service.reconcile_payment("reconcile")
    assert result["status"] == "paid"
    assert result["settlement"]["ledgerIndex"] == 77
    assert service.reconcile_payment("reconcile") == result
    assert service.confirm_payment("reconcile") == result
    assert policy["spent"] == "40.00"
    assert adapter.calls == 1
    assert adapter.lookups == 1


def test_unknown_timeout_without_hash_stays_pending_and_never_resubmits():
    class UnknownAdapter:
        calls = 0

        def submit_payment(self, payment, *, idempotency_key):
            self.calls += 1
            return {"requestId": payment["id"], "status": "pending",
                    "simulated": False}

    adapter = UnknownAdapter()
    service = PaymentLifecycle(mandate(), evaluate_payment, XRPLSettlementBridge(adapter))
    service.create_request(request("unknown"))
    first = service.confirm_payment("unknown")
    assert service.reconcile_payment("unknown") == first
    assert service.confirm_payment("unknown") == first
    assert adapter.calls == 1
