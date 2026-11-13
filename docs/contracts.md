# Integration contract

All workstreams can use local fixtures while their implementation is in progress. Use decimal strings for amounts and ISO 8601 timestamps.

`PaymentRequest`: `{ id, supplierId, supplierName, invoiceNumber, amount, currency, destination, createdAt }`.

`Mandate`: `{ version, active, perPaymentLimit, totalBudget, spent, approvedSupplierIds, expiresAt }`.

`Decision`: `{ requestId, outcome: "allowed" | "protected", reasons: string[], mandateVersion }`.

`Settlement`: `{ requestId, status: "pending" | "validated" | "failed", txHash?, ledgerIndex? }`.

API routes: `GET /overview`, `GET /payables`, `GET /mandate`, `PUT /mandate`, `POST /agent/runs`, `POST /payments/:id/confirm`, `GET /payments/:id`. A protected decision must never reach signing. The backend rechecks policy at confirmation time.
