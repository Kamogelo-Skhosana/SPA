# SPA submission draft — Agentic Finance

## One-line pitch

SPA is an SME payables workspace where an agent prepares payment requests, a deterministic operator mandate protects the budget, and an approved RLUSD payment can be submitted to XRPL Testnet after human confirmation.

## Problem and user

Small business operators spend time checking invoices, supplier eligibility, and payment limits. SPA helps an SME finance operator review payables by preparing structured requests and explaining policy decisions. The operator retains authority over any payment.

## What the demo shows

1. The operator reviews Overview, Payables, the active Mandate, and the Setup status.
2. An agent proposes a structured request. Deterministic policy checks supplier, amount, remaining budget, expiry, and active status.
3. A protected request stops before signing. An allowed request requires explicit operator confirmation.
4. The backend rechecks policy and hands an allowed request to the settlement adapter. Only a validated Testnet transaction with a real hash and ledger index counts as a live settlement.
5. A retry replays the same result. An ambiguous timeout remains pending for ledger investigation.

## Architecture and track fit

The React operator UI uses the shared API client. FastAPI owns mandate and payable state, runs deterministic rules, and controls payment and wallet setup confirmation. The XRPL adapter holds the backend-only Testnet signing seed. Agent output is a proposal, never signing authority. This fits Agentic Finance because autonomous preparation and decision support operate under financial policy and human confirmation before onchain action.

## Demo assets to capture

- Desktop and mobile captures of Overview, Payables, Mandate, and Setup, labeled fixture, API simulation, or Testnet.
- Approved request: policy result, confirmation action, and—only if actually validated—transaction hash, explorer URL, ledger index, issuer, amount, destination, and validated status.
- Protected request: failed rule and evidence that adapter submission did not occur.
- Refresh and retry: same payable and settlement, with no duplicate submission.
- Repository URL, reproducible setup steps, passing CI result, and a three-minute recording.

Use [the evidence checklist](evidence.md). Enter transaction identifiers only after observing the validated ledger result. Never paste a wallet seed or use fixture addresses on the ledger.

## Current implementation limits

The backend payable, mandate, wallet-adapter cache, and XRPL idempotency records are process-local. They are suitable for a single-process hackathon demonstration, not restart-safe or multi-worker payment processing. Simulated receipts and balances cannot serve as Testnet evidence. Fixture destinations are placeholders. A live Testnet transaction and live browser-to-ledger demonstration still require a funded Testnet account and must be captured before claiming end-to-end ledger validation.

## Three-minute recording outline

- **0:00–0:25** — Introduce the SME operator problem and show the current network and balance source.
- **0:25–0:55** — Show the mandate's supplier allowlist, payment cap, total budget, expiry, and pause control.
- **0:55–1:40** — Run an allowed request, inspect the policy decision, confirm it, and show a validated receipt only if obtained.
- **1:40–2:15** — Run an unapproved supplier and an over-cap amount; show both stopped before signing.
- **2:15–3:00** — Refresh and retry, explain the signing boundary, and identify the next step toward durable storage.

If no live settlement has been validated, show the clearly labeled simulation and state that limitation directly.
