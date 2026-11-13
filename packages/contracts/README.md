# Shared SPA contracts

The initial cross-service shapes and routes live in [docs/contracts.md](../../docs/contracts.md). Each implementation owns its local types or models and verifies they agree with that document. Propose a contract change in a small PR and update fixtures in the same change. Use decimal strings for money and stable request IDs for retries.
