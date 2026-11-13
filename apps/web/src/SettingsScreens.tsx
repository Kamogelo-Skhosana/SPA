import { useEffect, useState } from 'react';
import ConfirmDialog from './ConfirmDialog';
import { amount, fixtureSettings, initialMandate, supplierName, type SettingsAdapter, type WalletSetupStatus } from './settings';

export default function SettingsScreens({ screen, adapter = fixtureSettings }: {
  screen: 'mandate' | 'setup';
  adapter?: SettingsAdapter;
}) {
  const [mandate, setMandate] = useState(initialMandate);
  const [loading, setLoading] = useState(screen === 'mandate' && Boolean(adapter.loadMandate));
  const [loadedMandate, setLoadedMandate] = useState(!adapter.loadMandate);
  const [walletStatus, setWalletStatus] = useState<WalletSetupStatus | null>(null);
  const [setupLoading, setSetupLoading] = useState(screen === 'setup' && Boolean(adapter.getWalletStatus));
  const [setupError, setSetupError] = useState('');
  const [confirm, setConfirm] = useState<'mandate' | 'wallet' | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [rehearsed, setRehearsed] = useState(() => {
    try { return adapter.walletRehearsed?.() ?? false; } catch { return false; }
  });
  const connected = adapter.source === 'api';

  useEffect(() => {
    if (screen !== 'mandate' || !adapter.loadMandate) return;
    let active = true;
    setLoading(true);
    adapter.loadMandate().then(value => {
      if (!value || !Array.isArray(value.approvedSupplierIds) || !Number.isInteger(value.version)) throw new Error('Invalid mandate contract');
      if (active) { setMandate(value); setLoadedMandate(true); }
    }).catch(() => { if (active) setError(connected ? 'Mandate could not be loaded from the API.' : 'The saved simulated mandate could not be loaded.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [adapter, connected, screen]);

  useEffect(() => {
    if (screen !== 'setup' || !adapter.getWalletStatus) return;
    let active = true;
    setSetupLoading(true); setSetupError('');
    adapter.getWalletStatus().then(value => {
      if (!value || typeof value.configured !== 'boolean' || typeof value.simulated !== 'boolean'
        || (value.configured && (!value.wallet || !value.balance || typeof value.wallet.funded !== 'boolean'
          || typeof value.balance.trustline !== 'boolean'))) throw new Error('Invalid XRPL status response');
      if (active) setWalletStatus(value);
    }).catch(() => { if (active) setSetupError('XRPL Testnet status could not be loaded. Check the backend connection and retry.'); })
      .finally(() => { if (active) setSetupLoading(false); });
    return () => { active = false; };
  }, [adapter, screen]);

  async function apply() {
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      if (confirm === 'mandate') {
        const updated = await adapter.saveMandate({ ...mandate, active: !mandate.active, version: mandate.version + 1 });
        setMandate(updated);
        setNotice(connected ? 'Mandate updated on the API after operator confirmation.' : `Simulated mandate ${updated.active ? 'resumed' : 'paused'}. No live policy was changed.`);
      } else if (connected && adapter.setupTrustline) {
        const result = await adapter.setupTrustline();
        if (!result.simulated && (!result.txHash || !result.trustline)) throw new Error('XRPL did not return a validated trustline receipt.');
        const latest = await adapter.getWalletStatus?.();
        if (latest) setWalletStatus(latest);
        setNotice(result.simulated
          ? 'Simulated trustline setup completed. No XRPL ledger transaction was submitted.'
          : `XRPL Testnet trustline validated. Transaction hash: ${result.txHash}`);
      } else {
        await adapter.rehearseWallet();
        setRehearsed(true);
        setNotice('Simulated rehearsal complete. No wallet, funding, or trustline was created on XRPL Testnet.');
      }
      setConfirm(null);
    } catch {
      setError(connected ? 'The API action failed. No success was recorded. Retry or cancel.' : 'The simulated action failed. Your previous state is unchanged. Retry or cancel.');
    } finally { setBusy(false); }
  }

  if (screen === 'mandate' && loading) return <section className="panel loading-panel" role="status">Loading mandate…</section>;
  if (screen === 'mandate' && !loadedMandate) return <section className="panel error" role="alert"><h2>Unable to load mandate</h2><p>{error}</p><button className="button" onClick={() => window.location.reload()}>Reload workspace</button></section>;

  return <div className="screen-stack">
    <div className="notice">{connected ? 'Connected API · Backend policy is authoritative' : 'Fixture preview · Not connected to live services'}</div>
    {error && !confirm && <p className="error" role="alert">{error}</p>}
    {notice && <p className="notice" role="status">{notice}</p>}
    {screen === 'mandate' ? <>
      <section className="panel panel-heading"><div><p className="eyebrow">SPENDING PROTECTION</p><h2>Your payment mandate</h2><p>Version {mandate.version} · Supplier and budget guardrails</p></div><span className={`badge ${mandate.active ? 'allowed' : 'protected'}`}>{mandate.active ? 'Active' : 'Paused'}{connected ? '' : ' · simulated'}</span></section>
      <div className="stats-grid"><article className="panel"><p>Per-payment limit</p><h2>{amount(mandate.perPaymentLimit)} <small>RLUSD</small></h2></article><article className="panel"><p>Total budget</p><h2>{amount(mandate.totalBudget)} <small>RLUSD</small></h2></article><article className="panel"><p>Remaining budget</p><h2>{amount((Number(mandate.totalBudget) - Number(mandate.spent)).toFixed(2))} <small>RLUSD</small></h2><small>Spent: {amount(mandate.spent)} RLUSD{connected ? '' : ' · simulated'}</small></article></div>
      <section className="panel"><h2>Approved suppliers</h2><p>{connected ? 'These suppliers are allowed by the backend mandate.' : 'Only these suppliers are included in this fixture mandate.'}</p><ul className="supplier-list">{mandate.approvedSupplierIds.map(id => <li key={id}><span>{supplierName(id)}</span><span className="badge allowed">Approved</span></li>)}</ul></section>
      <section className="panel panel-heading"><div><h2>Expiry & controls</h2><p>Expires <time dateTime={mandate.expiresAt}>{new Date(mandate.expiresAt).toLocaleString('en-ZA', { timeZone: 'Africa/Johannesburg' })} SAST</time></p><p>{connected ? 'The backend rechecks this mandate before each payment confirmation.' : 'Pausing prevents simulated payment approval. The backend remains authoritative for live policy.'}</p></div><button className="button secondary" disabled={loading} onClick={() => { setError(''); setConfirm('mandate'); }}>{mandate.active ? 'Pause mandate' : 'Resume mandate'}</button></section>
    </> : connected ? <>
      <section className="panel"><p className="eyebrow">XRPL TESTNET SETUP</p><h2>Wallet and RLUSD trustline</h2><p>The wallet seed stays in the backend environment. This page only shows public account status and requires confirmation before a TrustSet transaction.</p>
        {setupLoading && <p role="status">Checking wallet and trustline…</p>}
        {setupError && <div role="alert" className="error"><p>{setupError}</p><button className="button secondary" onClick={() => window.location.reload()}>Retry connection</button></div>}
        {walletStatus && !walletStatus.configured && <><span className="badge protected">Wallet not configured</span><p>{walletStatus.message ?? 'Configure XRPL_WALLET_SEED in the backend environment.'}</p></>}
        {walletStatus?.configured && walletStatus.wallet && walletStatus.balance && <>
          <span className={`badge ${walletStatus.simulated ? 'pending' : 'allowed'}`}>{walletStatus.simulated ? 'Simulated wallet' : 'Connected to XRPL Testnet'}</span>
          <dl className="details"><div><dt>Public wallet address</dt><dd>{walletStatus.wallet.address}</dd></div><div><dt>Test XRP balance</dt><dd>{walletStatus.wallet.xrpBalance} XRP</dd></div><div><dt>RLUSD trustline</dt><dd>{walletStatus.balance.trustline ? 'Configured' : 'Not configured'}</dd></div><div><dt>RLUSD balance</dt><dd>{walletStatus.balance.balance} RLUSD</dd></div><div><dt>Data source</dt><dd>{walletStatus.simulated ? 'Simulated only' : 'XRPL Testnet validated ledger'}</dd></div></dl>
          {!walletStatus.wallet.funded && <p role="alert">Fund this account with Testnet XRP before creating a trustline. Funding is a separate operator action.</p>}
          {walletStatus.wallet.funded && !walletStatus.balance.trustline && <button className="button" onClick={() => { setError(''); setConfirm('wallet'); }}>Configure RLUSD trustline</button>}
          {walletStatus.balance.trustline && <p className="notice">RLUSD trustline is ready. Balance values are {walletStatus.simulated ? 'simulated' : 'read from Testnet'}.</p>}
        </>}
      </section>
    </> : <>
      <section className="panel"><p className="eyebrow">XRPL TESTNET ONLY</p><h2>Set up your workspace</h2><p>Rehearse the wallet setup journey locally. These steps do not connect, fund, or configure a real account.</p><span className="badge protected">Not connected to XRPL Testnet</span></section>
      <section className="panel"><h2>Wallet setup progress</h2><ol className="setup-steps">{['Connect a testnet wallet', 'Fund with test XRP', 'Configure RLUSD trustline', 'Verify testnet readiness'].map((step, index) => <li key={step}><span className="step-number">{index + 1}</span><div><strong>{step}</strong><p>{rehearsed ? 'Rehearsed locally · simulated only' : 'Not verified on XRPL Testnet'}</p></div></li>)}</ol><button className="button" onClick={() => { setError(''); setConfirm('wallet'); }}>{rehearsed ? 'Rehearse again' : 'Rehearse setup'}</button></section>
    </>}
    {confirm && <ConfirmDialog title={confirm === 'mandate'
      ? `${mandate.active ? 'Pause' : 'Resume'} ${connected ? 'mandate?' : 'simulated mandate?'}`
      : connected ? (walletStatus?.simulated ? 'Confirm simulated trustline setup?' : 'Confirm XRPL Testnet trustline?') : 'Rehearse wallet setup?'}
      onClose={() => { if (!busy) setConfirm(null); }}>
      <p>{confirm === 'mandate'
        ? (connected ? 'Confirm this mandate update. Payments are rechecked against the saved values.' : 'This changes fixture state only. Confirm to continue.')
        : connected ? (walletStatus?.simulated ? 'This uses a simulated adapter and will not submit a ledger transaction.' : 'This submits a TrustSet transaction on XRPL Testnet after your confirmation.')
          : 'This marks the demo steps as rehearsed locally. It does not create any ledger activity.'}</p>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="button-row"><button className="button secondary" disabled={busy} onClick={() => setConfirm(null)}>Cancel</button><button className="button" disabled={busy} onClick={apply}>{busy ? 'Applying…' : error ? 'Retry' : connected && confirm === 'mandate' ? 'Confirm mandate update' : connected && walletStatus?.simulated ? 'Confirm simulated trustline' : connected ? 'Confirm Testnet trustline' : 'Confirm simulation'}</button></div>
    </ConfirmDialog>}
  </div>;
}
