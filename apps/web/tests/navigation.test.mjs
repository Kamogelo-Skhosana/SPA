import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const navigation = readFileSync(new URL("../src/navigation.ts", import.meta.url), "utf8");
const shell = readFileSync(new URL("../src/App.tsx", import.meta.url), "utf8");
const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

test("all four required routes are declared", () => {
  for (const route of ["/overview", "/payables", "/mandate", "/setup"]) {
    assert.ok(navigation.includes(`path: "${route}"`));
  }
});
test("navigation indicates active page and supports keyboard access", () => {
  assert.match(shell, /aria-current=/);
  assert.match(shell, /aria-expanded=/);
  assert.match(shell, /aria-modal="true"/);
  assert.match(shell, /Escape/);
  assert.match(shell, /hashchange/);
});
test("simulated and testnet states are labeled and responsive", () => {
  assert.match(shell, /Demo data is simulated/);
  assert.match(shell, /Simulated preview/);
  assert.match(css, /max-width:850px/);
  assert.match(css, /focus-visible/);
});
