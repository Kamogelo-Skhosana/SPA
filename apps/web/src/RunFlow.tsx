import { useEffect, useState } from 'react';
import ConfirmDialog from './ConfirmDialog';
import { amount } from './settings';
import { createFixturePayments, requests as fixtureRequests, type PaymentAdapter, type PaymentRequest, type Decision, type Settlement } from './payments';

function validateSettlement(s: Settlement | null, requestId: string) {
  if (s && (s.requestId !== requestId || !['pending', 'failed', 'validated'].includes(s.status))) throw new Error('Invalid receipt');
  if (s?.status === 'validated') {
    if (s.simulated) {
      if (!s.txHash || !(/^[A-F0-9]{64}$/.test(s.txHash) || s.txHash.startsWith('SIMULATED-'))) throw new Error('Invalid simulated receipt');
    } else if (!/^[A-F0-9]{64}$/.test(s.txHash ?? '') || !Number.isInteger(s.ledgerIndex)) {
      throw new Error('Validated XRPL receipts require a hash and ledger index');
    }
  }
  return s;
}

export default function RunFlow({ adapter, initialId, onUpdate, requests = fixtureRequests, simulated = true }: {
  adapter?: PaymentAdapter;
  initialId?: string;
  onUpdate?: () => void;
  requests?: PaymentRequest[];
  simulated?: boolean;
}) {
  const [api] = useState(() => adapter ?? createFixturePayments(window.localStorage));
  const [id, setId] = useState(initialId ?? requests[0]?.id ?? '');
  useEffect(() => { if (initialId) setId(initialId); }, [initialId]);
  const request = requests.find(r => r.id === id);
  return <section className="panel"><p className="eyebrow">OPERATOR REVIEW · {simulated ? 'SIMULATED' : 'CONNECTED API'}</p><h2>Review payment request</h2><p>{simulated ? 'Review a fixture request, inspect its policy decision, then explicitly confirm an allowed simulation.' : 'The backend rechecks policy when you explicitly confirm a payment.'}</p>
    {initialId ? <p><strong>{request?.invoiceNumber}</strong></p> : <label className="field">Payment request<select value={id} onChange={e => setId(e.target.value)}>{requests.map(r => <option key={r.id} value={r.id}>{r.invoiceNumber} · {r.supplierName}</option>)}</select></label>}
    {request && <RequestFlow key={id} request={request} adapter={api} simulated={simulated} onUpdate={onUpdate} />}
  </section>;
}

