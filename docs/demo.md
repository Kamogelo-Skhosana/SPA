# SPA Agentic Finance demo

## Problem, user, and value

SME finance operators spend time checking invoices, supplier eligibility, and payment limits. SPA prepares payable decisions while a deterministic mandate gateway checks supplier, amount, budget, expiry, and active status. The operator reviews the decision and explicitly confirms an allowed payment. This keeps delegated preparation separate from authority to sign.

## Three-minute walkthrough

- **0:00–0:25** — Show Overview and identify whether the current run is fixture, simulated API, or connected to XRPL Testnet. Call out the balance source shown in the UI.
- **0:25–0:55** — Open Mandate. Explain the supplier allowlist, payment cap, total budget, expiry, and pause control. API mode loads the backend mandate.
- **0:55–1:40** — Run an approved request such as `req-approved-1048`. Show the agent proposal and policy result, then explicitly confirm. Only call it a Testnet settlement when a validated ledger receipt, transaction hash, and ledger index are visible.
- **1:40–2:15** — Run `req-protected-1047` for an unapproved supplier and `req-over-limit-1049` for an over-cap amount. Show the exact policy reason and that no submit action is available.
- **2:15–3:00** — Show Payables and Setup, then explain the boundary: the agent proposes, the backend rechecks policy, the operator confirms, and only the backend adapter can sign.

## Run locally

From the repository root, install and start the API:

```sh
python -m pip install -r services/api/requirements.txt
uvicorn services.api.main:app --reload --port 8000
```

In a second terminal, start the UI:

```sh
cd apps/web
npm ci
VITE_SPA_API_URL=http://localhost:8000 npm run dev
```

For fixture-only rehearsal, omit `VITE_SPA_API_URL`. For API simulation, set `XRPL_SIMULATED=true` in the backend environment before starting the API. Simulated values and actions are not ledger activity. The API's initial mandate and payable list are process-local; prepare demo requests using the API and expect them to reset when the backend restarts.

## Testnet preparation and safety

For an actual Testnet run, set `XRPL_NETWORK=testnet` and `XRPL_WALLET_SEED` only in the backend environment. Never put the seed in frontend configuration, source control, screenshots, or chat. Open Setup to inspect public wallet status. Fund the account with Testnet XRP, then explicitly confirm the RLUSD TrustSet. Create a payable only with a real, valid Testnet destination; fixture values beginning with `rTEST_` are placeholders and must never be submitted.

A live approved payment needs a funded Testnet wallet, RLUSD issuer/trustline and balance, a real destination, and a validated ledger receipt. A protected request must stop before signing. If any prerequisite is absent, demonstrate the clearly labeled simulation and state that live settlement was not verified. Never present a simulated hash or balance as Testnet evidence.

## Track fit

The Agentic Finance track calls for agents that transact, manage treasury, and execute financial decisions onchain. SPA demonstrates autonomous payment preparation and decision support constrained by operator policy and human confirmation before an onchain action.

## Evidence

Use [the checklist](evidence.md) during the final run. Capture screenshots from the implementation being demonstrated and label each as fixture, simulated, or Testnet. Do not use mock evidence as proof of a live transaction.
