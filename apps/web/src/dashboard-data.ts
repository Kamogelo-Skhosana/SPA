import demo from './fixtures/demo.json';
import { requests, type PaymentAdapter, type PaymentRequest } from './payments';
export type PayableStatus = 'paid' | 'pending' | 'protected' | 'awaiting_confirmation' | 'failed';
export type Payable = PaymentRequest & { status: PayableStatus };
export type DashboardData = { payables: Payable[]; balance: { amount: string; currency: string; source: string } | null; simulated: boolean };
export type DashboardLoader = () => Promise<DashboardData>;
export function fixtureDashboard(api: PaymentAdapter): DashboardLoader {
  return async () => {
    const payables: Payable[] = await Promise.all(requests.map(async request => {
      const settlement = await api.payment(request.id);
      return { ...request, status: settlement?.status === 'validated' ? 'paid' : settlement?.status ?? request.status as PayableStatus };
    }));
    const paid = totalAmount(payables.filter(payable => payable.status === 'paid'));
    const balance = { ...demo.balance, amount: (Number(demo.balance.amount) - Number(paid)).toFixed(2) };
    return { balance, simulated: true, payables };
  };
}
export function statusLabel(status: PayableStatus, simulated: boolean) {
  const label: Record<PayableStatus, string> = { paid: 'Paid', pending: 'Pending', protected: 'Protected', awaiting_confirmation: 'Awaiting confirmation', failed: 'Failed' };
  return simulated && ['paid', 'pending', 'failed'].includes(status) ? `${label[status]} · simulated` : label[status];
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
