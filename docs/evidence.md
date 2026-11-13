# Demo evidence checklist

Capture only from the running implementation. Label every capture as fixture, API simulation, or XRPL Testnet.

- [ ] Overview screenshot shows the network and whether the balance is simulated or from Testnet.
- [ ] Mandate screenshot shows the payment cap, total budget, suppliers, expiry, and active status.
- [ ] Approved request trace shows extracted fields, policy checks, explicit operator confirmation, and final status.
- [ ] Real settlement evidence includes Testnet network, transaction hash, explorer URL, validated status, ledger index, amount, currency, issuer, destination, and timestamp.
- [ ] Protected request trace shows the exact failed rule and evidence that no signing or submission occurred.
- [ ] Refresh and retry show a consistent request and settlement without a duplicate payment.
- [ ] Setup screen distinguishes fixture progress from API simulation and actual wallet/trustline state.
- [ ] Mobile and desktop captures show usable navigation and readable status.
- [ ] Demo recording follows the timed script and labels each simulation.

## Unresolved evidence

No live Testnet transaction hash, ledger index, browser-to-ledger capture, or live retry trace has been recorded in this repository yet. The current work environment does not have a funded Testnet wallet configured. Complete these items during a live rehearsal before claiming full end-to-end Testnet validation. Never include the wallet seed in evidence or use fixture addresses on the ledger.
