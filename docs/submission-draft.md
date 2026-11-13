# SPA submission draft

## Title

SPA — an agent for supplier payments within your mandate

## Short description

SPA reviews SME payables, enforces operator-defined spending rules, and settles approved payments on XRPL Testnet.

## Problem

A small business can delegate repetitive payable review, but it needs clear limits on who can be paid, how much can be spent, and when authority expires. An agent that can submit payments without those controls creates an unacceptable operational risk.

## What SPA does

The operator sets an approved supplier list, per-payment cap, total budget, and expiry. SPA interprets a payment request, checks the mandate through a deterministic gateway, explains the decision, and asks the operator to confirm an allowed payment. The XRPL adapter submits an approved payment and verifies its ledger outcome. Requests outside the mandate are protected before signing.

## Demo flow

Show a Cape Meridian Foods payable within the mandate, then a Kopano Packaging request outside the supplier list. Display the protected refusal, then the approved request's operator confirmation and actual validated XRPL Testnet evidence when available. The timed run and fixtures are in `docs/demo.md`.

## How it was built

React and TypeScript operator workspace, Python agent and FastAPI policy gateway, XRPL Testnet settlement adapter, shared JSON contract, fixture-driven parallel development, and required GitHub CI. Update this section to match the final implementation and link its source code.

## Challenges and learning

The payment decision must be reproducible and enforceable separately from the agent's explanation. Duplicate confirmation and concurrent budget use require idempotent, atomic handling. A testnet transaction is a settlement demonstration, while sample balances and supplier records are labeled simulations.

## Evidence to add before submission

- Live demo URL and repository link
- Short video and screenshots from the implemented UI
- Validated XRPL Testnet transaction hash and explorer link
- Exact implementation status of agent, policy gateway, and wallet setup
- Team credits and final testing notes

This is a draft. Replace all evidence placeholders with verified outcomes before submitting.
