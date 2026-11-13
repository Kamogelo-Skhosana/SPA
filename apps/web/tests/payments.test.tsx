import React from 'react';
import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RequestFlow } from '../src/RunFlow';
import { createFixturePayments, requests, fixtureDecision } from '../src/payments';
import { fixtureSettings } from '../src/settings';
afterEach(() => {cleanup(); localStorage.clear();});
const now = () => new Date('2026-11-13T12:00:00Z');
function adapter() {return createFixturePayments(localStorage, now);}
async function run() { await waitFor(() => expect(screen.getByRole('button', {name:'Run agent'}).disabled).toBe(false)); fireEvent.click(screen.getByRole('button', {name:'Run agent'})); }
test('protected supplier and over-limit decisions never invoke confirmation', async () => {
  for (const request of requests.slice(1)) {
    const api = adapter(); const confirm = vi.spyOn(api, 'confirmPayment');
    render(<RequestFlow request={request} adapter={api} />); await run();
    await screen.findByText('Protected — submission blocked');
    expect(screen.queryByRole('button', {name:'Review confirmation'})).toBeNull();
    expect(confirm).not.toHaveBeenCalled(); cleanup();
  }
});
test('approval needs explicit confirmation; pending and receipt survive remount', async () => {
  const api=adapter();const confirm=vi.spyOn(api,'confirmPayment');
  const view=render(<RequestFlow request={requests[0]} adapter={api}/>);await run();
  fireEvent.click(await screen.findByRole('button',{name:'Review confirmation'}));
  expect(confirm).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
  expect(confirm).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Review confirmation'}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm simulation'}));await screen.findByText('Simulation pending');
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(screen.queryByText('Allowed — awaiting operator confirmation')).toBeNull();
  view.unmount();
  render(<RequestFlow request={requests[0]} adapter={api}/>);await screen.findByText('Simulation pending');
  expect(screen.queryByRole('button',{name:'Review confirmation'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Check simulated status'}));await screen.findByText('Simulated validated receipt');
  expect(screen.getByText('A'.repeat(64))).toBeTruthy();cleanup();
  render(<RequestFlow request={requests[0]} adapter={api}/>);await screen.findByText('Simulated validated receipt');
  expect(confirm).toHaveBeenCalledTimes(1);
});
test('adapter rechecks policy, blocks forged approval and prevents duplicates', async () => {
  const api=adapter();
  await expect(api.confirmPayment({...fixtureDecision(requests[1],now()),outcome:'allowed'},`fixture:${requests[1].id}`)).rejects.toThrow('Protected');
  const d=fixtureDecision(requests[0],now());
  expect(await api.confirmPayment(d,`fixture:${d.requestId}`)).toEqual(await api.confirmPayment(d,`fixture:${d.requestId}`));
  const expired=createFixturePayments(localStorage,()=>new Date('2026-12-01'));
  await expect(expired.confirmPayment(d,`fixture:${d.requestId}`)).rejects.toThrow('Protected');
});
test('failed submission recovers without losing operator confirmation', async () => {
  const api=adapter(); const original=api.confirmPayment;api.confirmPayment=vi.fn().mockRejectedValueOnce(new Error('offline')).mockImplementation(original);
  render(<RequestFlow request={requests[0]} adapter={api}/>);await run();
  fireEvent.click(await screen.findByRole('button',{name:'Review confirmation'}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm simulation'}));
  await waitFor(()=>expect(screen.getAllByRole('alert').length).toBeGreaterThan(0));
  fireEvent.click(screen.getByRole('button',{name:'Confirm simulation'}));await screen.findByText('Simulation pending');
});
test('failed settlement requires a fresh allowed decision before retry', async()=>{
  const api=adapter();localStorage.setItem('spa.simulated.settlements.v1',JSON.stringify({[requests[0].id]:{requestId:requests[0].id,status:'failed'}}));
  render(<RequestFlow request={requests[0]} adapter={api}/>);await screen.findByText('Simulation failed');
  expect(screen.queryByRole('button',{name:'Retry simulated payment'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Recheck policy before retry'}));
  await screen.findByRole('button',{name:'Retry simulated payment'});
});

test('persisted pause blocks review and confirmation from a fresh adapter', async () => {
  const request = requests[0];
  const decision = await adapter().runAgent(request);
  const initial = await fixtureSettings.loadMandate!();
  const paused = await fixtureSettings.saveMandate({ ...initial, active: false, version: initial.version + 1 });
  expect(await fixtureSettings.loadMandate!()).toEqual(paused);
  expect(await adapter().runAgent(request)).toMatchObject({
    outcome: 'protected', reasons: ['Mandate is paused.'], mandateVersion: paused.version,
  });
  await expect(adapter().confirmPayment(decision, `fixture:${request.id}`)).rejects.toThrow('Protected');
  expect(await adapter().payment(request.id)).toBeNull();
  await fixtureSettings.saveMandate({ ...paused, active: true, version: paused.version + 1 });
  const fresh = await adapter().runAgent(request);
  await expect(adapter().confirmPayment(decision, `fixture:${request.id}`)).rejects.toThrow('stale');
  await adapter().confirmPayment(fresh, `fixture:${request.id}`);
  expect((await fixtureSettings.loadMandate!()).spent).toBe('31250.00');
  await adapter().payment(request.id, true);
  expect((await fixtureSettings.loadMandate!()).spent).toBe('49700.00');
});
