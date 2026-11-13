from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest

from services.api.lifecycle import PaymentLifecycle, StubSettlementAdapter
from services.api.policy import evaluate_payment


@pytest.fixture
def mandate():
    return {
        "version": 1,
        "active": True,
        "perPaymentLimit": "100.00",
        "totalBudget": "100.00",
        "spent": "0.00",
        "approvedSupplierIds": ["supplier-a"],
        "expiresAt": "2027-01-01T00:00:00Z",
    }


def request_for(request_id, amount="60.00", supplier="supplier-a"):
    return {
        "id": request_id,
        "supplierId": supplier,
        "supplierName": "Supplier A",
        "invoiceNumber": f"INV-{request_id}",
        "amount": amount,
        "currency": "RLUSD",
        "destination": "rTestDestination",
        "createdAt": "2026-11-13T12:00:00Z",
    }


def evaluator(request, mandate):
    return evaluate_payment(
        request, mandate, now=datetime(2026, 11, 13, tzinfo=timezone.utc)
    )


def test_duplicate_request_is_idempotent_and_rejects_payload_changes(mandate):
    service = PaymentLifecycle(mandate, evaluator)
    req = request_for("p-1", "20.00")
    assert service.create_request(req) == service.create_request(req)
    with pytest.raises(ValueError):
        service.create_request(request_for("p-1", "21.00"))


def test_protected_request_never_reaches_adapter(mandate):
    adapter = StubSettlementAdapter()
    service = PaymentLifecycle(mandate, evaluator, adapter)
    service.create_request(request_for("p-protected", supplier="unknown"))

    result = service.confirm_payment("p-protected")

    assert result["status"] == "protected"
    assert result["settlement"] is None
    assert adapter.submission_count == 0
    assert mandate["spent"] == "0.00"


def test_duplicate_confirmation_submits_once_and_replays_receipt(mandate):
    adapter = StubSettlementAdapter()
    service = PaymentLifecycle(mandate, evaluator, adapter)
    service.create_request(request_for("p-1", "40.00"))

    first = service.confirm_payment("p-1")
    second = service.confirm_payment("p-1")

    assert first == second
    assert adapter.submission_count == 1
    assert first["settlement"]["simulated"] is True
    assert mandate["spent"] == "40.00"


def test_concurrent_requests_cannot_overspend_budget(mandate):
    adapter = StubSettlementAdapter()
    service = PaymentLifecycle(mandate, evaluator, adapter)
    service.create_request(request_for("p-1", "60.00"))
    service.create_request(request_for("p-2", "60.00"))
    barrier = Barrier(3)

    def confirm(request_id):
        barrier.wait()
        return service.confirm_payment(request_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(confirm, request_id) for request_id in ("p-1", "p-2")]
        barrier.wait()
        results = [future.result() for future in futures]

    assert sorted(result["status"] for result in results) == ["paid", "protected"]
    assert adapter.submission_count == 1
    assert mandate["spent"] == "60.00"


def test_failed_settlement_releases_reservation_and_is_not_resubmitted(mandate):
    adapter = StubSettlementAdapter(result_status="failed")
    service = PaymentLifecycle(mandate, evaluator, adapter)
    service.create_request(request_for("p-fail", "80.00"))

    first = service.confirm_payment("p-fail")
    second = service.confirm_payment("p-fail")

    assert first == second
    assert first["status"] == "failed"
    assert adapter.submission_count == 1
    assert mandate["spent"] == "0.00"
    assert service._reserved_total == 0


def test_pending_settlement_keeps_budget_reserved_and_replays(mandate):
    adapter = StubSettlementAdapter(result_status="pending")
    service = PaymentLifecycle(mandate, evaluator, adapter)
    service.create_request(request_for("p-pending", "80.00"))

    first = service.confirm_payment("p-pending")
    second = service.confirm_payment("p-pending")

    assert first == second
    assert first["status"] == "pending"
    assert adapter.submission_count == 1
    assert service._reserved_total == 80


def test_missing_request_raises_key_error(mandate):
    service = PaymentLifecycle(mandate, evaluator)
    with pytest.raises(KeyError):
        service.confirm_payment("missing")
