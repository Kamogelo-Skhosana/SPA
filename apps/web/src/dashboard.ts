import demo from './fixtures/demo.json';
import { requests, type PaymentAdapter, type PaymentRequest } from './payments';
export type PayableStatus = 'paid' | 'pending' | 'protected' | 'awaiting_confirmation' | 'failed';
export type Payable = Omit<PaymentRequest, 'status'> & { status: PayableStatus };
export type DashboardData = { payables: Payable[]; balance: typeof demo.balance };
export type DashboardLoader = () => Promise<DashboardData>;
export function fixtureDashboard(api: PaymentAdapter): DashboardLoader {
  return async () => ({ balance: demo.balance, payables: await Promise.all(requests.map(async r => {
    const settlement = await api.payment(r.id);
    return { ...r, status: settlement?.status === 'validated' ? 'paid' : settlement?.status ?? r.status as PayableStatus };
  })) });
}
export const statusLabels: Record<PayableStatus, string> = { paid: 'Paid · simulated', pending: 'Pending · simulated', protected: 'Protected', awaiting_confirmation: 'Awaiting confirmation', failed: 'Failed · simulated' };
export function filterPayables(payables: Payable[], query: string, status: string) {
  const term = query.trim().toLocaleLowerCase();
  return payables.filter(p => (status === 'all' || p.status === status) && `${p.supplierName} ${p.invoiceNumber} ${p.amount} ${p.currency} ${p.destination}`.toLocaleLowerCase().includes(term));
}
export function totalAmount(payables: Payable[]) {
  const cents = payables.reduce((total, p) => {
    if (!/^\d+\.\d{2}$/.test(p.amount)) throw new Error('Invalid decimal amount');
    return total + BigInt(p.amount.replace('.', ''));
  }, 0n);
  return `${cents / 100n}.${(cents % 100n).toString().padStart(2, '0')}`;
}
