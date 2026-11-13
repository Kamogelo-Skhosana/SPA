# XRPL RLUSD payment adapter

`XRPLPaymentAdapter` accepts an approved payment request and idempotency key,
constructs an RLUSD `Payment`, signs locally with the Testnet wallet loaded
from `XRPL_WALLET_SEED`, submits through `xrpl-py`, and returns a transaction
hash only when available. `lookup_transaction()` checks the XRPL Testnet
transaction record and reports validated, failed, or pending status.

The adapter accepts only `currency: "RLUSD"` requests and uses the Testnet
issuer and currency configured in `adapter.py`. It does not expose signing keys
in its responses, errors, or logs. Keep the signer inside the backend process;
agent/LLM code should call the payment service without access to
`XRPL_WALLET_SEED`.

## Idempotency and timeout behavior

The adapter binds each request ID to one idempotency key and payment payload.
Repeat calls replay the same result. If submission raises an exception after it
may have reached the ledger, the adapter returns `pending` and does not
automatically submit again. Check the account transaction history before
deciding what to do next.

The result cache is in memory and only protects retries in one running process.
Before multi-worker or restart-safe deployment, persist the idempotency record
and signed transaction identity in durable storage. Do not treat an unknown
timeout as a definitive failure.

## Simulation

Set `XRPL_SIMULATED=true` to use
`SimulatedXRPLPaymentAdapter`. It never connects to XRPL or signs anything.
Its output has `simulated: true` and a `SIMULATED-` hash, which must not be
presented as a real transaction hash or Testnet evidence.
