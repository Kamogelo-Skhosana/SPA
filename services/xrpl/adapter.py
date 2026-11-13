"""XRPL Testnet wallet, funding, RLUSD trustline, and balance adapter.

Private seeds are accepted only from XRPL_WALLET_SEED and are never returned
from the adapter. The simulator is opt-in and labels every result simulated.
"""
from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Any


TESTNET_RPC_URL = "https://s.altnet.rippletest.net:51234"
TESTNET_ISSUER = "rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV"
RLUSD_CURRENCY = "524C555344000000000000000000000000000000"


class XRPLAdapterError(RuntimeError):
    """Raised when wallet setup or a testnet read/write fails."""


class XRPLTestnetAdapter:
    """Connect to XRPL Testnet using a seed supplied through the environment."""

    def __init__(self, seed: str | None = None, client: Any | None = None, wallet: Any | None = None) -> None:
        if os.getenv("XRPL_NETWORK", "testnet").lower() != "testnet":
            raise XRPLAdapterError("This adapter is restricted to XRPL Testnet.")
        self._seed = seed or os.getenv("XRPL_WALLET_SEED")
        if not self._seed:
            raise XRPLAdapterError("Set XRPL_WALLET_SEED in the service environment.")
        self._client = client
        self._wallet = wallet

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
            raise XRPLAdapterError(f"{operation} returned an invalid XRPL response.")
        return result

    def wallet_status(self) -> dict[str, Any]:
        """Read account activation and XRP balance from the validated ledger."""
        from xrpl.models.requests import AccountInfo

        try:
            response = self.client.request(
                AccountInfo(account=self.address, ledger_index="validated")
            )
            result = self._result(response, "AccountInfo")
            if not getattr(response, "is_successful", lambda: False)():
                if result.get("error") == "actNotFound":
                    return {
                        "network": "testnet",
                        "address": self.address,
                        "funded": False,
                        "xrpBalance": "0",
                        "simulated": False,
                    }
                raise XRPLAdapterError(result.get("error_message") or result.get("error") or "Account lookup failed.")
            drops = Decimal(str(result["account_data"]["Balance"]))
            return {
                "network": "testnet",
                "address": self.address,
                "funded": True,
                "xrpBalance": format(drops / Decimal("1000000"), "f"),
                "simulated": False,
            }
        except XRPLAdapterError:
            raise
        except Exception as error:
            raise XRPLAdapterError(f"Could not read XRPL Testnet wallet status: {error}") from error

    def rlusd_balance(self) -> dict[str, Any]:
        """Read the RLUSD trustline balance; absent line means zero and not ready."""
        from xrpl.models.requests import AccountLines

        try:
            response = self.client.request(
                AccountLines(
                    account=self.address,
                    peer=TESTNET_ISSUER,
                    ledger_index="validated",
                )
            )
            result = self._result(response, "AccountLines")
            if not getattr(response, "is_successful", lambda: False)():
                raise XRPLAdapterError(result.get("error_message", "Trustline lookup failed."))
            lines = result.get("lines", [])
            matching = next(
                (
                    line for line in lines
                    if line.get("currency", "").upper() in {"RLUSD", RLUSD_CURRENCY}
                    and line.get("account") == TESTNET_ISSUER
                ),
                None,
            )
            return {
                "network": "testnet",
                "address": self.address,
                "issuer": TESTNET_ISSUER,
                "currency": RLUSD_CURRENCY,
                "trustline": matching is not None,
                "balance": str(matching.get("balance", "0")) if matching else "0",
                "simulated": False,
            }
        except XRPLAdapterError:
            raise
        except Exception as error:
            raise XRPLAdapterError(f"Could not read RLUSD balance: {error}") from error

    def setup_rlusd_trustline(self, limit: str = "1000000") -> dict[str, Any]:
        """Submit an operator-invoked TrustSet transaction on Testnet."""
        from xrpl.models.amounts import IssuedCurrencyAmount
        from xrpl.models.transactions import TrustSet
        from xrpl.transaction import submit_and_wait

        try:
            limit_value = Decimal(str(limit))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError("Trustline limit must be a positive decimal.") from error
        if not limit_value.is_finite() or limit_value <= 0:
            raise ValueError("Trustline limit must be a positive decimal.")

        status = self.wallet_status()
        if not status["funded"]:
            raise XRPLAdapterError("Fund the Testnet wallet with XRP before setting a trustline.")

        tx = TrustSet(
            account=self.address,
            limit_amount=IssuedCurrencyAmount(
                currency=RLUSD_CURRENCY,
                issuer=TESTNET_ISSUER,
                value=format(limit_value, "f"),
            ),
        )
        try:
            response = submit_and_wait(tx, self.client, self.wallet)
            result = self._result(response, "TrustSet")
            if not getattr(response, "is_successful", lambda: False)():
                raise XRPLAdapterError(
                    result.get("engine_result_message", result.get("error_message", "TrustSet failed."))
                )
            return {
                "network": "testnet",
                "address": self.address,
                "issuer": TESTNET_ISSUER,
                "currency": RLUSD_CURRENCY,
                "trustline": True,
                "txHash": result.get("hash"),
                "simulated": False,
            }
        except XRPLAdapterError:
            raise
        except Exception as error:
            raise XRPLAdapterError(f"Could not set RLUSD trustline: {error}") from error


class SimulatedXRPLAdapter:
    """Local-only fixture adapter with unmistakably simulated outputs."""

    def wallet_status(self) -> dict[str, Any]:
        return {
            "network": "simulated",
            "address": "SIMULATED-WALLET",
            "funded": True,
            "xrpBalance": "100",
            "simulated": True,
        }

    def rlusd_balance(self) -> dict[str, Any]:
        return {
            "network": "simulated",
            "address": "SIMULATED-WALLET",
            "issuer": TESTNET_ISSUER,
            "currency": RLUSD_CURRENCY,
            "trustline": True,
            "balance": "1000",
            "simulated": True,
        }

    def setup_rlusd_trustline(self, limit: str = "1000000") -> dict[str, Any]:
        return {
            "network": "simulated",
            "address": "SIMULATED-WALLET",
            "issuer": TESTNET_ISSUER,
            "currency": RLUSD_CURRENCY,
            "trustline": True,
            "simulated": True,
        }


def create_xrpl_adapter() -> XRPLTestnetAdapter | SimulatedXRPLAdapter:
    """Select simulation only when explicitly enabled."""
    if os.getenv("XRPL_SIMULATED", "").strip().lower() in {"1", "true", "yes"}:
        return SimulatedXRPLAdapter()
    return XRPLTestnetAdapter()
