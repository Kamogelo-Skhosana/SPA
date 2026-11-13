export class SpaApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'SpaApiError';
    this.status = status;
  }
}

export function createSpaApi({ baseUrl = '', fetchImpl = fetch } = {}) {
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetchImpl(`${baseUrl}${path}`, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...options.headers },
      });
    } catch (cause) {
      throw new SpaApiError(`SPA API unavailable: ${cause.message}`, 0);
    }

    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new SpaApiError('SPA API returned invalid JSON', response.status);
    }
    if (!response.ok) {
      throw new SpaApiError(payload?.detail ?? 'SPA API request failed', response.status);
    }
    return payload;
  }

  return {
    overview: () => request('/overview'),
    payables: () => request('/payables'),
    createPayable: (paymentRequest) => request('/payables', {
      method: 'POST', body: JSON.stringify(paymentRequest),
    }),
    mandate: () => request('/mandate'),
    updateMandate: (mandate) => request('/mandate', {
      method: 'PUT', body: JSON.stringify(mandate),
    }),
    runAgent: (paymentRequest) => request('/agent/runs', {
      method: 'POST', body: JSON.stringify(paymentRequest),
    }),
    confirmPayment: (decision, idempotencyKey) => {
      if (decision.outcome !== 'allowed') {
        throw new SpaApiError('Protected requests cannot be confirmed', 400);
      }
      if (!idempotencyKey) {
        throw new SpaApiError('An idempotency key is required', 400);
      }
      return request(`/payments/${encodeURIComponent(decision.requestId)}/confirm`, {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
      });
    },
    payment: (requestId) => request(`/payments/${encodeURIComponent(requestId)}`),
    reconcilePayment: (requestId) => request(`/payments/${encodeURIComponent(requestId)}/reconcile`, {
      method: 'POST',
    }),
    xrplStatus: () => request('/xrpl/status'),
    setupTrustline: () => request('/xrpl/trustline', {
      method: 'POST', body: JSON.stringify({ confirmed: true }),
    }),
  };
}
