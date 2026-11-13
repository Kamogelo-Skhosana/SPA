# SPA rehearsal record

This guide separates reproducible fixture/API rehearsals from a live Testnet run. Fixture and simulated results do not prove ledger activity.

## Fixture rehearsal

1. Start the UI without `VITE_SPA_API_URL`.
2. Open Overview and identify fixture labels and simulated balances.
3. Open Mandate and review the supplier list, limits, expiry, and pause control.
4. Run `req-approved-1048`; verify the policy decision and explicit operator confirmation.
5. Run `req-protected-1047` and `req-over-limit-1049`; verify the reason and that neither has a submit action.
6. Retry and refresh. Record what the fixture preserves, and label all results as simulated.

## API simulation rehearsal

1. Start the backend using [the API run steps](../services/api/README.md) with `XRPL_SIMULATED=true`; start the UI with `VITE_SPA_API_URL=http://localhost:8000`.
2. Confirm Setup identifies a simulated wallet. Inspect wallet status and the simulated RLUSD balance.
3. Use Setup to request the simulated trustline and confirm the dialog. Verify the receipt is explicitly labeled simulated.
4. Create API payables with a valid Testnet-style destination only for a future real run. Run an allowed payment and a protected payment, then refresh and retry. Verify protected requests never call settlement and retries do not duplicate a simulated request.
5. Capture screenshots or a recording and label them API simulation.

## Live XRPL Testnet run

1. Configure `XRPL_NETWORK=testnet` and a funded `XRPL_WALLET_SEED` in the backend environment only. Do not put the seed in frontend variables or commit it.
2. Load Setup status; verify the public account address and XRP balance against Testnet.
3. Confirm the RLUSD TrustSet in the UI and record its validated transaction hash.
4. Create an approved payable using a real Testnet destination. Confirm it once, record the validated receipt and ledger index, then refresh/retry and verify the same result without a second payment.
5. Run an unapproved or over-limit payable and verify no signing/submission occurs.
6. Record screenshots, timestamps, transaction hashes, ledger index, issuer, amount, destination, and explorer URL in [the evidence checklist](evidence.md). Remove any private credentials from captured material.

## Current result and unresolved gap

The repository contains the implementation and instructions for the API simulation and Testnet paths. This session does not have a funded Testnet account or operator seed, so it cannot produce or claim a real validated transaction hash, live browser-to-ledger screenshots, or a live retry record. Keep those evidence items open until the live steps above are performed. The simulator is not Testnet evidence.
