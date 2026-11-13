export type PaymentRequest = {
  id: string;
  supplierId: string;
  supplierName: string;
  invoiceNumber: string;
  amount: string;
  currency: string;
  destination: string;
  createdAt: string;
};
export type ApiDecision = {
  requestId: string;
  outcome: 'allowed' | 'protected';
  reasons: string[];
  mandateVersion: number;
};
export type ApiSettlement = {
  requestId: string;
  status: 'pending' | 'validated' | 'failed';
  txHash?: string;
  ledgerIndex?: number;
  simulated?: boolean;
  error?: string;
};
export type ApiPaymentRecord = {
  request: PaymentRequest;
  status: string;
  decision: ApiDecision | null;
  settlement: ApiSettlement | null;
};
export type ApiOverview = {
  mandate: {
    version: number;
    active: boolean;
    perPaymentLimit: string;
    totalBudget: string;
    spent: string;
    approvedSupplierIds: string[];
    expiresAt: string;
  };
  payables: ApiPaymentRecord[];
  budgetUsed: string;
  simulated: boolean;
  network: string;
  balance?: { amount: string; currency: string; source: 'simulated' | 'testnet' } | null;
  balanceError?: string | null;
};
export type XRPLStatus = {
  network: 'testnet';
  configured: boolean;
  simulated: boolean;
  message?: string;
  wallet?: { network: string; address: string; funded: boolean; xrpBalance: string; simulated: boolean };
  balance?: { network: string; address: string; issuer: string; currency: string; trustline: boolean; balance: string; simulated: boolean };
};
export type TrustlineResult = {
  network: string; address: string; issuer: string; currency: string;
  trustline: boolean; txHash?: string; simulated: boolean;
};
export class SpaApiError extends Error {
  status: number;
  constructor(message: string, status: number);
}
export function createSpaApi(options?: {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}): {
  overview(): Promise<ApiOverview>;
  payables(): Promise<ApiPaymentRecord[]>;
  createPayable(request: PaymentRequest): Promise<ApiPaymentRecord>;
  mandate(): Promise<ApiOverview['mandate']>;
  updateMandate(mandate: Omit<ApiOverview['mandate'], 'version'> & { confirmed: boolean }): Promise<ApiOverview['mandate']>;
  runAgent(request: PaymentRequest): Promise<ApiDecision>;
  confirmPayment(decision: ApiDecision, idempotencyKey: string): Promise<ApiPaymentRecord>;
  payment(requestId: string): Promise<ApiPaymentRecord>;
  reconcilePayment(requestId: string): Promise<ApiPaymentRecord>;
  xrplStatus(): Promise<XRPLStatus>;
  setupTrustline(): Promise<TrustlineResult>;
};
