from types import SimpleNamespace

import pytest
import xrpl.transaction

from services.xrpl.payment import (
    SimulatedXRPLPaymentAdapter,
    XRPLPaymentAdapter,
    XRPLPaymentError,
)


TEST_ADDRESS = "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"


class FakeResponse:
    def __init__(self, result, successful=True):
        self.result = result
        self._successful = successful

    def is_successful(self):
        return self._successful


class FakeClient:
    def __init__(self, response=None):
        self.response = response
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return self.response


def fake_wallet():
    return SimpleNamespace(classic_address=TEST_ADDRESS)


def payment_request(request_id="pay-1", amount="10.25", currency="RLUSD"):
    return {
        "id": request_id,
        "supplierId": "supplier-a",
        "supplierName": "Supplier A",
        "invoiceNumber": "INV-1",
        "amount": amount,
        "currency": currency,
        "destination": TEST_ADDRESS,
        "createdAt": "2026-11-13T12:00:00Z",
    }


def test_validated_payment_returns_hash_and_ledger(monkeypatch):
    calls = []
    monkeypatch.setattr(
        xrpl.transaction,
        "submit_and_wait",
        lambda tx, client, wallet: (
            calls.append(tx)
            or FakeResponse({"hash": "ABC123", "validated": True, "ledger_index": 77})
        ),
    )
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )

    result = adapter.submit_payment(payment_request(), idempotency_key="pay-1-key")

    assert result == {
        "requestId": "pay-1",
        "status": "validated",
        "simulated": False,
        "txHash": "ABC123",
        "ledgerIndex": 77,
    }
    assert len(calls) == 1


def test_duplicate_submission_replays_cached_result(monkeypatch):
    calls = []
    monkeypatch.setattr(
        xrpl.transaction,
        "submit_and_wait",
        lambda tx, client, wallet: (
            calls.append(tx)
            or FakeResponse({"hash": "ABC123", "validated": True})
        ),
    )
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )
    request = payment_request()

    first = adapter.submit_payment(request, idempotency_key="pay-1-key")
    second = adapter.submit_payment(request, idempotency_key="pay-1-key")

    assert first == second
    assert len(calls) == 1


def test_timeout_is_pending_and_never_retried_automatically(monkeypatch):
    calls = []

    def timeout(*_args, **_kwargs):
        calls.append(1)
        raise TimeoutError("ledger timeout")

    monkeypatch.setattr(xrpl.transaction, "submit_and_wait", timeout)
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )

    first = adapter.submit_payment(payment_request(), idempotency_key="pay-1-key")
    second = adapter.submit_payment(payment_request(), idempotency_key="pay-1-key")

    assert first["status"] == "pending"
    assert "before retrying" in first["error"]
    assert first == second
    assert len(calls) == 1


def test_failed_validated_transaction_is_reported(monkeypatch):
    monkeypatch.setattr(
        xrpl.transaction,
        "submit_and_wait",
        lambda *_args, **_kwargs: FakeResponse(
            {
                "hash": "BAD123",
                "validated": True,
                "ledger_index": 80,
                "meta": {"TransactionResult": "tecPATH_DRY"},
            },
            successful=False,
        ),
    )
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )

    result = adapter.submit_payment(
        payment_request(), idempotency_key="pay-1-key"
    )

    assert result["status"] == "failed"
    assert result["error"] == "tecPATH_DRY"


def test_rejects_unsupported_currency_and_invalid_amount():
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )
    with pytest.raises(XRPLPaymentError, match="Only RLUSD"):
        adapter.submit_payment(
            payment_request(currency="XRP"), idempotency_key="key-1"
        )
    with pytest.raises(XRPLPaymentError, match="positive decimal"):
        adapter.submit_payment(
            payment_request(amount="-1"), idempotency_key="key-2"
        )


def test_rejects_reusing_request_id_with_different_idempotency_key(monkeypatch):
    monkeypatch.setattr(
        xrpl.transaction,
        "submit_and_wait",
        lambda *_args, **_kwargs: FakeResponse({"hash": "ABC123", "validated": True}),
    )
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )
    adapter.submit_payment(payment_request(), idempotency_key="first-key")
    with pytest.raises(XRPLPaymentError, match="already bound"):
        adapter.submit_payment(payment_request(), idempotency_key="second-key")


def test_transaction_lookup_distinguishes_validated_pending_and_failed():
    client = FakeClient(
        FakeResponse(
            {
                "hash": "ABC123",
                "validated": True,
                "ledger_index": 77,
                "meta": {"TransactionResult": "tesSUCCESS"},
            }
        )
    )
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=client, wallet=fake_wallet()
    )
    assert adapter.lookup_transaction("ABC123")["status"] == "validated"

    client.response = FakeResponse({"error": "txnNotFound"}, successful=False)
    assert adapter.lookup_transaction("NOTFOUND")["status"] == "pending"

    client.response = FakeResponse(
        {
            "hash": "BAD123",
            "validated": True,
            "meta": {"TransactionResult": "tecPATH_DRY"},
        }
    )
    assert adapter.lookup_transaction("BAD123")["status"] == "failed"


def test_simulator_marks_receipt_and_replays():
    adapter = SimulatedXRPLPaymentAdapter()
    first = adapter.submit_payment(payment_request(), idempotency_key="key-1")
    second = adapter.submit_payment(payment_request(), idempotency_key="key-1")
    assert first == second
    assert first["simulated"] is True
    assert first["txHash"].startswith("SIMULATED-")


def test_mainnet_disabled():
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )
    assert adapter.address == TEST_ADDRESS


def test_idempotency_key_cannot_be_reused_for_changed_payment(monkeypatch):
    monkeypatch.setattr(
        xrpl.transaction,
        "submit_and_wait",
        lambda *_args, **_kwargs: FakeResponse({"hash": "ABC123", "validated": True}),
    )
    adapter = XRPLPaymentAdapter(
        seed="test-seed", client=FakeClient(), wallet=fake_wallet()
    )
    adapter.submit_payment(payment_request(), idempotency_key="same-key")
    changed = payment_request(amount="11.00")
    with pytest.raises(XRPLPaymentError, match="different payment data"):
        adapter.submit_payment(changed, idempotency_key="same-key")
