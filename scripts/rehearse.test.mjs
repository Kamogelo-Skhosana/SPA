import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const fixture = JSON.parse(readFileSync(new URL('../docs/fixtures/demo.json', import.meta.url)));
const { mandate, payables } = fixture;

function evaluate(request) {
  const reasons = [];
  if (!mandate.active) reasons.push('Mandate paused');
  if (!mandate.approvedSupplierIds.includes(request.supplierId)) {
    reasons.push('Supplier is not on the approved list.');
  }
  if (Number(request.amount) > Number(mandate.perPaymentLimit)) {
    reasons.push('Amount exceeds the per-payment cap.');
  }
  if (Number(request.amount) + Number(mandate.spent) > Number(mandate.totalBudget)) {
    reasons.push('Amount exceeds the remaining budget.');
  }
  if (Date.parse(request.createdAt) > Date.parse(mandate.expiresAt)) {
    reasons.push('Mandate expired.');
  }
  return { outcome: reasons.length ? 'protected' : 'allowed', reasons };
}

test('demo fixture identifies testnet and simulated balances', () => {
  assert.equal(fixture.business.environment, 'XRPL Testnet');
  assert.equal(fixture.business.dataMode, 'simulated');
  assert.equal(fixture.balance.source, 'simulated');
});

for (const request of payables) {
  test(`rehearsal decision for ${request.id}`, () => {
    const decision = evaluate(request);
    assert.equal(decision.outcome, request.fixtureOutcome);
    if (decision.outcome === 'protected') {
      assert.equal(request.status, 'protected');
      assert.ok(decision.reasons.length);
    } else {
      assert.equal(request.status, 'awaiting_confirmation');
    }
    assert.ok(request.destination.startsWith('rTEST_'), 'Fixture destination must be a placeholder');
    assert.equal(request.txHash, undefined, 'A fixture must not claim a real transaction');
  });
}
