import React from 'react';
import { afterEach, expect, test } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from '../src/App';
afterEach(() => { cleanup(); window.location.hash = ''; });
test('search filters pages, traps focus and restores the opener', () => {
  render(<App />);
  const opener = screen.getByRole('button', { name: 'Search workspace pages' });
  opener.focus(); fireEvent.click(opener);
  const input = screen.getByRole('textbox', { name: 'Search pages' });
  expect(document.activeElement).toBe(input);
  fireEvent.change(input, { target: { value: 'mandate' } });
  const link = screen.getByRole('dialog').querySelector('a')!;
  expect(link.textContent).toContain('Mandate');
  link.focus(); fireEvent.keyDown(window, { key: 'Tab' });
  expect(document.activeElement).toBe(input);
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(document.activeElement).toBe(opener);
});
test('mobile menu exposes its controlled navigation and closes with Escape', () => {
  render(<App />);
  const button = screen.getByRole('button', { name: 'Open menu' });
  fireEvent.click(button);
  expect(button.getAttribute('aria-expanded')).toBe('true');
  expect(document.getElementById(button.getAttribute('aria-controls')!)).not.toBeNull();
  fireEvent.keyDown(window, { key: 'Escape' });
  expect(button.getAttribute('aria-expanded')).toBe('false');
  expect(document.activeElement).toBe(button);
});

test('Enter opens the sole page match and closes search', async () => {
  render(<App />);
  fireEvent.click(screen.getByRole('button', { name: 'Search workspace pages' }));
  const input = screen.getByRole('textbox', { name: 'Search pages' });
  fireEvent.change(input, { target: { value: 'payables' } });
  fireEvent.keyDown(input, { key: 'Enter' });
  expect(screen.queryByRole('dialog')).toBeNull();
  await screen.findByRole('heading', { name: 'Supplier payment queue' });
});
