import assert from 'node:assert/strict';
import test from 'node:test';
import { createSpaApi, SpaApiError } from '../src/api-client.mjs';

test('reads overview and sends structured agent request', async () => {
  const calls = [];
  const api = createSpaApi({ fetchImpl: async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ value: 'fixture' }) };
  } });
  assert.deepEqual(await api.overview(), { value: 'fixture' });
  await api.runAgent({ id: 'req-1' });
  assert.equal(calls[0].url, '/overview');
  assert.equal(calls[1].url, '/agent/runs');
  assert.equal(calls[1].options.body, '{"id":"req-1"}');
});

test('protected payment never reaches confirmation endpoint', () => {
  let calls = 0;
  const api = createSpaApi({ fetchImpl: async () => { calls++; } });
  assert.throws(() => api.confirmPayment({
    requestId: 'req-protected', outcome: 'protected',
  }, 'retry-1'), SpaApiError);
  assert.equal(calls, 0);
});

test('allowed payment uses stable retry key and encoded request ID', async () => {
  let call;
  const api = createSpaApi({ fetchImpl: async (url, options) => {
    call = { url, options };
    return { ok: true, json: async () => ({ status: 'pending' }) };
  } });
  await api.confirmPayment({ requestId: 'invoice/42', outcome: 'allowed' }, 'retry-42');
  assert.equal(call.url, '/payments/invoice%2F42/confirm');
  assert.equal(call.options.headers['Idempotency-Key'], 'retry-42');
});

test('surfaces API errors to the UI', async () => {
  const api = createSpaApi({ fetchImpl: async () => ({
    ok: false, status: 409, json: async () => ({ detail: 'Mandate changed' }),
  }) });
  await assert.rejects(api.mandate(), (error) =>
    error instanceof SpaApiError && error.status === 409 && error.message === 'Mandate changed');
});
