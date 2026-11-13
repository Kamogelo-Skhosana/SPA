from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from services.api import main
from services.api.policy import evaluate_payment


@pytest.fixture
def mandate():
    return {
        "version": 3,
        "active": True,
        "perPaymentLimit": "1000.00",
        "totalBudget": "2500.00",
        "spent": "1500.00",
        "approvedSupplierIds": ["supplier-a"],
        "expiresAt": "2027-01-01T00:00:00Z",
    }


@pytest.fixture
def request_data():
    return {
        "id": "pay-1",
        "supplierId": "supplier-a",
        "amount": "1000.00",
        "currency": "RLUSD",
        "destination": "rExample",
    }


def test_allowed_at_exact_payment_limit_and_budget(mandate, request_data):
    result = evaluate_payment(
        request_data, mandate, now=datetime(2026, 12, 1, tzinfo=timezone.utc)
    )
    assert result == {
        "requestId": "pay-1",
        "outcome": "allowed",
        "reasons": ["Payment complies with the active mandate."],
        "mandateVersion": 3,
    }


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"active": False}, "Mandate is paused."),
        ({"approvedSupplierIds": []}, "Supplier is not on the approved supplier list."),
        ({"perPaymentLimit": "999.99"}, "Payment exceeds the per-payment limit."),
        ({"totalBudget": "2499.99"}, "Payment exceeds the remaining mandate budget."),
        ({"expiresAt": "2026-11-30T23:59:59Z"}, "Mandate has expired."),
    ],
)
def test_policy_protects_when_each_rule_fails(mandate, request_data, change, expected):
    mandate.update(change)
    result = evaluate_payment(
        request_data, mandate, now=datetime(2026, 12, 1, tzinfo=timezone.utc)
    )
    assert result["outcome"] == "protected"
    assert expected in result["reasons"]


@pytest.mark.parametrize("amount", ["0", "-0.01", "NaN", "not-money"])
def test_invalid_or_nonpositive_amount_is_protected(mandate, request_data, amount):
    request_data["amount"] = amount
    result = evaluate_payment(
        request_data, mandate, now=datetime(2026, 12, 1, tzinfo=timezone.utc)
    )
    assert result["outcome"] == "protected"
    assert "Payment or mandate amount is invalid." in result["reasons"]


def test_invalid_expiry_is_protected(mandate, request_data):
    mandate["expiresAt"] = "not-a-date"
    result = evaluate_payment(
        request_data, mandate, now=datetime(2026, 12, 1, tzinfo=timezone.utc)
    )
    assert result["outcome"] == "protected"
    assert "Mandate expiry is invalid." in result["reasons"]


@pytest.fixture
def client(monkeypatch):
    original = {
        "version": 1,
        "active": True,
        "perPaymentLimit": "5000.00",
        "totalBudget": "20000.00",
        "spent": "0.00",
        "approvedSupplierIds": ["northstar-imports"],
        "expiresAt": "2027-01-01T00:00:00Z",
    }
    with main._lock:
        main._mandate.clear()
        main._mandate.update(original)
    yield TestClient(main.app)
    with main._lock:
        main._mandate.clear()
        main._mandate.update(original)


def test_get_mandate_returns_contract_shape(client):
    response = client.get("/mandate")
    assert response.status_code == 200
    assert response.json()["version"] == 1
    assert "approvedSupplierIds" in response.json()


def test_mandate_change_requires_operator_confirmation(client):
    payload = {
        "active": False,
        "perPaymentLimit": "5000.00",
        "totalBudget": "20000.00",
        "spent": "0.00",
        "approvedSupplierIds": ["northstar-imports"],
        "expiresAt": "2027-01-01T00:00:00Z",
    }
    response = client.put("/mandate", json=payload)
    assert response.status_code == 409
    assert client.get("/mandate").json()["version"] == 1


def test_confirmed_mandate_update_increments_version(client):
    payload = {
        "active": False,
        "perPaymentLimit": "5000.00",
        "totalBudget": "20000.00",
        "spent": "0.00",
        "approvedSupplierIds": ["northstar-imports"],
        "expiresAt": "2027-01-01T00:00:00Z",
        "confirmed": True,
    }
    response = client.put("/mandate", json=payload)
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert response.json()["active"] is False


def test_spent_cannot_exceed_budget(client):
    payload = {
        "active": True,
        "perPaymentLimit": "5000.00",
        "totalBudget": "100.00",
        "spent": "100.01",
        "approvedSupplierIds": ["northstar-imports"],
        "expiresAt": "2027-01-01T00:00:00Z",
        "confirmed": True,
    }
    response = client.put("/mandate", json=payload)
    assert response.status_code == 422


def test_agent_run_returns_protected_decision(client):
    response = client.post(
        "/agent/runs",
        json={"id": "pay-2", "supplierId": "unapproved", "amount": "25", "currency": "RLUSD"},
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "protected"
    assert response.json()["requestId"] == "pay-2"
