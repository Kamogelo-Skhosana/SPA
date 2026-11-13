import demo from './fixtures/demo.json';
export const initialMandate = demo.mandate;
export type Mandate = typeof initialMandate;
export type WalletSetupStatus = {
  network: string;
  configured: boolean;
  simulated: boolean;
  message?: string;
  wallet?: { network: string; address: string; funded: boolean; xrpBalance: string; simulated: boolean };
  balance?: { network: string; address: string; issuer: string; currency: string; trustline: boolean; balance: string; simulated: boolean };
};
export type TrustlineSetupResult = {
  network: string; address: string; issuer: string; currency: string;
  trustline: boolean; txHash?: string; simulated: boolean;
};
export interface SettingsAdapter {
  source?: 'fixture' | 'api';
  getWalletStatus?: () => Promise<WalletSetupStatus>;
  setupTrustline?: () => Promise<TrustlineSetupResult>;
  loadMandate?: () => Promise<Mandate>;
  saveMandate: (mandate: Mandate) => Promise<Mandate>;
  rehearseWallet: () => Promise<void>;
}
export const fixtureSettings: SettingsAdapter = {
  source: 'fixture',
  async saveMandate(mandate) { return structuredClone(mandate); },
  async rehearseWallet() { /* Local rehearsal only; no wallet is created. */ },
};
export function amount(value: string) {
  return new Intl.NumberFormat('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value));
}
export function supplierName(id: string) {
  return demo.payables.find(p => p.supplierId === id)?.supplierName ?? id.split('-').map(word => word[0].toUpperCase() + word.slice(1)).join(' ');
}
