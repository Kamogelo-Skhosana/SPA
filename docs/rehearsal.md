# SPA rehearsal record

Run `npm ci && npm test` on the feature branch. The fixture rehearsal checks the allowed Cape Meridian request, the unapproved Kopano request, the over-cap Cape Meridian request, and simulation labels. It does not submit a payment.

## Operator walkthrough

1. Open Overview and verify the XRPL Testnet banner and simulated balance.
2. Open Mandate and verify Policy v3 limits, allowlist, expiry, and pause control.
3. Run `req-approved-1048`. Verify the policy outcome is allowed, then require an explicit operator confirmation before any submission.
4. Run `req-protected-1047`. Verify the supplier refusal and confirm that no signing or submission event exists.
5. Retry the protected request and refresh the UI. The result remains protected.
6. Once the actual adapter lands, submit the approved request on XRPL Testnet. Record the validated hash, ledger index, currency issuer, timestamp, and explorer URL in `docs/evidence.md`. Retry confirmation and confirm the same payment is returned.
7. Run the browser-to-API-to-ledger flow on desktop and mobile layouts, then capture screenshots or a short recording.

## Current result

Fixture policy cases are covered by `scripts/rehearse.test.mjs`. Live API, signing, ledger validation, refresh persistence, and screenshots remain pending implemented services and UI. Do not mark issue #24 complete until actual evidence is recorded.
