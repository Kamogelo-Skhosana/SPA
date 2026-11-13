# XRPL Testnet adapter

This adapter provides XRPL Testnet wallet status, XRP funding lookup, RLUSD
trustline setup, and RLUSD balance lookup using `xrpl-py`. It never connects
to Mainnet. Testnet funds have no real-world value.

## Testnet configuration

The RLUSD values below are from
[Ripple's official RLUSD XRPL documentation](https://docs.ripple.com/products/stablecoin/developer-resources/rlusd-on-the-xrpl):

- Network: XRP Ledger Testnet
- JSON-RPC: `https://s.altnet.rippletest.net:51234`
- RLUSD issuer: `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV`
- RLUSD currency (160-bit hex): `524C555344000000000000000000000000000000`

Check the issuer/currency against Ripple's documentation before using a
different network. Testnet ledgers and balances may be reset.

## Environment

For a real Testnet wallet, set these values in the API service environment:

```text
XRPL_NETWORK=testnet
XRPL_WALLET_SEED=<testnet wallet seed>
XRPL_SIMULATED=false
```

Never commit the seed or return it from an API. The adapter reports the wallet's
classic address, funding status, and XRP balance, but not private key material.
An unfunded wallet is returned as `funded: false`; transport or ledger errors
are raised distinctly instead of being reported as an unfunded wallet.

To use local fixtures without connecting to XRPL, set
`XRPL_SIMULATED=true`. Every simulator response contains `simulated: true`
and a clearly fake wallet address.

## Trustline

Call `setup_rlusd_trustline()` only as an explicit operator action. The wallet
must already be funded with Testnet XRP. The XRPL ledger enforces its current
reserve requirements; check the current Testnet reserve before submitting.
TrustSet returns the validated transaction hash when successful.

The account-lines reader identifies the trustline only when both the RLUSD
currency and configured Testnet issuer match, and returns a zero balance when
the line has not been created yet.
