# SPA pitch

Small businesses need to pay suppliers quickly without giving an automated agent unlimited access to their money. SPA lets an operator define a payment mandate, then delegates payable review to an agent. The agent reads a request and proposes an action. A deterministic policy gateway checks the supplier, payment cap, remaining budget, mandate status, and expiry. The operator confirms an eligible payment. An XRPL Testnet adapter submits it and returns a verifiable result.

The demo starts with Northstar Imports and a payable from Cape Meridian Foods for 18,450 RLUSD. SPA identifies the supplier and invoice, checks Policy v3, and asks the operator to confirm. A separate request from Kopano Packaging is protected because the supplier is outside the mandate. The refusal happens before signing.

The agent makes the workflow faster and explains what it found. The mandate sets its authority. A validated XRPL transaction provides settlement evidence. The MVP focuses on this narrow flow and clearly marks sample data and testnet activity. Business verification, real currency conversion, and production financial operations are future work.

## Judge questions

**Why an agent?** It turns a payable instruction into a structured proposal, reviews the context, and explains the outcome while preserving operator control.

**Why blockchain?** The approved testnet payment can have a shared, independently verifiable settlement record. The protected request demonstrates that policy is enforced before that action.

**What prevents unauthorized spending?** Deterministic policy checks, operator confirmation, idempotent backend processing, and a signing adapter outside the agent.

**What is live?** Show only actual validated transaction details as live. The Northstar fixture, balances, and placeholder addresses are simulated until connected to the implemented services.
