import demo from './fixtures/demo.json';
import { fixtureMandateKey, readFixtureMandate } from './payments';
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
  walletRehearsed?: () => boolean;
  rehearseWallet: () => Promise<void>;
}
export const fixtureSettings: SettingsAdapter = {
  source: 'fixture',
  async loadMandate() { return readFixtureMandate(window.localStorage); },
  async saveMandate(mandate) {
    const storage = window.localStorage;
    const current = readFixtureMandate(storage);
    if (mandate.version !== current.version + 1) throw new Error('Fixture mandate changed');
    storage.setItem(fixtureMandateKey, JSON.stringify({ active: mandate.active, version: mandate.version }));
    return { ...current, active: mandate.active, version: mandate.version };
  },
  walletRehearsed() { return window.localStorage.getItem('spa.simulated.wallet-rehearsal.v1') === 'true'; },
  async rehearseWallet() { window.localStorage.setItem('spa.simulated.wallet-rehearsal.v1', 'true'); },
};
export function amount(value: string) {
  return new Intl.NumberFormat('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value));
}
export function supplierName(id: string) {
  return demo.payables.find(p => p.supplierId === id)?.supplierName ?? id.split('-').map(word => word[0].toUpperCase() + word.slice(1)).join(' ');
}
