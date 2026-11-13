import { expect, test, vi } from 'vitest';
import { createApiWorkspace } from '../src/api-workspace';

const request = {
  id: 'api-request-1', supplierId: 'northstar-imports', supplierName: 'Northstar Imports',
  invoiceNumber: 'INV-1', amount: '25.00', currency: 'RLUSD',
  destination: 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh', createdAt: '2026-11-13T12:00:00Z',
};
const mandate = {
  version: 2, active: true, perPaymentLimit: '5000.00', totalBudget: '20000.00',
  spent: '0.00', approvedSupplierIds: ['northstar-imports'], expiresAt: '2027-01-01T00:00:00Z',
};
function response(payload: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload } as Response;
}
test('API workspace maps overview and payable records, marking missing balance unavailable', async () => {
  const fetchImpl = vi.fn(async () => response({
    network: 'XRPL Testnet', simulated: true, mandate, budgetUsed: mandate.spent,
    payables: [{ request, status: 'pending', decision: null, settlement: null }],
  }));
  const workspace = createApiWorkspace('http://api.test', fetchImpl as typeof fetch);
  const data = await workspace.loadDashboard();
  expect(data.simulated).toBe(true);
  expect(data.balance).toBeNull();
  expect(data.payables).toEqual([{ ...request, status: 'awaiting_confirmation' }]);
  expect(fetchImpl).toHaveBeenCalledWith('http://api.test/overview', expect.any(Object));
});

test('API payment flow checks policy, confirms with a stable key, and reads validated receipt', async () => {
  const decision = { requestId: request.id, outcome: 'allowed', reasons: [], mandateVersion: 2 };
  const receipt = { requestId: request.id, status: 'validated', simulated: true, txHash: 'SIMULATED-abc' };
  const fetchImpl = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    const path = String(url);
    if (path.endsWith('/agent/runs')) return response(decision);
    if (path.endsWith('/confirm')) return response({ request, status: 'paid', decision, settlement: receipt });
    if (path.endsWith('/payments/api-request-1')) return response({ request, status: 'paid', decision, settlement: receipt });
    throw new Error(`Unexpected API request: ${path}`);
  });
  const workspace = createApiWorkspace('http://api.test', fetchImpl as typeof fetch);
  const checked = await workspace.payments.runAgent(request);
  expect(checked).toEqual(decision);
  expect(await workspace.payments.confirmPayment(checked, `spa:${request.id}`)).toEqual(receipt);
  expect(await workspace.payments.payment(request.id)).toEqual(receipt);
  expect(fetchImpl.mock.calls[1][1]?.headers).toMatchObject({ 'Idempotency-Key': `spa:${request.id}` });
});

test('API adapter rejects a validated non-simulated receipt without ledger evidence', async () => {
  const fetchImpl = vi.fn(async () => response({
    request, status: 'paid', decision: null,
    settlement: { requestId: request.id, status: 'validated', simulated: false, txHash: 'short' },
  }));
  const workspace = createApiWorkspace('http://api.test', fetchImpl);
  await expect(workspace.payments.payment(request.id)).rejects.toThrow('hash and ledger index');
});


test('API mandate reads and confirmed updates use only writable fields', async () => {
  let updateBody: Record<string, unknown> | null = null;
  const fetchImpl = vi.fn(async (url: string | URL | Request, init?: RequestInit) => {
    if (String(url).endsWith('/mandate') && !init?.method) return response(mandate);
    if (String(url).endsWith('/mandate') && init?.method === 'PUT') {
      updateBody = JSON.parse(String(init.body));
      return response({ ...mandate, active: false, version: 3 });
    }
    throw new Error('Unexpected API request');
  });
  const workspace = createApiWorkspace('http://api.test', fetchImpl as typeof fetch);
  expect(await workspace.settings.loadMandate?.()).toEqual(mandate);
  const updated = await workspace.settings.saveMandate({ ...mandate, active: false, version: 3 });
  expect(updated.active).toBe(false);
  expect(updateBody).toEqual({
    active: false,
    perPaymentLimit: mandate.perPaymentLimit,
    totalBudget: mandate.totalBudget,
    spent: mandate.spent,
    approvedSupplierIds: mandate.approvedSupplierIds,
    expiresAt: mandate.expiresAt,
    confirmed: true,
  });
});
