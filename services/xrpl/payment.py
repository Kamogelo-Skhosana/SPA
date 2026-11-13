"""RLUSD Testnet payment adapter with an isolated signing boundary.

The seed is loaded from XRPL_WALLET_SEED and is never logged or returned.
Idempotency state is process-local; production must persist it before enabling
multi-worker or restart-safe payment submission.
"""
from __future__ import annotations

import os
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from threading import RLock
from typing import Any


TESTNET_RPC_URL = "https://s.altnet.rippletest.net:51234"
TESTNET_ISSUER = "rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV"
RLUSD_CURRENCY = "524C555344000000000000000000000000000000"


class XRPLPaymentError(RuntimeError):
    """Raised for invalid payment input or ledger lookup errors."""


class XRPLPaymentAdapter:
    """Build, sign, submit, and verify RLUSD payments on XRPL Testnet."""

    def __init__(self, seed: str | None = None, client: Any | None = None, wallet: Any | None = None):
        if os.getenv("XRPL_NETWORK", "testnet").lower() != "testnet":
            raise XRPLPaymentError("Payment adapter is restricted to XRPL Testnet.")
        self._seed = seed or os.getenv("XRPL_WALLET_SEED")
        if not self._seed:
            raise XRPLPaymentError("Set XRPL_WALLET_SEED in the service environment.")
        self._client = client
        self._wallet = wallet
        self._lock = RLock()
        self._results: dict[str, dict[str, Any]] = {}
        self._request_keys: dict[str, str] = {}

    @property
    def client(self):
        if self._client is None:
            from xrpl.clients import JsonRpcClient
            self._client = JsonRpcClient(TESTNET_RPC_URL)
        return self._client

    @property
    def wallet(self):
        if self._wallet is not None:
            return self._wallet
        from xrpl.wallet import Wallet
        return Wallet.from_seed(self._seed)

    @property
    def address(self) -> str:
        wallet = self.wallet
        return getattr(wallet, "classic_address", None) or wallet.address

    @staticmethod
    def _result(response: Any, operation: str) -> dict[str, Any]:
        result = getattr(response, "result", None)
        if not isinstance(result, dict):
            raise XRPLPaymentError(f"{operation} returned an invalid XRPL response.")
        return result

    @staticmethod
    def _response_hash(result: dict[str, Any]) -> str | None:
        return result.get("hash") or result.get("tx_json", {}).get("hash")

    @staticmethod
    def _result_meta(result: dict[str, Any]) -> dict[str, Any]:
        meta = result.get("meta", {})
        return meta if isinstance(meta, dict) else {}

    def submit_payment(
        self, request: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        """Submit once per key and cache pending/terminal results for safe retries."""
        from xrpl.models.amounts import IssuedCurrencyAmount
        from xrpl.models.transactions import Payment
        from xrpl.transaction import submit_and_wait

        request_id = str(request.get("id", ""))
        if not request_id or not idempotency_key or not idempotency_key.strip():
            raise XRPLPaymentError("Request id and idempotency key are required.")
        destination = request.get("destination")
        if not isinstance(destination, str) or not destination.strip():
            raise XRPLPaymentError("Payment destination is required.")
        if str(request.get("currency", "")).upper() != "RLUSD":
            raise XRPLPaymentError("Only RLUSD payments are supported by this adapter.")
        try:
            amount = Decimal(str(request["amount"]))
        except (KeyError, InvalidOperation, TypeError, ValueError) as error:
            raise XRPLPaymentError("Payment amount must be a positive decimal.") from error
        if not amount.is_finite() or amount <= 0:
            raise XRPLPaymentError("Payment amount must be a positive decimal.")

        payment = Payment(
            account=self.address,
            destination=destination,
            amount=IssuedCurrencyAmount(
                currency=RLUSD_CURRENCY,
                issuer=TESTNET_ISSUER,
                value=format(amount, "f"),
            ),
        )

        with self._lock:
            existing_key = self._request_keys.get(request_id)
            if existing_key and existing_key != idempotency_key:
                raise XRPLPaymentError("This request id is already bound to another idempotency key.")
            self._request_keys[request_id] = idempotency_key
            if idempotency_key in self._results:
                return deepcopy(self._results[idempotency_key])

            # Persist a pending marker before any network submission. A timeout
            # is ambiguous, so this process must not blindly submit the payment
            # again on retry.
            pending = {
                "requestId": request_id,
                "status": "pending",
                "simulated": False,
            }
            self._results[idempotency_key] = pending
            try:
                response = submit_and_wait(payment, self.client, self.wallet)
                result = self._result(response, "Payment")
                tx_hash = self._response_hash(result)
                ledger_index = result.get("ledger_index") or result.get("validated_ledger_index")
                validated = result.get("validated") is True
                successful = getattr(response, "is_successful", lambda: False)()

                outcome: dict[str, Any] = {
                    "requestId": request_id,
                    "status": "validated" if validated and successful else (
                        "failed" if validated and not successful else "pending"
                    ),
                    "simulated": False,
                }
                if tx_hash:
                    outcome["txHash"] = tx_hash
                if ledger_index is not None:
                    outcome["ledgerIndex"] = ledger_index
                if outcome["status"] == "failed":
                    meta = self._result_meta(result)
                    outcome["error"] = meta.get(
                        "TransactionResult",
                        result.get("engine_result_message", "XRPL transaction failed."),
                    )
                self._results[idempotency_key] = outcome
                return deepcopy(outcome)
            except Exception as error:
                # Submission may have reached the network before a timeout.
                # Keep the pending result; reconcile by transaction lookup.
                pending["error"] = f"Submission outcome unknown; reconcile before retrying: {error}"
                self._results[idempotency_key] = pending
                return deepcopy(pending)

    def lookup_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Read the transaction from XRPL and report only validated outcomes."""
        from xrpl.models.requests import Tx

        if not tx_hash or tx_hash.startswith("SIMULATED-"):
            raise XRPLPaymentError("A real XRPL transaction hash is required.")
        try:
            response = self.client.request(Tx(transaction=tx_hash))
            result = self._result(response, "Transaction lookup")
            if not getattr(response, "is_successful", lambda: False)():
                if result.get("error") in {"txnNotFound", "transactionNotFound"}:
                    return {
                        "status": "pending",
                        "txHash": tx_hash,
                        "simulated": False,
                    }
                raise XRPLPaymentError(
                    result.get("error_message", "Transaction lookup failed.")
                )

            validated = result.get("validated") is True
            meta = self._result_meta(result)
            engine_result = meta.get("TransactionResult")
            if not validated:
                status = "pending"
            elif engine_result and engine_result != "tesSUCCESS":
                status = "failed"
            else:
                status = "validated"

            output: dict[str, Any] = {
                "status": status,
                "txHash": tx_hash,
                "simulated": False,
            }
            ledger_index = result.get("ledger_index")
            if ledger_index is not None:
                output["ledgerIndex"] = ledger_index
            if engine_result and status == "failed":
                output["error"] = engine_result
            return output
        except XRPLPaymentError:
            raise
        except Exception as error:
            raise XRPLPaymentError(f"Transaction lookup failed: {error}") from error


class SimulatedXRPLPaymentAdapter:
    """Deterministic local payment fixture; it never signs or connects."""

    def __init__(self) -> None:
        self._results: dict[str, dict[str, Any]] = {}

    def submit_payment(
        self, request: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        if idempotency_key in self._results:
            return deepcopy(self._results[idempotency_key])
        digest = sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
        result = {
            "requestId": request["id"],
            "status": "validated",
            "txHash": f"SIMULATED-{digest}",
            "simulated": True,
        }
        self._results[idempotency_key] = result
        return deepcopy(result)


def create_payment_adapter() -> XRPLPaymentAdapter | SimulatedXRPLPaymentAdapter:
    if os.getenv("XRPL_SIMULATED", "").strip().lower() in {"1", "true", "yes"}:
        return SimulatedXRPLPaymentAdapter()
    return XRPLPaymentAdapter()
