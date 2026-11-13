from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

module_path = Path(__file__).resolve().parents[1] / "settlement.py"
spec = spec_from_file_location("spa_settlement", module_path)
settlement = module_from_spec(spec)
import sys
sys.modules[spec.name] = settlement
spec.loader.exec_module(settlement)


class Gateway:
    def __init__(self, reservation):
        self.reservation = reservation
        self.submissions = []
        self.validations = []

    def reserve(self, request_id, key):
        return self.reservation

    def record_submission(self, reservation, tx_hash):
        self.submissions.append(tx_hash)

    def record_validation(self, reservation, result):
        self.validations.append(result)


class Adapter:
    def __init__(self, result):
        self.result = result
        self.submissions = 0
        self.lookups = []

    def submit(self, reservation):
        self.submissions += 1
        return "TEST_HASH"

    def lookup(self, tx_hash):
        self.lookups.append(tx_hash)
        return self.result


def test_protected_request_never_reaches_adapter():
    gateway = Gateway(settlement.Reservation("r1", "key", "protected"))
    adapter = Adapter({"validated": True})
    assert settlement.settle("r1", "key", gateway, adapter)["status"] == "protected"
    assert adapter.submissions == 0
    assert adapter.lookups == []


def test_validated_reservation_is_not_submitted_again():
    gateway = Gateway(settlement.Reservation("r1", "key", "validated",
                                             transaction_hash="EXISTING_HASH"))
    adapter = Adapter({"validated": True})
    assert settlement.settle("r1", "key", gateway, adapter)["txHash"] == "EXISTING_HASH"
    assert adapter.submissions == 0


def test_new_authorized_reservation_records_validated_result():
    gateway = Gateway(settlement.Reservation("r1", "key", "reserved", "AUTH"))
    adapter = Adapter({"validated": True, "ledger_index": 123})
    result = settlement.settle("r1", "key", gateway, adapter)
    assert result == {"requestId": "r1", "status": "validated",
                      "txHash": "TEST_HASH", "ledgerIndex": 123}
    assert gateway.submissions == ["TEST_HASH"]
    assert len(gateway.validations) == 1


def test_pending_submission_only_looks_up_existing_hash():
    gateway = Gateway(settlement.Reservation("r1", "key", "submitted",
                                             transaction_hash="EXISTING_HASH"))
    adapter = Adapter({"validated": False})
    assert settlement.settle("r1", "key", gateway, adapter)["status"] == "pending"
    assert adapter.submissions == 0
    assert adapter.lookups == ["EXISTING_HASH"]
