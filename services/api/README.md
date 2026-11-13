# API and policy gateway

Python FastAPI service. Own API routes, deterministic mandate evaluation, confirmation, idempotency, and persistence. Accept the shapes in `docs/contracts.md`. Re-evaluate policy before submitting a payment. Tests should cover approved supplier, limits, expiry, paused mandate, duplicate confirmation, and concurrent spending.
