const PLAYER = "media_player.sfr_box_8";
const REMOTE = "remote.sfr_box_8";
const FAVORITES = [{ name: "Guadeloupe 1ère", channel: "5" }];
const CHANNEL = /^[0-9]{1,4}$/;

const style = `
  :host { display: block; }
  ha-card { box-sizing: border-box; padding: 20px; }
  h2 { margin: 0; font-size: 1.25rem; color: var(--primary-text-color); }
  p { margin: 5px 0 0; color: var(--secondary-text-color); }
  button, input { box-sizing: border-box; font: inherit; }
  button {
    min-height: 46px; border: 1px solid var(--divider-color);
    border-radius: 12px; background: var(--secondary-background-color);
    color: var(--primary-text-color); cursor: pointer; font-weight: 600;
  }
  button:hover:enabled { border-color: var(--primary-color); }
  button:disabled { opacity: .48; cursor: default; }
  button:focus-visible, input:focus-visible {
    outline: 2px solid var(--primary-color); outline-offset: 2px;
  }
  ha-icon { --mdc-icon-size: 20px; }
  .controls, .number, .keys, .favorites { display: grid; gap: 8px; }
  .controls { grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 16px 0 18px; }
  .controls button { display: grid; gap: 3px; place-content: center; justify-items: center; padding: 7px 2px; }
  .controls button span { font-size: .78rem; }
  .channel-step { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: -8px 0 18px; }
  .channel-step button { display: flex; align-items: center; justify-content: center; gap: 5px; padding: 0 6px; }
  .controls [data-power][aria-pressed="true"] { color: var(--primary-color); border-color: currentColor; }
  .number { grid-template-columns: minmax(0, 1fr) auto; margin: 6px 0 8px; }
  .number button { padding: 0 16px; background: var(--primary-color); color: var(--text-primary-color, white); border-color: transparent; }
  .number input {
    width: 100%; min-width: 0; border: 1px solid var(--divider-color);
    border-radius: 12px; background: var(--card-background-color);
    color: var(--primary-text-color); padding: 0 12px; font-size: 1.15rem;
    font-variant-numeric: tabular-nums;
  }
  label { color: var(--primary-text-color); }
  .keys { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .keys button { font-size: 1.14rem; }
  .keys button[data-edit] { font-size: .84rem; }
  .favorites { grid-template-columns: repeat(auto-fit, minmax(min(100%, 120px), 1fr)); margin-top: 16px; }
  .favorites button { text-align: left; padding: 10px 12px; display: grid; gap: 3px; overflow-wrap: anywhere; }
  .favorites button small { color: var(--secondary-text-color); font-weight: 400; }
  .message { margin-top: 10px; }
  .message:empty { display: none; }
  .message[data-error="true"] { color: var(--error-color); }
`;

class SfrCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (config.entity && !config.entity.startsWith("media_player.")) {
      throw new Error("Choisis une entité media_player.");
    }
    this.config = { entity: PLAYER, ...config };
    this.render();
    this.update();
  }

  set hass(hass) {
    this.home = hass;
    this.update();
  }

  get player() {
    return this.home?.states[this.config?.entity];
  }

  get available() {
    return !!this.player && !["unknown", "unavailable"].includes(this.player.state);
  }

  get on() {
    return this.available && !["off", "standby"].includes(this.player.state);
  }

  shell(markup) {
    this.shadowRoot.innerHTML = `
      <style>${style}</style>
      <ha-card>${markup}<p class="message" role="status" aria-live="polite"></p></ha-card>
    `;
  }

  async run(domain, action, data, success = "", onSuccess) {
    if (!this.available || this.pending) return;
    this.pending = true;
    this.message("", false);
    this.update();
    try {
      await this.home.callService(domain, action, data);
      onSuccess?.();
      this.message(success, false);
    } catch (error) {
      const detail = typeof error?.message === "string" ? error.message : "";
      this.message(detail || "Commande impossible. Réessaie dans un instant.", true);
    } finally {
      this.pending = false;
      this.update();
    }
  }

  message(text, error) {
    const status = this.shadowRoot.querySelector(".message");
    status.textContent = text;
    status.dataset.error = String(error);
  }

  tune(channel, onSuccess) {
    if (!CHANNEL.test(channel)) return;
    return this.run("media_player", "play_media", {
      entity_id: this.config.entity,
      media_content_type: "channel",
      media_content_id: channel,
    }, `Chaîne ${channel} demandée`, onSuccess);
  }
}

