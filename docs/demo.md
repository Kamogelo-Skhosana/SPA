# SPA Agentic Finance demo

## Story and timing

Northstar Imports is an SME operator workspace. Its owner delegates payable review to SPA, which proposes a payment. A deterministic mandate gateway checks supplier, amount, budget, expiry, and active status. An operator confirms permitted payments before an XRPL Testnet adapter signs and submits them.

- 0:00–0:25. Show Overview, the XRPL Testnet banner, and the simulated balance.
- 0:25–0:55. Open Mandate. Show Policy v3, 25,000 per-payment cap, 100,000 total budget, three approved suppliers, and 30 November 2026 expiry.
- 0:55–1:40. Run `req-approved-1048`. Cape Meridian Foods is approved and 18,450 is within the cap. Show agent proposal, policy result, operator confirmation, then a validated XRPL Testnet transaction. Show a hash only after real validation.
- 1:40–2:15. Run `req-protected-1047`. Kopano Packaging is not approved. Show the reason and no submit action. `req-over-limit-1049` provides a second refusal case.
- 2:15–3:00. Show Payables and Setup, validated testnet evidence if available, and the system boundary. The agent proposes, gateway authorizes, operator confirms, and XRPL adapter signs.

## Rehearsal

Use [the fixture](fixtures/demo.json) to rehearse every screen without live services. Its addresses are placeholders and must never be submitted. Replace fixture state with live API and validated XRPL Testnet data for the final settlement. If live settlement is unavailable, state that the outcome is simulated.

## Track fit

W3Node's Agentic Finance track calls for autonomous agents that transact, manage treasury, and execute financial decisions onchain. SPA demonstrates delegated payment review under an operator mandate and an onchain settlement step.

## Evidence

Use [the checklist](evidence.md) during the final run.
