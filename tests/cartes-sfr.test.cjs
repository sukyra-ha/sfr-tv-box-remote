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

function cardTestContext() {
  const context = {
    HTMLElement: class { attachShadow() {} },
    customElements: createRegistry(true),
    window: {},
  };
  vm.runInNewContext(moduleSource, context);
  return context;
}

function testEntity(entity_id, device_id, platform = "sfr_box_8") {
  return { entity_id, device_id, platform };
}

test("existing cards with the old defaults use a single renamed SFR decoder", async () => {
  const context = cardTestContext();
  const RemoteCard = context.customElements.get("sfr-remote-card");
  const FavoritesCard = context.customElements.get("sfr-favorites-card");
  const players = [
    testEntity("media_player.decodeur_salon", "salon"),
    testEntity("remote.autre_nom", "salon"),
    testEntity("media_player.television", "tv", "webostv"),
  ];
  const calls = [];
  const home = {
    entities: Object.fromEntries(players.map((entity) => [entity.entity_id, entity])),
    states: Object.fromEntries(players.map((entity) => [entity.entity_id, { state: "on" }])),
    callService: async (...args) => calls.push(args),
  };

  const remote = new RemoteCard();
  remote.config = { entity: "media_player.sfr_box_8", remote: "remote.sfr_box_8" };
  remote.home = home;
  remote.update = () => {};
  remote.message = () => {};
  remote.shell = () => {};
  const handlers = {};
  const power = { addEventListener: (_event, callback) => { handlers.power = callback; } };
  const key = {
    dataset: { key: "CHAN_UP" },
    addEventListener: (_event, callback) => { handlers.channel = callback; },
  };
  const placeholder = { addEventListener() {} };
  remote.shadowRoot = {
    querySelector: (selector) => selector === "[data-power]" ? power : placeholder,
    querySelectorAll: (selector) => selector === "[data-key]" ? [key] : [],
  };
  remote.render();
  await handlers.power();
  await handlers.channel();

  const favorites = new FavoritesCard();
  favorites.config = { entity: "media_player.sfr_box_8" };
  favorites.home = home;
  favorites.update = () => {};
  favorites.message = () => {};
  await favorites.tune("5");

  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [
    ["media_player", "turn_off", { entity_id: "media_player.decodeur_salon" }],
    ["remote", "send_command", { entity_id: "remote.autre_nom", command: ["CHAN_UP"] }],
    ["media_player", "play_media", {
      entity_id: "media_player.decodeur_salon", media_content_type: "channel", media_content_id: "5",
    }],
  ]);
});

test("two SFR decoders require a selection and the remote stays paired to the same device", () => {
  const context = cardTestContext();
  const RemoteCard = context.customElements.get("sfr-remote-card");
  const entities = [
    testEntity("media_player.sfr_box_8", "chambre"),
    testEntity("remote.sfr_box_8", "chambre"),
    testEntity("media_player.decodeur_salon", "salon"),
    testEntity("remote.decodeur_different", "salon"),
  ];
  const card = new RemoteCard();
  card.home = {
    entities: Object.fromEntries(entities.map((entity) => [entity.entity_id, entity])),
    states: Object.fromEntries(entities.map((entity) => [entity.entity_id, { state: "on" }])),
  };
  card.config = RemoteCard.getStubConfig();
  assert.equal(card.playerId, undefined);
  assert.equal(card.available, false);
  card.config = { entity: "media_player.decodeur_salon", remote: "remote.sfr_box_8" };
  assert.equal(card.playerId, "media_player.decodeur_salon");
  assert.equal(card.remoteId, "remote.decodeur_different");
  card.config = { entity: "media_player.sfr_box_8" };
  assert.equal(card.remoteId, "remote.sfr_box_8");
});
