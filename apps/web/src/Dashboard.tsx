import { useCallback, useEffect, useState } from 'react';
import demo from './fixtures/demo.json';
import RunFlow from './RunFlow';
import { createFixturePayments, type PaymentAdapter } from './payments';
import { amount } from './settings';
import { filterPayables, fixtureDashboard, statusLabels, totalAmount, type DashboardData, type DashboardLoader, type PayableStatus } from './dashboard';
export default function Dashboard({ screen, load, paymentAdapter }: { screen: 'overview' | 'payables'; load?: DashboardLoader; paymentAdapter?: PaymentAdapter }) {
  const [api] = useState(() => paymentAdapter ?? createFixturePayments(window.localStorage));
  const [loader] = useState(() => load ?? fixtureDashboard(api));
  const [data, setData] = useState<DashboardData | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const [selected, setSelected] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setBusy(true); setError('');
    try {
      const result = await loader();
      if (result.balance.source !== 'simulated' || !Array.isArray(result.payables) || result.payables.some(p => !statusLabels[p.status] || !/^\d+\.\d{2}$/.test(p.amount))) throw new Error('Invalid fixture response');
      setData(result);
    } catch { setError('Payables could not be loaded. Retry to recover the fixture view.'); }
    finally { setBusy(false); }
  }, [loader]);
  useEffect(() => {void refresh();}, [refresh]);
  const matches = filterPayables(data?.payables ?? [], query, status);
  const request = data?.payables.find(p => p.id === selected);
  return <div className="screen-stack">
    <div className="notice">{demo.business.name} · Fixture preview · Not connected to live services</div>
    {busy && <div className="panel loading-panel" role="status">Loading {screen === 'overview' ? 'overview' : 'payables'}…</div>}
    {error && <section className="panel error" role="alert"><h2>Unable to load payables</h2><p>{error}</p><button className="button" onClick={refresh}>Retry loading</button></section>}
    {data && !error && <>
      {screen === 'overview' && <>
        <section className="balance-card"><div><p className="eyebrow">WORKSPACE BALANCE · SIMULATED</p><h2>{amount(data.balance.amount)} <span>{data.balance.currency}</span></h2><p>Fixture balance · no live wallet connected</p></div><a className="button light" href="#/setup">View setup</a></section>
        <div className="stats-grid"><article className="panel"><p>Awaiting review</p><h2>{data.payables.filter(p => p.status === 'awaiting_confirmation').length} <small>requests</small></h2></article><article className="panel"><p>Protected requests</p><h2>{data.payables.filter(p => p.status === 'protected').length} <small>blocked</small></h2></article><article className="panel"><p>Paid in this simulation</p><h2>{amount(totalAmount(data.payables.filter(p => p.status === 'paid')))} <small>RLUSD</small></h2></article></div>
      </>}
      <section className="panel payable-panel" aria-busy={busy}>
        <div className="panel-heading"><div><p className="eyebrow">PAYMENT ACTIVITY</p><h2>{screen === 'overview' ? 'Recent requests' : 'All payables'}</h2></div><button className="button secondary" disabled={busy} onClick={refresh}>Refresh requests</button></div>
        <div className="filters"><label className="field">Search payables<input type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Supplier, invoice or amount" /></label><label className="field">Status<select value={status} onChange={e => setStatus(e.target.value)}><option value="all">All statuses</option>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label></div>
        {!data.payables.length ? <div className="empty-state"><h3>No payment requests yet</h3><p>Fixture requests will appear here when available.</p></div> : !matches.length ? <div className="empty-state"><h3>No matching requests</h3><p>Try another supplier, invoice, amount or status.</p><button className="button secondary" onClick={() => {setQuery(''); setStatus('all');}}>Clear filters</button></div> : <div className="table-scroll"><table><caption className="sr-only">Simulated payment requests</caption><thead><tr><th scope="col">Supplier / invoice</th><th scope="col">Amount</th><th scope="col">Status</th><th scope="col">Details</th></tr></thead><tbody>{matches.map(p => <tr key={p.id}><td><strong>{p.supplierName}</strong><small>{p.invoiceNumber}</small></td><td className="amount-cell">{amount(p.amount)}<small>{p.currency} · simulated</small></td><td><span className={`badge ${p.status === 'awaiting_confirmation' ? 'pending' : p.status}`}>{statusLabels[p.status]}</span></td><td><button className="detail-button" aria-label={`View ${p.invoiceNumber}`} aria-expanded={selected === p.id} onClick={() => {setSelected(p.id); document.getElementById('request-detail')?.scrollIntoView?.({behavior:'smooth',block:'nearest'});}}>View <span aria-hidden="true">↗</span></button></td></tr>)}</tbody></table></div>}
        <p className="table-note">{matches.length} of {data.payables.length} requests · All amounts and status results are simulated.</p>
      </section>
      {request && <section id="request-detail" className="panel" aria-label="Request details"><div className="panel-heading"><div><p className="eyebrow">REQUEST DETAILS</p><h2>{request.supplierName}</h2></div><button className="button secondary" onClick={() => setSelected(null)}>Close details</button></div><dl className="details"><div><dt>Invoice</dt><dd>{request.invoiceNumber}</dd></div><div><dt>Created</dt><dd><time dateTime={request.createdAt}>{new Date(request.createdAt).toLocaleString('en-ZA',{timeZone:'Africa/Johannesburg'})} SAST</time></dd></div><div><dt>Status</dt><dd>{statusLabels[request.status as PayableStatus]}</dd></div></dl><RunFlow key={request.id} initialId={request.id} adapter={api} onUpdate={refresh}/></section>}
      {!selected && <RunFlow adapter={api} onUpdate={refresh}/>}
    </>}
  </div>;
}
