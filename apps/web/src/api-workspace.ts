import { createSpaApi, type ApiPaymentRecord, type ApiSettlement, type PaymentRequest as ApiRequest } from '../../../packages/contracts/src/api-client.mjs';
import type { PaymentAdapter, Decision, Settlement } from './payments';
import type { DashboardData, DashboardLoader, Payable } from './dashboard';
import type { Mandate, SettingsAdapter } from './settings';

function toSettlement(record: ApiPaymentRecord, requestId: string): Settlement | null {
  if (record.request.id !== requestId) throw new Error('API payment id does not match the requested payment.');
  const value: ApiSettlement | null = record.settlement;
  if (!value) return null;
  if (value.requestId !== requestId || !['pending', 'validated', 'failed'].includes(value.status)) {
    throw new Error('API returned a settlement that does not match the shared contract.');
  }
  if (value.status === 'validated') {
    if (value.simulated) {
      if (!value.txHash?.startsWith('SIMULATED-')) throw new Error('Simulated receipts must use a simulated hash.');
    } else if (!/^[A-F0-9]{64}$/.test(value.txHash ?? '') || !Number.isInteger(value.ledgerIndex)) {
      throw new Error('Validated XRPL receipts require a transaction hash and ledger index.');
    }
  }
  return value;
}

function toPayable(record: ApiPaymentRecord): Payable {
  const request = record.request;
  if (!request || !request.id || !/^\d+(\.\d+)?$/.test(request.amount)
    || !request.supplierId || !request.supplierName || !request.invoiceNumber
    || !request.currency || !request.destination || !request.createdAt) {
    throw new Error('API payable does not match the shared PaymentRequest contract.');
  }
  if (!['paid', 'pending', 'protected', 'failed'].includes(record.status)) {
    throw new Error('API payment status does not match the shared contract.');
  }
  const status = record.status === 'paid' ? 'paid'
    : record.status === 'protected' ? 'protected'
    : record.status === 'failed' ? 'failed'
    : record.status === 'pending' && record.settlement ? 'pending'
    : 'awaiting_confirmation';
  return { ...request, status };
}

export function createApiWorkspace(baseUrl: string, fetchImpl: typeof fetch = fetch) {
  let endpoint = baseUrl.trim();
  while (endpoint.endsWith('/')) endpoint = endpoint.slice(0, -1);
  const client = createSpaApi({ baseUrl: endpoint, fetchImpl });
  const payments: PaymentAdapter = {
    async runAgent(request: ApiRequest): Promise<Decision> {
      const decision = await client.runAgent(request);
      if (decision.requestId !== request.id || !['allowed', 'protected'].includes(decision.outcome)
        || !Array.isArray(decision.reasons) || !Number.isInteger(decision.mandateVersion)) {
        throw new Error('API decision does not match the shared contract.');
      }
      return decision;
    },
    async confirmPayment(decision, idempotencyKey) {
      const record = await client.confirmPayment(decision, idempotencyKey);
      if (record.status === 'protected') {
        throw new Error('The backend policy recheck protected this payment. Run the policy check again.');
      }
      const settlement = toSettlement(record, decision.requestId);
      if (!settlement) throw new Error('API confirmation did not return a settlement result.');
      return settlement;
    },
    async payment(requestId, refresh = false) {
      const record = refresh ? await client.reconcilePayment(requestId) : await client.payment(requestId);
      return toSettlement(record, requestId);
    },
  };

  const loadDashboard: DashboardLoader = async (): Promise<DashboardData> => {
    const overview = await client.overview();
    if (overview.network !== 'XRPL Testnet' || typeof overview.simulated !== 'boolean'
      || !Array.isArray(overview.payables) || !overview.mandate) {
      throw new Error('API overview does not match the shared contract.');
    }
    const balance = overview.balance ?? null;
    if (balance && (!/^\d+(\.\d+)?$/.test(balance.amount) || balance.currency !== 'RLUSD'
      || !['simulated', 'testnet'].includes(balance.source))) {
      throw new Error('API balance does not match the shared contract.');
    }
    return {
      payables: overview.payables.map(toPayable),
      balance,
      simulated: overview.simulated,
    };
  };

  const settings: SettingsAdapter & { source: 'api' } = {
    source: 'api',
    async getWalletStatus() {
      return await client.xrplStatus();
    },
    async setupTrustline() {
      return await client.setupTrustline();
    },
    async loadMandate() {
      return await client.mandate() as Mandate;
    },
    async saveMandate(mandate) {
      const { version: _version, ...values } = mandate;
      const updated = await client.updateMandate({ ...values, confirmed: true });
      return updated as Mandate;
    },
    async rehearseWallet() {
      throw new Error('Wallet setup is not available through this API connection.');
    },
  };

  return { payments, loadDashboard, settings };
}
