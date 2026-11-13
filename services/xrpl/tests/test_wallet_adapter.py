from types import SimpleNamespace

import pytest

from services.xrpl.adapter import (
    RLUSD_CURRENCY,
    TESTNET_ISSUER,
    SimulatedXRPLAdapter,
    XRPLAdapterError,
    XRPLTestnetAdapter,
)


class FakeResponse:
    def __init__(self, result, successful=True):
        self.result = result
        self._successful = successful

    def is_successful(self):
        return self._successful


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


def test_wallet_status_reads_funded_xrp_balance():
    client = FakeClient([FakeResponse({"account_data": {"Balance": "2500000"}})])
    adapter = XRPLTestnetAdapter(seed="test-seed", client=client)

    # Replace only wallet derivation; no key material is used in this unit test.
    adapter.wallet = SimpleNamespace(classic_address="rTestAddress")
    assert adapter.wallet_status() == {
        "network": "testnet",
        "address": "rTestAddress",
        "funded": True,
        "xrpBalance": "2.5",
        "simulated": False,
    }


def test_unfunded_wallet_is_a_normal_setup_state():
    client = FakeClient([FakeResponse({"error": "actNotFound"}, successful=False)])
    adapter = XRPLTestnetAdapter(seed="test-seed", client=client)
    adapter.wallet = SimpleNamespace(classic_address="rTestAddress")

    result = adapter.wallet_status()

    assert result["funded"] is False
    assert result["xrpBalance"] == "0"


def test_rlusd_balance_matches_only_configured_issuer_and_currency():
    lines = [
        {"account": "rOtherIssuer", "currency": RLUSD_CURRENCY, "balance": "999"},
        {"account": TESTNET_ISSUER, "currency": RLUSD_CURRENCY, "balance": "12.5"},
    ]
    adapter = XRPLTestnetAdapter(
        seed="test-seed", client=FakeClient([FakeResponse({"lines": lines})])
    )
    adapter.wallet = SimpleNamespace(classic_address="rTestAddress")

    result = adapter.rlusd_balance()

    assert result["trustline"] is True
    assert result["balance"] == "12.5"
    assert result["issuer"] == TESTNET_ISSUER
    assert result["simulated"] is False


def test_absent_rlusd_trustline_returns_zero_balance():
    adapter = XRPLTestnetAdapter(
        seed="test-seed", client=FakeClient([FakeResponse({"lines": []})])
    )
    adapter.wallet = SimpleNamespace(classic_address="rTestAddress")

    result = adapter.rlusd_balance()

    assert result["trustline"] is False
    assert result["balance"] == "0"


def test_rpc_error_is_not_reported_as_unfunded_wallet():
    adapter = XRPLTestnetAdapter(
        seed="test-seed",
        client=FakeClient([FakeResponse({"error": "timeout"}, successful=False)]),
    )
    adapter.wallet = SimpleNamespace(classic_address="rTestAddress")

    with pytest.raises(XRPLAdapterError, match="timeout"):
        adapter.wallet_status()


def test_invalid_or_nonpositive_trustline_limit_is_rejected():
    adapter = XRPLTestnetAdapter(seed="test-seed", client=FakeClient([]))
    with pytest.raises(ValueError):
        adapter.setup_rlusd_trustline("0")


def test_simulator_explicitly_labels_all_outputs():
    adapter = SimulatedXRPLAdapter()
    assert adapter.wallet_status()["simulated"] is True
    assert adapter.rlusd_balance()["simulated"] is True
    assert adapter.setup_rlusd_trustline()["simulated"] is True


def test_adapter_requires_testnet_seed_and_never_has_mainnet_mode(monkeypatch):
    monkeypatch.setenv("XRPL_NETWORK", "mainnet")
    with pytest.raises(XRPLAdapterError, match="restricted"):
        XRPLTestnetAdapter(seed="test-seed")
