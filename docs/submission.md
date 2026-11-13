# SPA submission draft — Agentic Finance

## One-line pitch

SPA is an SME payables workspace where an agent prepares payment requests, a deterministic operator mandate protects the budget, and approved RLUSD payments can settle on XRPL Testnet after human confirmation.

## Problem and user

Small business operators spend time checking invoices, supplier eligibility, and payment limits. A useful agent can prepare the work, but the operator needs a clear boundary around what it may pay. SPA is designed for an SME finance operator reviewing a queue of supplier payables.

## What the demo shows

1. The operator reviews Overview, Payables, and the active Mandate.
2. An agent proposes a structured request. The policy gateway explains whether the supplier, amount, remaining budget, expiry, and active status allow it.
3. A protected request stops before signing. An allowed request requires explicit operator confirmation.
4. The backend rechecks policy, reserves budget, and hands the approved request to the XRPL Testnet adapter. Only a validated transaction with a real hash and ledger index can be called a live settlement.
5. A retry replays the same result. An ambiguous timeout stays pending for ledger investigation.

## Architecture and track fit

The React operator UI uses the shared API client. FastAPI owns mandate and payable state, runs deterministic rules, and controls confirmation. The XRPL adapter alone has access to the Testnet signing seed. Agent output is a proposal, never a signing authority. This is an Agentic Finance workflow because autonomous preparation and decision support are constrained by an operator's financial policy before an onchain action.

## Demonstration evidence to attach

- Desktop and mobile captures of Overview, Payables, Mandate, and Setup, including simulated/Testnet labels.
- Allowed request: policy result, confirmation action, real transaction hash, explorer URL, ledger index, issuer, amount, destination, and validated result.
- Protected request: failed rule and evidence that the adapter submission count did not increase.
- Refresh and retry: same payable and transaction, with no duplicate submission.
- Repository URL, runnable setup steps, CI result, and a three-minute recording.

Use `docs/evidence.md` as the capture checklist. Enter links and hashes only after observing the running implementation. Never paste a wallet seed or use fixture addresses on the ledger.

## Current implementation limits

The backend payable and mandate stores and XRPL idempotency cache are process-local. They are suitable for a single-process hackathon demonstration, not restart-safe or multi-worker payment processing. The simulator uses `SIMULATED-` hashes and cannot serve as Testnet evidence. The supplied screen fixtures have placeholder destinations; replace them with funded Testnet accounts before any live run. The frontend screens and live wallet evidence must be verified before recording claims of a full browser-to-ledger demo.

## Three-minute recording outline

- **0:00–0:25** — Introduce the operator and the payables problem; point out Testnet and simulation labels.
- **0:25–0:55** — Show the mandate: supplier allowlist, per-payment cap, total budget, expiry, pause control.
- **0:55–1:40** — Run an allowed request, inspect the deterministic decision, confirm, and show the validated Testnet receipt if obtained.
- **1:40–2:15** — Run an unapproved supplier and an over-cap amount; show both stopped before signing.
- **2:15–3:00** — Retry and refresh, show the same state, explain the signing boundary and the next step toward durable storage.

If the live settlement has not been validated, show the simulated path and say so plainly in the recording and submission.
