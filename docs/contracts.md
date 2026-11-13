# Integration contract

All workstreams can use local fixtures while their implementation is in progress. Use decimal strings for amounts and ISO 8601 timestamps.

`PaymentRequest`: `{ id, supplierId, supplierName, invoiceNumber, amount, currency, destination, createdAt }`.

`Mandate`: `{ version, active, perPaymentLimit, totalBudget, spent, approvedSupplierIds, expiresAt }`.

`Decision`: `{ requestId, outcome: "allowed" | "protected", reasons: string[], mandateVersion }`.

`Settlement`: `{ requestId, status: "pending" | "validated" | "failed", txHash?, ledgerIndex?, simulated? }`. A non-simulated validated XRPL result includes a real transaction hash and validated ledger index. Simulated hashes and balances are never ledger evidence.

`PaymentRecord`: `{ request: PaymentRequest, status, decision: Decision | null, settlement: Settlement | null }`.

API routes:

- `GET /overview` returns the mandate, payment records, budget used, network, simulation mode, and optional wallet balance. Balance includes a source of `simulated` or `testnet`; a wallet read failure is reported as `balanceError` without taking down the payable dashboard.
- `GET /payables` and `POST /payables` list and create payable records.
- `GET /mandate` and confirmed `PUT /mandate` read and update the mandate.
- `POST /agent/runs` returns a deterministic `Decision`.
- `POST /payments/:id/confirm` rechecks policy and submits only an allowed payment.
- `GET /payments/:id` reads the current payment record.
- `POST /payments/:id/reconcile` checks a known pending transaction without resubmitting it.
- `GET /xrpl/status` reports whether wallet setup is configured, public wallet status, XRP balance, RLUSD trustline and balance, and whether values are simulated. It never returns the signing seed.
- Confirmed `POST /xrpl/trustline` submits the RLUSD TrustSet through the backend adapter. The caller must send `{"confirmed":true}`; setup failure is an error, not a success receipt.

The backend owns authorization and rechecks the current mandate at confirmation time. A protected decision must never reach signing. Keep signing keys inside the backend environment. Use `XRPL_SIMULATED=true` for clearly labeled local adapter rehearsal; use `XRPL_NETWORK=testnet` and configure a backend-only `XRPL_WALLET_SEED` for Testnet. Never use a fixture destination for a ledger transaction.
