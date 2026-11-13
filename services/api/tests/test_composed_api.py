"""Contract smoke test for the composed operator API."""
from fastapi.testclient import TestClient

from services.api.main import _lifecycle, _lock, app


def request_for(request_id, supplier="northstar-imports"):
    return {
        "id": request_id,
        "supplierId": supplier,
        "supplierName": "Northstar Imports",
        "invoiceNumber": f"INV-{request_id}",
        "amount": "25.00",
        "currency": "RLUSD",
        "destination": "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh",
        "createdAt": "2026-11-13T12:00:00Z",
    }


def test_overview_and_payables_share_lifecycle_state():
    client = TestClient(app)
    created = client.post("/payables", json=request_for("contract-overview-1"))
    assert created.status_code == 201
    overview = client.get("/overview").json()
    assert overview["simulated"] is True
    assert overview["network"] == "XRPL Testnet"
    assert any(item["request"]["id"] == "contract-overview-1"
               for item in overview["payables"])
    assert any(item["request"]["id"] == "contract-overview-1"
               for item in client.get("/payables").json())


def test_protected_request_never_has_settlement():
    client = TestClient(app)
    client.post("/payables", json=request_for(
        "contract-protected-1", supplier="not-approved"
    ))
    decision = client.post("/agent/runs", json=request_for(
        "contract-protected-1", supplier="not-approved"
    )).json()
    assert decision["outcome"] == "protected"
    result = client.post("/payments/contract-protected-1/confirm").json()
    assert result["status"] == "protected"
    assert result["settlement"] is None


def test_mandate_updates_and_payment_confirmations_share_one_lock():
    # A PUT /mandate update cannot race with the policy recheck and reservation
    # performed by POST /payments/{id}/confirm.
    assert _lifecycle._lock is _lock


def test_local_operator_ui_origin_can_call_api():
    client = TestClient(app)
    response = client.options(
        "/overview",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_xrpl_setup_reports_missing_backend_configuration(monkeypatch):
    import services.api.main as api_main

    monkeypatch.delenv("XRPL_WALLET_SEED", raising=False)
    monkeypatch.delenv("XRPL_SIMULATED", raising=False)
    monkeypatch.setattr(api_main, "_wallet_adapter", None)
    response = TestClient(app).get("/xrpl/status")
    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert "XRPL_WALLET_SEED" in response.json()["message"]


def test_trustline_setup_requires_confirmation_and_labels_simulation(monkeypatch):
    import services.api.main as api_main
    from services.xrpl.adapter import SimulatedXRPLAdapter

    adapter = SimulatedXRPLAdapter()
    monkeypatch.setattr(api_main, "_get_wallet_adapter", lambda: adapter)
    client = TestClient(app)
    denied = client.post("/xrpl/trustline", json={})
    assert denied.status_code == 409
    result = client.post("/xrpl/trustline", json={"confirmed": True})
    assert result.status_code == 200
    assert result.json()["simulated"] is True
    assert result.json()["trustline"] is True


def test_overview_uses_simulated_wallet_balance_without_claiming_ledger_evidence(monkeypatch):
    import services.api.main as api_main
    from services.xrpl.adapter import SimulatedXRPLAdapter

    monkeypatch.setattr(api_main, "_get_wallet_adapter", SimulatedXRPLAdapter)
    overview = TestClient(app).get("/overview").json()
    assert overview["balance"] == {
        "amount": "1000",
        "currency": "RLUSD",
        "source": "simulated",
    }
    assert overview["simulated"] is True