class SfrRemoteCard extends SfrCard {
  static getStubConfig() {
    return { entity: PLAYER, remote: REMOTE };
  }

  getCardSize() {
    return 9;
  }

  render() {
    this.shell(`
      <h2>Télécommande TV</h2>
      <p data-state></p>
      <div class="controls">
        <button type="button" data-power><ha-icon icon="mdi:power"></ha-icon><span>Marche</span></button>
        <button type="button" data-key="VOL_DOWN" aria-label="Baisser le volume"><ha-icon icon="mdi:volume-minus"></ha-icon><span>Vol −</span></button>
        <button type="button" data-key="VOL_UP" aria-label="Monter le volume"><ha-icon icon="mdi:volume-plus"></ha-icon><span>Vol +</span></button>
        <button type="button" data-key="MUTE" aria-label="Basculer le son"><ha-icon icon="mdi:volume-mute"></ha-icon><span>Muet</span></button>
      </div>
      <div class="channel-step" aria-label="Changer de chaîne">
        <button type="button" data-key="CHAN_DOWN" aria-label="Chaîne précédente"><ha-icon icon="mdi:chevron-down"></ha-icon><span>Chaîne −</span></button>
        <button type="button" data-key="CHAN_UP" aria-label="Chaîne suivante"><ha-icon icon="mdi:chevron-up"></ha-icon><span>Chaîne +</span></button>
      </div>
      <form>
        <label for="channel-number">Numéro de chaîne</label>
        <div class="number">
          <input id="channel-number" type="text" inputmode="numeric" maxlength="4" autocomplete="off" placeholder="Ex. 99">
          <button type="submit">OK</button>
        </div>
      </form>
      <div class="keys" aria-label="Pavé numérique">
        ${[1,2,3,4,5,6,7,8,9].map((digit) => `<button type="button" data-digit="${digit}">${digit}</button>`).join("")}
        <button type="button" data-edit="clear">Effacer</button>
        <button type="button" data-digit="0">0</button>
        <button type="button" data-edit="backspace" aria-label="Effacer le dernier chiffre"><ha-icon icon="mdi:backspace-outline"></ha-icon></button>
      </div>
    `);
    const root = this.shadowRoot;
    this.input = root.querySelector("input");
    this.input.addEventListener("input", () => {
      this.input.value = this.input.value.replace(/[^0-9]/g, "").slice(0, 4);
      this.update();
    });
    root.querySelector("form").addEventListener("submit", (event) => {
      event.preventDefault();
      this.tune(this.input.value, () => { this.input.value = ""; });
    });
    root.querySelector("[data-power]").addEventListener("click", () => {
      this.run("media_player", this.on ? "turn_off" : "turn_on", { entity_id: this.config.entity });
    });
    for (const button of root.querySelectorAll("[data-key]")) {
      button.addEventListener("click", () => this.run("remote", "send_command", {
        entity_id: this.config.remote ?? REMOTE,
        command: [button.dataset.key],
      }));
    }
    for (const button of root.querySelectorAll("[data-digit]")) {
      button.addEventListener("click", () => {
        this.input.value = (this.input.value + button.dataset.digit).slice(0, 4);
        this.update();
      });
    }
    for (const button of root.querySelectorAll("[data-edit]")) {
      button.addEventListener("click", () => {
        this.input.value = button.dataset.edit === "clear" ? "" : this.input.value.slice(0, -1);
        this.update();
      });
    }
  }

  update() {
    if (!this.input) return;
    const root = this.shadowRoot;
    const locked = Boolean(this.pending);
    const power = root.querySelector("[data-power]");
    power.disabled = !this.available || locked;
    power.setAttribute("aria-pressed", String(this.on));
    power.setAttribute("aria-label", this.on ? "Mettre le décodeur en veille" : "Allumer le décodeur");
    power.querySelector("span").textContent = this.on ? "Veille" : "Marche";
    root.querySelector("[data-state]").textContent = !this.available ? "Décodeur indisponible"
      : this.on ? (this.player.attributes.media_title || "Décodeur allumé") : "Décodeur en veille";
    const remote = this.home?.states[this.config.remote ?? REMOTE];
    const remoteReady = remote && !["unknown", "unavailable"].includes(remote.state);
    for (const button of root.querySelectorAll("[data-key]")) {
      button.disabled = !this.on || !remoteReady || locked;
    }
    for (const button of root.querySelectorAll("[data-digit]")) {
      button.disabled = locked || this.input.value.length >= 4;
    }
    for (const button of root.querySelectorAll("[data-edit]")) {
      button.disabled = locked || this.input.value.length === 0;
    }
    this.input.readOnly = locked;
    root.querySelector("[type=submit]").disabled = !this.available || locked || !CHANNEL.test(this.input.value);
  }
}

