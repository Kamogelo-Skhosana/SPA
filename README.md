# SPA

Agentic finance prototype for the W3Node hackathon. The operator reviews payables and sets a mandate. The agent evaluates requests against deterministic policy before a testnet payment is submitted.

## Try the demo

[Open SPA on Vercel](https://spa-fawn-iota.vercel.app/) to test payment review with sample invoices and simulated settlements.

## Workstreams

- `apps/web/` React operator dashboard with Overview, Payables, Mandate, and Setup screens.
- `services/api/` API and orchestration.
- `services/agent/` payment assessment and explanations.
- `services/xrpl/` testnet wallet, RLUSD trustline, and settlement adapter.
- `packages/contracts/` shared request, decision, and transaction schemas.
- `docs/` demo flow, API contract, and design references.

Build each workstream against fixtures and agreed contracts so teammates can work concurrently. Use butter cream, forest green, and hot pink accents. Clearly label simulated activity and testnet funds.
