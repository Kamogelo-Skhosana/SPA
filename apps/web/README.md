# SPA operator dashboard

The React + TypeScript workspace runs in fixture mode by default. To connect it to the FastAPI service, start the backend from the repository root, then set the Vite API URL before starting the UI:

```sh
python -m pip install -r services/api/requirements.txt
uvicorn services.api.main:app --reload --port 8000
```

In a second terminal:

```sh
cd apps/web
npm ci
VITE_SPA_API_URL=http://localhost:8000 npm run dev
```

On PowerShell, set it with `$env:VITE_SPA_API_URL="http://localhost:8000"` before `npm run dev`. The API uses explicit CORS origins from `SPA_CORS_ORIGINS`; local Vite origins are allowed by default. Set that variable to a comma-separated list of exact origins for another deployment.

When configured, the UI uses API data and does not silently fall back to fixtures if requests fail. A blank API returns an empty payables list; create requests with `POST /payables`. Use a real destination for Testnet configuration. Without `XRPL_WALLET_SEED`, payment settlement is explicitly simulated unless the service is unconfigured. With a Testnet seed, the backend rechecks policy before its signing adapter is called.

API mode loads overview, payables, and mandate state, and routes agent decisions, explicit confirmation, and payment reconciliation through the shared client. The Setup screen reads `/xrpl/status`; it displays only public wallet state. It requires an explicit operator confirmation before requesting a TrustSet through the backend. Set `XRPL_SIMULATED=true` in the backend for an adapter rehearsal without ledger activity. For a real Testnet run, set `XRPL_NETWORK=testnet`, keep `XRPL_WALLET_SEED` on the backend only, and fund the account with Testnet XRP. Never enter the seed in the browser. If the API does not provide an account balance, the UI reports it as unavailable rather than substituting fixture balance data.

Without `VITE_SPA_API_URL`, hash routes (`#/overview`, `#/payables`, `#/mandate`, `#/setup`) use the local fixture adapter. Use Ctrl/Cmd+K for page search; Escape closes search and mobile navigation. Fixture receipts and balances are simulated, not XRPL Testnet evidence.

Clear the `spa.simulated.settlements.v1` local-storage key in browser developer tools to reset fixture rehearsals.
