# Settlement integration boundary

`settlement.py` is a dependency-injected bridge for issue #19. The backend and XRPL teams can implement the two protocols without sharing each other's code directories.

The policy gateway must atomically recheck the mandate, reserve budget, and persist a stable idempotency key before returning `reserved`. A retry with the same key returns the existing `submitted` or `validated` reservation. Protected requests return `protected`, with no authorization token. The adapter signs only an authorized reservation.

The XRPL adapter must persist or deterministically reproduce the signed transaction before broadcasting so a crash between broadcast and `record_submission` cannot send a second payment on retry. `lookup` must verify a validated ledger result. A pending result retains the existing hash for later polling. The backend records final validation and updates the payable state.

The current bridge and tests use injected fakes. Wiring concrete gateway persistence and the XRPL testnet adapter remains part of issue #19 when those implementations land. The fixture tests do not establish a live settlement.
