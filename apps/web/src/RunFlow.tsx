import { useEffect, useState } from 'react';
import ConfirmDialog from './ConfirmDialog';
import { amount } from './settings';
import { createFixturePayments, requests, type PaymentAdapter, type PaymentRequest, type Decision, type Settlement } from './payments';
function validateSettlement(s: Settlement | null, requestId: string) {
  if (s && (s.requestId !== requestId || !['pending', 'failed', 'validated'].includes(s.status) || (s.status === 'validated' && (!/^[A-F0-9]{64}$/.test(s.txHash ?? '') || !Number.isInteger(s.ledgerIndex))))) throw new Error('Invalid receipt');
  return s;
}
export default function RunFlow({ adapter, initialId }: { adapter?: PaymentAdapter; initialId?: string }) {
  const [api] = useState(() => adapter ?? createFixturePayments(window.localStorage));
  const [id, setId] = useState(initialId ?? requests[0].id);
  useEffect(() => { if (initialId) setId(initialId); }, [initialId]);
  return <section className="panel"><p className="eyebrow">OPERATOR REVIEW · SIMULATED</p><h2>Run payment agent</h2><p>Review a fixture request, inspect its policy decision, then explicitly confirm an allowed simulation.</p>
    <label className="field">Payment request<select value={id} onChange={e => setId(e.target.value)}>{requests.map(r => <option key={r.id} value={r.id}>{r.invoiceNumber} · {r.supplierName}</option>)}</select></label>
    <RequestFlow key={id} request={requests.find(r => r.id === id)!} adapter={api} />
  </section>;
}
export function RequestFlow({ request, adapter }: { request: PaymentRequest; adapter: PaymentAdapter }) {
  const [decision, setDecision] = useState<Decision | null>(null);
  const [settlement, setSettlement] = useState<Settlement | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(false);
  useEffect(() => {
    let active = true;
    adapter.payment(request.id).then(s => { if (active) setSettlement(validateSettlement(s, request.id)); }).catch(() => {if (active) setError('Saved simulation could not be loaded. Retry loading before continuing.');}).finally(() => {if (active) setBusy(false);});
    return () => { active = false; };
  }, [adapter, request.id]);
  async function act(action: 'run' | 'confirm' | 'refresh' | 'load') {
    if (busy) return;
    setBusy(true); setError('');
    try {
      if (action === 'run') {
        const d = await adapter.runAgent(request);
        if (d.requestId !== request.id || !['allowed', 'protected'].includes(d.outcome) || !Array.isArray(d.reasons) || !d.reasons.every(r => typeof r === 'string')) throw new Error('Invalid decision');
        setDecision(d);
      } else {
        const s = action === 'confirm' && decision?.outcome === 'allowed'
          ? await adapter.confirmPayment(decision, `fixture:${request.id}`)
          : await adapter.payment(request.id, action === 'refresh');
        validateSettlement(s, request.id);
        setSettlement(s); setConfirm(false);
      }
    } catch { setError('The simulation could not complete. Retry the action; no confirmed ledger payment is claimed.'); }
    finally { setBusy(false); }
  }
  const canConfirm = decision?.outcome === 'allowed' && (!settlement || settlement.status === 'failed');
  return <div className="request-flow" aria-busy={busy}>
    <dl className="details"><div><dt>Amount</dt><dd>{amount(request.amount)} {request.currency}</dd></div><div><dt>Destination · fixture placeholder</dt><dd>{request.destination}</dd></div></dl>
    {busy && <p role="status">Loading simulation…</p>}
    {error && !confirm && <div role="alert" className="error"><p>{error}</p>{!confirm && <button className="button secondary" disabled={busy} onClick={() => act('load')}>Reload saved simulation</button>}</div>}
    {!settlement && !error && <button className="button" disabled={busy} onClick={() => act('run')}>{decision ? 'Run agent again' : 'Run agent'}</button>}
    {decision && <div className="decision"><h3>{decision.outcome === 'protected' ? 'Protected — submission blocked' : 'Allowed — awaiting operator confirmation'}</h3><p>Fixture mandate version {decision.mandateVersion} · simulated decision</p><ul>{decision.reasons.map(r => <li key={r}>{r}</li>)}</ul>{decision.outcome === 'protected' && <p>No signing or settlement action is available.</p>}</div>}
    {canConfirm && !confirm && <button className="button" disabled={busy || !!error} onClick={() => setConfirm(true)}>{settlement?.status === 'failed' ? 'Retry simulated payment' : 'Review confirmation'}</button>}
    {settlement && <div className="receipt"><h3>{settlement.status === 'validated' ? 'Simulated validated receipt' : settlement.status === 'pending' ? 'Simulation pending' : 'Simulation failed'}</h3>
      <p>This fixture is not evidence of a validated XRPL Testnet transaction.</p>
      {settlement.status === 'validated' && <dl className="details"><div><dt>Simulated transaction hash</dt><dd>{settlement.txHash}</dd></div><div><dt>Simulated ledger index</dt><dd>{settlement.ledgerIndex}</dd></div></dl>}
      {settlement.status === 'pending' && <button className="button secondary" disabled={busy} onClick={() => act('refresh')}>Check simulated status</button>}
      {settlement.status === 'failed' && <button className="button secondary" disabled={busy} onClick={() => act('run')}>Recheck policy before retry</button>}
    </div>}
    {confirm && canConfirm && <ConfirmDialog title="Confirm simulated payment?" onClose={() => {if (!busy) setConfirm(false);}}><p>Send {amount(request.amount)} {request.currency} to {request.supplierName} in the fixture only? No real funds or ledger transactions are involved.</p><p>Invoice {request.invoiceNumber}</p>{error && <p role="alert" className="error">{error}</p>}<div className="button-row"><button className="button secondary" disabled={busy} onClick={() => setConfirm(false)}>Cancel</button><button className="button" disabled={busy} onClick={() => act('confirm')}>{busy ? 'Submitting…' : 'Confirm simulation'}</button></div></ConfirmDialog>}
  </div>;
}
