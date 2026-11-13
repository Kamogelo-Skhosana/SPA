# SPA operator dashboard

Fixture-backed React + TypeScript workspace. No live backend or wallet dependency.

```sh
cd apps/web
npm ci
npm run dev
npm run build
npm test
```

Open the local Vite URL. Hash routes: `#/overview`, `#/payables`, `#/mandate`, `#/setup`. Use Ctrl/Cmd+K for page search; Escape closes search and mobile navigation.

Overview and Payables show simulated balance, search, status filters, and request details. Run the agent for INV-2026-1048, review its allowed decision, explicitly confirm the simulation, then check simulated status. Its paid status and illustrative receipt persist in browser local storage. INV-2026-1047 and INV-2026-1049 are protected and never offer submission. Simulation expiry uses the fixture mandate's real expiry date.

Mandate pause/resume and wallet rehearsal are local mock actions. Wallet steps never claim live funding, a trustline, or connectivity. No fixture destination can be used for a real payment. All receipts and balances are simulated, including those labeled validated within the simulation; none is XRPL Testnet evidence.

Tests exercise keyboard focus, cancellation, policy refusal, forged approval rejection, explicit confirmation, persistence, failure/retry, dashboard updates, filters, loading, empty and error states. No screenshot assets were supplied in the repository; styling follows `docs/design.md`.

Clear the `spa.simulated.settlements.v1` local-storage key in browser developer tools to reset payment rehearsals. Backend integration is tracked separately by #20.
