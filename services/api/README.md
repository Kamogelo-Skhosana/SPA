# API and policy gateway

Python FastAPI service for mandate reads and confirmed updates, deterministic payment decisions, payable records, settlement confirmation, and reconciliation. State is in memory for this MVP process; it is not durable across restarts or shared across multiple workers.

Install dependencies and run from the repository root:

```sh
python -m pip install -r services/api/requirements.txt
uvicorn services.api.main:app --reload --port 8000
```

The browser development origins are allowed by default. Set `SPA_CORS_ORIGINS` to a comma-separated list of exact origins when hosting the UI elsewhere. Set `XRPL_WALLET_SEED` only in the backend environment to enable the Testnet signing adapter. Without it, settlement uses an explicitly simulated adapter. The agent and browser never receive the signing seed.

See [the contract](../../docs/contracts.md) for request and response shapes. Confirmation always re-evaluates the current mandate. Protected requests do not reach the adapter. Pending XRPL outcomes are reconciled by transaction lookup; they are not resubmitted automatically.