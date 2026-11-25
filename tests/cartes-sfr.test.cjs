const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const moduleSource = fs.readFileSync(
  path.join(__dirname, "../custom_components/sfr_box_8/cartes-sfr.js"),
  "utf8",
);

function createRegistry(ready = false) {
  const elements = new Map();
  if (ready) elements.set("home-assistant", class {});
  return {
    get: (tag) => elements.get(tag),
    define(tag, element) {
      assert.ok(!elements.has(tag), `${tag} registered twice`);
      elements.set(tag, element);
    },
  };
}

test("SFR cards wait for the registry Home Assistant uses", () => {
  const original = createRegistry();
  const callbacks = [];
  const context = {
    HTMLElement: class {},
    customElements: original,
    window: { setTimeout: (callback) => callbacks.push(callback) },
  };
  vm.runInNewContext(moduleSource, context);
  assert.equal(original.get("sfr-remote-card"), undefined);
  assert.equal(callbacks.length, 1);
  assert.equal(context.window.customCards, undefined);

  context.customElements = createRegistry(true);
  callbacks.shift()();

  assert.equal(typeof context.customElements.get("sfr-remote-card"), "function");
  assert.equal(typeof context.customElements.get("sfr-favorites-card"), "function");
  assert.equal(typeof context.customElements.get("sfr-favorites-editor"), "function");
  assert.equal(context.window.customCards.length, 2);
});

test("SFR cards register immediately when Home Assistant is ready", () => {
  const context = { HTMLElement: class {}, customElements: createRegistry(true), window: {} };
  vm.runInNewContext(moduleSource, context);
  assert.equal(typeof context.customElements.get("sfr-remote-card"), "function");
  assert.equal(context.window.customCards.length, 2);
});
