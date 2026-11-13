# API and policy gateway

Python FastAPI service for mandate reads and confirmed updates, deterministic payment decisions, payable records, settlement confirmation, reconciliation, and XRPL wallet setup. State and idempotency records are in memory for this MVP process; they are not durable across restarts or shared across multiple workers.

Install dependencies and run from the repository root:

```sh
python -m pip install -r services/api/requirements.txt
uvicorn services.api.main:app --reload --port 8000
```

The browser development origins are allowed by default. Set `SPA_CORS_ORIGINS` to a comma-separated list of exact origins when hosting the UI elsewhere.

For a no-ledger rehearsal, set `XRPL_SIMULATED=true` in the backend environment. Status, balances, and trustline setup will be explicitly labeled simulated and will not submit a transaction. For Testnet, set `XRPL_NETWORK=testnet` and configure `XRPL_WALLET_SEED` only in the backend environment. Fund the account with Testnet XRP before creating a trustline. The seed is never returned to the browser or agent.

`GET /xrpl/status` reads the public account status and RLUSD line from the validated Testnet ledger. `POST /xrpl/trustline` requires `{"confirmed":true}` and invokes the operator-requested TrustSet. Wallet/setup errors are reported as errors; they do not create a successful receipt. Keep the signing key out of source control, browser settings, logs, and screenshots.

See [the contract](../../docs/contracts.md) for request and response shapes. Confirmation always re-evaluates the current mandate. Protected requests do not reach the adapter. Pending XRPL outcomes are reconciled by transaction lookup; they are not resubmitted automatically.