export function RequestFlow({ request, adapter, onUpdate, simulated = true }: { request: PaymentRequest; adapter: PaymentAdapter; onUpdate?: () => void; simulated?: boolean }) {
  const [decision, setDecision] = useState<Decision | null>(null);
  const [settlement, setSettlement] = useState<Settlement | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(false);
  useEffect(() => {
    let active = true;
    adapter.payment(request.id).then(s => { if (active) setSettlement(validateSettlement(s, request.id)); })
      .catch(() => { if (active) setError('Payment status could not be loaded. Retry before continuing.'); })
      .finally(() => { if (active) setBusy(false); });
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
          ? await adapter.confirmPayment(decision, `${simulated ? 'fixture' : 'spa'}:${request.id}`)
          : await adapter.payment(request.id, action === 'refresh');
        validateSettlement(s, request.id);
        setSettlement(s); setConfirm(false); onUpdate?.();
      }
    } catch {
      if (action === 'confirm') {
        try {
          const fresh = await adapter.runAgent(request);
          if (fresh.requestId === request.id) setDecision(fresh);
        } catch { /* Keep the previous decision visible with the request error. */ }
      }
      setError(simulated ? 'The simulation could not complete. No ledger payment is claimed.' : 'The API action failed. The backend did not return a confirmed settlement.');
    } finally { setBusy(false); }
  }
  const settlementSimulated = settlement?.simulated ?? simulated;
  const canConfirm = decision?.outcome === 'allowed' && (!settlement || (simulated && settlement.status === 'failed'));
  return <div className="request-flow" aria-busy={busy}>
    <dl className="details"><div><dt>Amount</dt><dd>{amount(request.amount)} {request.currency}</dd></div><div><dt>{simulated ? 'Destination · fixture placeholder' : 'Destination'}</dt><dd>{request.destination}</dd></div></dl>
    {busy && <p role="status">{settlement ? 'Loading payment status…' : 'Loading request…'}</p>}
    {error && !confirm && <div role="alert" className="error"><p>{error}</p><button className="button secondary" disabled={busy} onClick={() => act('load')}>Reload payment status</button></div>}
    {!settlement && !error && <button className="button" disabled={busy} onClick={() => act('run')}>{decision ? 'Run policy check again' : 'Run agent'}</button>}
    {decision && <div className="decision"><h3>{decision.outcome === 'protected' ? 'Protected — submission blocked' : 'Allowed — awaiting operator confirmation'}</h3><p>Mandate version {decision.mandateVersion} · {simulated ? 'simulated decision' : 'API decision'}</p><ul>{decision.reasons.map(r => <li key={r}>{r}</li>)}</ul>{decision.outcome === 'protected' && <p>No signing or settlement action is available.</p>}</div>}
    {canConfirm && !confirm && <button className="button" disabled={busy || !!error} onClick={() => setConfirm(true)}>{settlement?.status === 'failed' ? (simulated ? 'Retry simulated payment' : 'Review retry confirmation') : 'Review confirmation'}</button>}
    {settlement && <div className="receipt"><h3>{settlement.status === 'validated' ? (settlementSimulated ? 'Simulated validated receipt' : 'XRPL Testnet validated receipt') : settlement.status === 'pending' ? (settlementSimulated ? 'Simulation pending' : 'Settlement pending') : (settlementSimulated ? 'Simulation failed' : 'Testnet payment failed')}</h3>
      <p>{settlementSimulated ? 'This result is simulated and is not ledger evidence.' : settlement.status === 'pending' ? 'The XRPL outcome is not yet validated. Retry will reconcile status without resubmitting.' : 'Confirmed by the XRPL Testnet ledger.'}</p>
      {settlement.status === 'validated' && <dl className="details"><div><dt>{settlementSimulated ? 'Simulated transaction hash' : 'XRPL transaction hash'}</dt><dd>{settlement.txHash}</dd></div>{settlement.ledgerIndex !== undefined && <div><dt>{settlementSimulated ? 'Simulated ledger index' : 'Validated ledger index'}</dt><dd>{settlement.ledgerIndex}</dd></div>}</dl>}
      {settlement.status === 'pending' && <button className="button secondary" disabled={busy} onClick={() => act('refresh')}>{simulated ? 'Check simulated status' : 'Recheck payment status'}</button>}
      {settlement.status === 'failed' && simulated && <button className="button secondary" disabled={busy} onClick={() => act('run')}>Recheck policy before retry</button>}
      {settlement.status === 'failed' && !simulated && <p>Do not resubmit this request ID. Review the failure and create a new payable before another attempt.</p>}
    </div>}
    {confirm && canConfirm && <ConfirmDialog title={simulated ? 'Confirm simulated payment?' : 'Confirm XRPL Testnet payment?'} onClose={() => { if (!busy) setConfirm(false); }}><p>{simulated ? `Send ${amount(request.amount)} ${request.currency} to ${request.supplierName} in the fixture only? No real funds or ledger transactions are involved.` : `Send ${amount(request.amount)} ${request.currency} to ${request.supplierName} on XRPL Testnet? The backend will recheck the mandate before signing.`}</p><p>Invoice {request.invoiceNumber}</p>{error && <p role="alert" className="error">{error}</p>}<div className="button-row"><button className="button secondary" disabled={busy} onClick={() => setConfirm(false)}>Cancel</button><button className="button" disabled={busy} onClick={() => act('confirm')}>{busy ? 'Submitting…' : simulated ? 'Confirm simulation' : 'Confirm Testnet payment'}</button></div></ConfirmDialog>}
  </div>;
}
