# Testing SPA

Run checks from the repository root before pushing:

```sh
npm ci
npm run check
npm test
```

When the React app has a package lock, run `npm ci`, `npm run build`, and `npm test --if-present` in `apps/web`.

For each Python service with `requirements.txt`, install its declared dependencies. Run `python -m pytest services/<name>/tests` for each service that has tests.

The CI workflow runs these checks for every feature branch push and PR. Keep the single required `check` job green. Add tests that exercise approved, protected, expired, over-budget, and duplicate payment requests. Confirm that a protected request never reaches signing, and that a validated testnet payment displays its transaction reference. Verify the responsive Overview, Payables, Mandate, and Setup views against the supplied screenshots and the design guide.

Fixture results must be labeled simulated. XRPL results count as confirmed only after ledger validation.
