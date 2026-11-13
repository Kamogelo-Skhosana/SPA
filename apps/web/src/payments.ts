import demo from './fixtures/demo.json';
export type PaymentRequest = {
  id: string; supplierId: string; supplierName: string; invoiceNumber: string;
  amount: string; currency: string; destination: string; createdAt: string;
  status?: 'paid' | 'pending' | 'protected' | 'awaiting_confirmation' | 'failed'; fixtureOutcome?: 'allowed' | 'protected'; fixtureReasons?: string[];
};
export type Decision = { requestId: string; outcome: 'allowed' | 'protected'; reasons: string[]; mandateVersion: number };
export type Settlement = { requestId: string; status: 'pending' | 'validated' | 'failed'; txHash?: string; ledgerIndex?: number; simulated?: boolean };
export interface PaymentAdapter {
  runAgent(request: PaymentRequest): Promise<Decision>;
  confirmPayment(decision: Decision, idempotencyKey: string): Promise<Settlement>;
  payment(requestId: string, refresh?: boolean): Promise<Settlement | null>;
}
export const requests = demo.payables as PaymentRequest[];
export function fixtureDecision(request: PaymentRequest, now = new Date()): Decision {
  const mandate = demo.mandate;
  const reasons: string[] = [];
  if (!mandate.active) reasons.push('Mandate is paused.');
  if (now >= new Date(mandate.expiresAt)) reasons.push('Mandate has expired.');
  if (!mandate.approvedSupplierIds.includes(request.supplierId)) reasons.push('Supplier is not on the approved list.');
  if (Number(request.amount) > Number(mandate.perPaymentLimit)) reasons.push('Amount exceeds the per-payment cap.');
  if (Number(request.amount) + Number(mandate.spent) > Number(mandate.totalBudget)) reasons.push('Amount exceeds the remaining budget.');
  return { requestId: request.id, outcome: reasons.length ? 'protected' : 'allowed', reasons: reasons.length ? reasons : ['Supplier, amount, budget and expiry are within the fixture mandate.'], mandateVersion: mandate.version };
}
export function createFixturePayments(storage: Pick<Storage, 'getItem' | 'setItem'>, now = () => new Date()): PaymentAdapter {
  const key = 'spa.simulated.settlements.v1';
  function read(): Record<string, Settlement> {
    const raw = storage.getItem(key);
    if (!raw) return {};
    const values: unknown = JSON.parse(raw);
    if (!values || typeof values !== 'object' || Array.isArray(values)) throw new Error('Invalid saved fixture state');
    for (const [id, value] of Object.entries(values)) {
      const s = value as Settlement;
      if (!requests.some(r => r.id === id) || s?.requestId !== id || !['pending', 'validated', 'failed'].includes(s.status)
        || (s.status === 'validated' && (!/^[A-F0-9]{64}$/.test(s.txHash ?? '') || !Number.isInteger(s.ledgerIndex)))) throw new Error('Invalid saved fixture settlement');
    }
    return values as Record<string, Settlement>;
  }
  return {
    async runAgent(request) {
      const known = requests.find(r => r.id === request.id);
      if (!known || JSON.stringify(known) !== JSON.stringify(request)) throw new Error('Unknown fixture request');
      return fixtureDecision(known, now());
    },
    async confirmPayment(decision, idempotencyKey) {
      const request = requests.find(r => r.id === decision.requestId);
      if (!request || decision.outcome !== 'allowed' || fixtureDecision(request, now()).outcome !== 'allowed') throw new Error('Protected requests cannot be submitted');
      if (idempotencyKey !== `fixture:${request.id}`) throw new Error('A stable fixture retry key is required');
      const saved = read();
      if (saved[request.id] && saved[request.id].status !== 'failed') return saved[request.id];
      const pending: Settlement = { requestId: request.id, status: 'pending', simulated: true };
      saved[request.id] = pending; storage.setItem(key, JSON.stringify(saved));
      return pending;
    },
    async payment(requestId, refresh = false) {
      const saved = read();
      const current = saved[requestId] ?? null;
      if (refresh && current?.status === 'pending') {
        const receipt: Settlement = { requestId, status: 'validated', txHash: 'A'.repeat(64), ledgerIndex: 100001, simulated: true };
        saved[requestId] = receipt; storage.setItem(key, JSON.stringify(saved)); return receipt;
      }
      return current;
    },
  };
}