class SfrFavoritesCard extends SfrCard {
  static getStubConfig() {
    return { entity: PLAYER, favorites: FAVORITES };
  }

  static getConfigElement() {
    return document.createElement("sfr-favorites-editor");
  }

  getCardSize() {
    return Math.max(3, 2 + (this.config?.favorites?.length ?? 0));
  }

  render() {
    this.shell('<h2>Chaînes favorites</h2><div class="favorites"></div>');
    const container = this.shadowRoot.querySelector(".favorites");
    const favorites = this.config.favorites ?? FAVORITES;
    if (!favorites.length) {
      container.textContent = "Ajoute tes raccourcis en modifiant cette carte.";
    }
    for (const favorite of favorites) {
      const channel = String(favorite.channel ?? "");
      const button = document.createElement("button");
      const name = document.createElement("span");
      const number = document.createElement("small");
      button.type = "button";
      button.dataset.channel = channel;
      name.textContent = favorite.name || `Chaîne ${channel}`;
      number.textContent = `Canal ${channel}`;
      button.append(name, number);
      button.addEventListener("click", () => this.tune(channel));
      container.append(button);
    }
  }

  update() {
    for (const button of this.shadowRoot.querySelectorAll("[data-channel]")) {
      button.disabled = !this.available || Boolean(this.pending) || !CHANNEL.test(button.dataset.channel);
    }
  }
}

class SfrFavoritesEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this.config = config;
    this.favorites = (config.favorites ?? FAVORITES).map((favorite) => ({
      name: String(favorite.name ?? ""),
      channel: String(favorite.channel ?? ""),
    }));
    this.render();
  }

  emitConfig() {
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: { ...this.config, favorites: this.favorites.map((row) => ({ ...row })) } },
      bubbles: true,
      composed: true,
    }));
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        ${style}
        :host { padding: 8px 0; }
        .row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(64px, 85px) auto; gap: 8px; align-items: end; margin-bottom: 10px; }
        label { display: grid; gap: 5px; font-size: .9rem; }
        input { width: 100%; min-height: 44px; border: 1px solid var(--divider-color); border-radius: 8px; padding: 6px 8px; background: var(--card-background-color); color: var(--primary-text-color); }
        button { min-height: 44px; padding: 0 9px; }
      </style>
      <div class="rows"></div>
      <button type="button" class="add">Ajouter un raccourci</button>
    `;
    const rows = this.shadowRoot.querySelector(".rows");
    this.favorites.forEach((favorite, index) => {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `
        <label>Nom<input type="text" maxlength="60"></label>
        <label>Canal<input type="text" inputmode="numeric" maxlength="4"></label>
        <button type="button" aria-label="Supprimer le raccourci"><ha-icon icon="mdi:trash-can-outline"></ha-icon></button>
      `;
      const [name, channel] = row.querySelectorAll("input");
      name.value = favorite.name;
      channel.value = favorite.channel;
      for (const [field, input] of [["name", name], ["channel", channel]]) {
        input.addEventListener("change", () => {
          if (field === "channel") input.value = input.value.replace(/[^0-9]/g, "").slice(0, 4);
          this.favorites[index][field] = input.value.trim();
          this.emitConfig();
        });
      }
      row.querySelector("button").addEventListener("click", () => {
        this.favorites.splice(index, 1);
        this.render();
        this.emitConfig();
      });
      rows.append(row);
    });
    this.shadowRoot.querySelector(".add").addEventListener("click", () => {
      this.favorites.push({ name: "", channel: "" });
      this.render();
      this.shadowRoot.querySelector(".row:last-child input").focus();
      this.emitConfig();
    });
  }
}

for (const [tag, element] of [
  ["sfr-remote-card", SfrRemoteCard],
  ["sfr-favorites-card", SfrFavoritesCard],
  ["sfr-favorites-editor", SfrFavoritesEditor],
]) {
  if (!customElements.get(tag)) customElements.define(tag, element);
}

window.customCards = window.customCards || [];
for (const [type, name, description] of [
  ["sfr-remote-card", "Télécommande SFR", "Marche, veille, volume, chaînes et pavé numérique."],
  ["sfr-favorites-card", "Favoris SFR", "Raccourcis de chaînes personnalisables."],
]) {
  if (!window.customCards.some((card) => card.type === type)) {
    window.customCards.push({ type, name, description, preview: true });
  }
}
