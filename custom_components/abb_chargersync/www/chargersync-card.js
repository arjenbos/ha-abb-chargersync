/** ChargerSync management UI. Data stays in this card, outside Recorder attributes. */
const TABS = {
  schedules: "Schedules", history: "History & costs", limits: "Current limits",
  solar: "Solar settings", tariffs: "Tariffs", reports: "Reports",
  diagnostics: "Diagnostics", manage: "Charger",
};
const RESOURCES = {
  schedules: ["schedules"], history: ["sessions", "currencies"], limits: ["load_limits"],
  solar: ["solar_offsets"], tariffs: ["price", "currencies"], reports: ["auto_export"],
  diagnostics: ["diagnostics", "firmware"], manage: [],
};
const node = (tag, text, props = {}) => {
  const element = document.createElement(tag);
  if (text !== undefined && text !== null) element.textContent = String(text);
  Object.assign(element, props);
  return element;
};
const rows = value => Array.isArray(value) ? value : Array.isArray(value?.data) ? value.data : [];
const numeric = value => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
const energyKwh = value => numeric(value) ? Number(value) / 1000 : null;
const enabled = value => value === true || Number(value) === 1;
const display = value => value === null || value === undefined ? "—" : typeof value === "object" ? JSON.stringify(value) : String(value);
const seconds = value => { const [h, m] = value.split(":").map(Number); return h * 3600 + m * 60; };
const clock = value => `${String(Math.floor(value / 3600)).padStart(2, "0")}:${String(Math.floor(value % 3600 / 60)).padStart(2, "0")}`;
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const dayNames = mask => DAYS.filter((_,i) => mask & (1 << i)).join(", ");
const apiTime = value => value.replace("T", " ") + (value.length === 16 ? ":00" : "");

export class ChargerSyncCard extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode: "open"}); this.data = {}; this.errors = {};
    this.tab = "schedules"; this.page = 0; this.busy = false; this.loaded = false;
    this.filters = {}; this.message = "";
  }
  setConfig(config) {
    if (!config.entity && !config.device_id) throw new Error("Set entity to this charger's charging-status entity, or set device_id.");
    this.config = config; this.deviceId = config.device_id; this.loaded = false;
    this.tab = config.tab in TABS ? config.tab : "schedules"; this.render();
  }
  set hass(hass) {
    this._hass = hass;
    if (this.config && !this.loaded && !this.initializing) {
      this.initializing = true;
      this.initialize().finally(() => { this.initializing = false; });
    }
  }
  getCardSize() { return 12; }
  getGridOptions() { return {columns: 12, rows: "auto", min_columns: 6}; }
  static getStubConfig(hass) {
    const entity = Object.keys(hass?.states || {}).find(id =>
      id.endsWith("_charging_status") && hass?.entities?.[id]?.platform === "abb_chargersync"
    ) || Object.keys(hass?.states || {}).find(id => id.endsWith("_charging_status"));
    return {entity: entity || "sensor.charger_charging_status"};
  }
  static getConfigForm() {
    return {
      schema: [
        {name: "entity", required: true, selector: {entity: {domain: "sensor", integration: "abb_chargersync"}}},
        {name: "title", selector: {text: {}}},
        {name: "tab", selector: {select: {options: Object.entries(TABS).map(([value,label]) => ({value,label}))}}},
      ],
      computeLabel: field => ({entity: "Charger status entity", title: "Card title", tab: "Default tab"})[field.name],
      computeHelper: field => field.name === "entity" ? "Choose the Charging status sensor of your ChargerSync charger." : undefined,
    };
  }
  async initialize() {
    try {
      if (!this.deviceId) {
        const entities = await this._hass.callWS({type: "config/entity_registry/list"});
        const entry = entities.find(e => e.entity_id === this.config.entity && e.platform === "abb_chargersync");
        if (!entry?.device_id) throw new Error("Choose a ChargerSync entity belonging to a charger.");
        this.deviceId = entry.device_id;
      }
      this.loaded = true;
      await this.load();
    } catch (error) { this.message = error.message || String(error); this.render(); }
  }
  async call(service, data = {}) {
    const response = await this._hass.callWS({
      type: "call_service", domain: "abb_chargersync", service,
      service_data: {device_id: this.deviceId, ...data}, return_response: true,
    });
    return response?.response?.result;
  }
  async load() {
    if (!this.deviceId || this.busy) return;
    this.busy = true; this.message = ""; this.render();
    // Serialize remote queries; a failed optional resource does not hide other sections.
    for (const resource of RESOURCES[this.tab]) {
      try {
        this.data[resource] = await this.call("get_data", {
          resource, ...(resource === "sessions" ? {...this.filters, page: this.page, limit: 20} : {}),
        });
        delete this.errors[resource];
      } catch (error) { delete this.data[resource]; this.errors[resource] = error.message || String(error); }
    }
    this.busy = false; this.render();
  }
  async mutate(service, data, confirmation) {
    if (this.busy || !this.deviceId) return;
    if (confirmation && !window.confirm(confirmation)) return;
    this.busy = true; this.message = ""; this.setDisabled(true);
    try {
      await this.call(service, data); this.busy = false; await this.load();
      this.editSchedule = null; this.message = "Saved successfully.";
    } catch (error) { this.message = error.message || String(error); }
    finally { this.busy = false; this.render(); }
  }
  setDisabled(disabled) { this.shadowRoot.querySelectorAll("button").forEach(b => { b.disabled = disabled; }); }
  button(label, callback, parent, secondary = false) {
    const b = node("button", label, {type: "button", disabled: this.busy});
    b.className = secondary ? "secondary" : "";
    b.addEventListener("click", callback); parent.append(b); return b;
  }
  field(parent, key, label, type = "text", value = "", options = {}) {
    const wrapper = node("label", label);
    let input;
    if (Array.isArray(type)) {
      input = node("select");
      for (const choice of type) {
        const [v, name] = Array.isArray(choice) ? choice : [choice, choice];
        input.append(node("option", name, {value: String(v)}));
      }
    } else input = node("input", null, {type});
    input.name = key;
    if (type === "checkbox") input.checked = Boolean(value);
    else input.value = value ?? "";
    Object.assign(input, options); wrapper.append(input); parent.append(wrapper); return input;
  }
  form(title, callback, buttonLabel = "Save") {
    const section = node("section"); section.append(node("h3", title));
    const form = node("form"); section.append(form);
    const submit = node("button", buttonLabel, {type: "submit", disabled: this.busy});
    const fields = node("div"); fields.className = "fields"; form.append(fields, submit);
    form.addEventListener("submit", event => {
      event.preventDefault(); if (this.busy || !form.reportValidity()) return;
      const values = {};
      for (const el of form.elements) if (el.name) values[el.name] = el.type === "checkbox" ? el.checked : el.type === "number" && el.value !== "" ? Number(el.value) : el.value;
      try { callback(values); } catch (error) { this.message = error.message; this.render(); }
    });
    this.content.append(section); return fields;
  }
  table(headers, data, action) {
    if (!data.length) { this.content.append(node("p", "No records returned.")); return; }
    const wrap = node("div"); wrap.className = "table-scroll";
    const table = node("table"); const head = node("tr");
    for (const h of headers) head.append(node("th", h[0]));
    if (action) head.append(node("th", "Actions")); table.append(head);
    for (const row of data) {
      const tr = node("tr");
      for (const [, key] of headers) tr.append(node("td", display(typeof key === "function" ? key(row) : row[key])));
      if (action) { const cell = node("td"); action(row, cell); tr.append(cell); }
      table.append(tr);
    }
    wrap.append(table); this.content.append(wrap);
  }
  details(title, value) {
    const details = node("details"); details.append(node("summary", title), node("pre", JSON.stringify(value, null, 2)));
    this.content.append(details);
  }
  render() {
    if (!this.config) return;
    this.shadowRoot.replaceChildren();
    const style = node("style", `
      :host{display:block;color:var(--primary-text-color)}ha-card{overflow:hidden}
      header{padding:24px 24px 12px}h2{margin:0 0 8px;font-size:24px;font-weight:500}h3{font-size:17px;margin:8px 0 18px}
      p{line-height:1.5;color:var(--secondary-text-color)}nav{display:flex;gap:8px;flex-wrap:wrap;padding:0 24px 16px;border-bottom:1px solid var(--divider-color)}
      .content{padding:20px 24px}section{padding:16px 0;border-bottom:1px solid var(--divider-color)}
      .fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:0 0 16px}
      label{display:flex;flex-direction:column;gap:7px;font-size:13px;color:var(--secondary-text-color)}
      input,select{font:inherit;color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:8px;padding:10px;min-width:0}
      input[type=checkbox]{align-self:start;width:22px;height:22px}button{cursor:pointer;border:0;border-radius:20px;padding:10px 16px;font:inherit;background:var(--primary-color);color:var(--text-primary-color,#fff);margin:3px}
      button.secondary{background:var(--secondary-background-color);color:var(--primary-text-color)}button:disabled{opacity:.45;cursor:wait}
      button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--primary-color);outline-offset:3px}
      .message{padding:12px 24px;background:var(--secondary-background-color)}.error{color:var(--error-color)}
      .table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:12px 8px;text-align:left;border-bottom:1px solid var(--divider-color);white-space:nowrap}
      pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}details{margin:16px 0}summary{cursor:pointer}svg{width:100%;height:180px} .stats{display:flex;gap:24px;flex-wrap:wrap}.stats strong{font-size:24px;display:block}
      @media(max-width:500px){header,.content{padding:16px}nav{padding:0 16px 12px}.fields{grid-template-columns:1fr}}
    `);
    const card = node("ha-card"); const header = node("header");
    header.append(node("h2", this.config.title || "ChargerSync management"), node("p", "Schedules, charging history and cloud settings"));
    const nav = node("nav"); nav.setAttribute("aria-label", "ChargerSync sections");
    for (const [key, label] of Object.entries(TABS)) {
      const b = this.button(label, () => { this.tab = key; this.message = ""; this.load(); }, nav, this.tab !== key);
      b.setAttribute("aria-pressed", String(this.tab === key));
    }
    card.append(header, nav);
    if (this.message) { const message = node("div", this.message); message.className = "message"; message.setAttribute("role", "status"); card.append(message); }
    this.content = node("div"); this.content.className = "content"; card.append(this.content);
    if (!this.loaded) {
      this.content.append(node("p", "Connecting to Home Assistant…"));
      this.button("Reconnect", () => this.initialize(), this.content);
    } else {
      this.button(this.busy ? "Loading…" : "Refresh", () => this.load(), this.content, true);
      for (const resource of RESOURCES[this.tab]) if (this.errors[resource]) {
        const error = node("p", `${resource}: ${this.errors[resource]}`); error.className = "error"; error.setAttribute("role", "alert"); this.content.append(error);
      }
      this[`render_${this.tab}`]();
    }
    this.shadowRoot.append(style, card);
  }
  currency(value) {
    const c = rows(this.data.currencies).find(c => String(c.currencyType) === String(value));
    return c ? c.tag || c.name || c.symbol || String(value) : value === undefined ? "Not reported" : `ID ${value}`;
  }
  render_schedules() {
    this.content.append(node("p", "Schedules follow the charger's cloud time settings. A window may cross midnight."));
    const schedules = rows(this.data.schedules);
    this.table([["Start", "startTime"], ["End", "endTime"], ["Enabled", r => Number(r.open) === 1 ? "Yes" : "No"]], schedules, (row, cell) => {
      this.button("Edit", () => { this.editSchedule = row; this.render(); }, cell, true);
      this.button("Delete", () => this.mutate("delete_schedule", {schedule_id: row.id}, "Delete this charging schedule?"), cell, true);
    });
    const edit = this.editSchedule;
    const fields = this.form(edit ? "Edit schedule" : "New schedule", values => {
      const service = edit ? "update_schedule" : "create_schedule";
      const data = edit ? {...values, schedule_id: edit.id} : values;
      return this.mutate(service, data);
    });
    this.field(fields, "start_time", "Start", "time", edit?.startTime || "22:00", {required: true});
    this.field(fields, "end_time", "End", "time", edit?.endTime || "06:00", {required: true});
    this.field(fields, "enabled", "Enabled", "checkbox", edit ? Number(edit.open) === 1 : true);
    if (edit) this.button("Cancel edit", () => { this.editSchedule = null; this.render(); }, this.content, true);
  }
  render_history() {
    const fields = this.form("Filter sessions", values => {
      this.filters = {};
      if (values.start_time) this.filters.start_time = apiTime(values.start_time);
      if (values.end_time) this.filters.end_time = apiTime(values.end_time);
      if (values.company !== "all") this.filters.company_only = values.company === "company";
      this.page = 0; return this.load();
    }, "Apply filters");
    this.field(fields, "start_time", "From", "datetime-local", this.filters.start_time?.replace(" ", "T"));
    this.field(fields, "end_time", "Until", "datetime-local", this.filters.end_time?.replace(" ", "T"));
    this.field(fields, "company", "Session type", [["all", "All"], ["company", "Company"], ["private", "Private"]], this.filters.company_only === undefined ? "all" : this.filters.company_only ? "company" : "private");
    const sessions = rows(this.data.sessions);
    const stats = node("div"); stats.className = "stats";
    const totalEnergy = sessions.filter(r => numeric(r.energy)).reduce((sum, r) => sum + Number(r.energy) / 1000, 0);
    const energy = node("div", "Energy on this page"); energy.append(node("strong", `${totalEnergy.toFixed(2)} kWh`)); stats.append(energy);
    const currencyGroups = new Map();
    for (const r of sessions) if (numeric(r.cost) && r.currencyType !== undefined) currencyGroups.set(r.currencyType, (currencyGroups.get(r.currencyType) || 0) + Number(r.cost));
    for (const [currency, cost] of currencyGroups) { const el = node("div", `Cost on this page · ${this.currency(currency)}`); el.append(node("strong", cost.toFixed(2))); stats.append(el); }
    this.content.append(stats);
    this.content.append(node("p", "Page totals cover the returned sessions only. Costs come from ChargerSync; different currencies are kept separate."));
    this.table([["Started", "startTime"], ["Stopped", "stopTime"], ["Energy (kWh)", r => energyKwh(r.energy)], ["Solar (kWh)", r => energyKwh(r.solarEnergy)], ["Solar share", r => numeric(r.energy) && Number(r.energy) > 0 && numeric(r.solarEnergy) ? `${(100 * Number(r.solarEnergy) / Number(r.energy)).toFixed(1)}%` : "—"], ["Cost", "cost"], ["Currency", r => this.currency(r.currencyType)], ["Duration (s)", "duration"], ["Company", r => Number(r.isCompanyCarSession) === 1 ? "Yes" : "No"], ["Finish reason", "chargeFinishReason"]], sessions, (row, cell) => {
      if (row.orderId) this.button(Number(row.isCompanyCarSession) === 1 ? "Mark private" : "Mark company", () => this.mutate("set_company_session", {session_id: String(row.orderId), company: Number(row.isCompanyCarSession) !== 1}), cell, true);
    });
    const prev = this.button("Previous", () => { this.page--; this.load(); }, this.content, true); prev.disabled = this.busy || this.page === 0;
    this.content.append(node("span", `Page ${this.page + 1}`));
    const next = this.button("Next", () => { this.page++; this.load(); }, this.content, true); next.disabled = this.busy || sessions.length < 20;
    const tf = this.form("Cloud statistics", values => this.loadTrends(values), "Load statistics");
    this.field(tf, "start_time", "From", "date", this.filters.start_time?.slice(0,10), {required: true});
    this.field(tf, "end_time", "Until", "date", this.filters.end_time?.slice(0,10), {required: true});
    this.field(tf, "trend_type", "Grouping", [["week", "Week"], ["month", "Month"], ["year", "Year"]], "week");
    if (this.trendError) this.content.append(node("p", this.trendError));
    if (this.data.trends !== undefined) {
      const trendRows = rows(this.data.trends?.trends ?? this.data.trends);
      this.content.append(node("p", `Statistics currency: ${this.currency(this.data.trends?.currencyType)}`));
      this.table([["Date", "date"], ["Energy (kWh)", r => energyKwh(r.energy)], ["Cost", "cost"], ["Duration (s)", "duration"], ["Sessions", "trans"]], trendRows);
      this.graph(trendRows);
      this.graph(trendRows, "cost");
    }
    this.details("Session details returned by ChargerSync", this.data.sessions);
  }
  async loadTrends(values) {
    if (this.busy) return;
    this.busy = true; this.setDisabled(true);
    try {
      if (values.end_time < values.start_time) throw new Error("End must not precede start.");
      this.data.trends = await this.call("get_data", {
        resource: "trends", ...values,
        start_time: `${values.start_time} 00:00:00`, end_time: `${values.end_time} 23:59:59`,
        ...(this.filters.company_only === undefined ? {} : {company_only:this.filters.company_only}),
      }); this.trendError = "";
    }
    catch (error) { delete this.data.trends; this.trendError = error.message || String(error); }
    finally { this.busy = false; this.render(); }
  }
  graph(data, metric = "energy") {
    const records = data.filter(r => numeric(r[metric])); if (!records.length) return;
    const value = r => metric === "energy" ? energyKwh(r.energy) : Number(r.cost);
    const titleText = metric === "energy" ? "Energy by date (kWh)" : `Cost by date (${this.currency(this.data.trends?.currencyType)})`;
    const max = Math.max(1, ...records.map(value));
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg"); svg.setAttribute("viewBox", "0 0 600 180"); svg.setAttribute("role", "img"); svg.setAttribute("aria-label", titleText);
    records.forEach((r, index) => {
      const rect = document.createElementNS(svg.namespaceURI, "rect");
      const width = 600 / records.length; const height = Math.max(0, value(r)) / max * 150;
      for (const [k, v] of Object.entries({x: index * width + 2, y: 160 - height, width: Math.max(1, width - 4), height, fill: "var(--primary-color)"})) rect.setAttribute(k, String(v));
      const title = document.createElementNS(svg.namespaceURI, "title"); title.textContent = `${r.date}: ${value(r)}`; rect.append(title); svg.append(rect);
    });
    this.content.append(node("h3", titleText), svg);
  }
  render_limits() {
    const current = this.data.load_limits;
    if (!current) return;
    if (!this.limitDraft) this.limitDraft = (current.ranges || []).map(r => ({...r}));
    this.content.append(node("p", "Saving replaces the complete list of timed limits, including any country-specific windows. Existing random-delay settings are preserved. Split overnight windows at midnight."));
    this.table([["Days", r => dayNames(r.weekdays)], ["From", r => clock(r.from)], ["Until", r => clock(r.to)], ["Limit (A)", "limit"]], this.limitDraft, (row, cell) => {
      this.button("Remove", () => { this.limitDraft.splice(this.limitDraft.indexOf(row), 1); this.render(); }, cell, true);
    });
    const fields = this.form("Add time window to draft", values => {
      const from = seconds(values.from); const to = values.to === "24:00" ? 86400 : seconds(values.to);
      if (from >= to) throw new Error("End must be after start. Split overnight windows at midnight.");
      const weekdays = DAYS.reduce((mask,_,i) => mask | (values[`day_${i}`] ? 1 << i : 0), 0);
      if (!weekdays) throw new Error("Select at least one day.");
      this.limitDraft.push({weekdays, from, to, limit: values.limit}); this.render();
    }, "Add window");
    DAYS.forEach((day,i) => this.field(fields, `day_${i}`, day, "checkbox", true));
    this.field(fields, "from", "From", "time", "00:00", {required:true});
    this.field(fields, "to", "Until (24:00 allowed)", "text", "24:00", {pattern:"(?:[01][0-9]|2[0-3]):[0-5][0-9]|24:00", required:true});
    this.field(fields, "limit", "Current (A)", "number", 16, {min:0, max:255, step:1, required:true});
    const save = this.form("Apply draft", values => this.mutate("replace_load_limits", {ranges: this.limitDraft, enabled: values.enabled}, "Replace all timed current limits with this draft?"));
    this.field(save, "enabled", "Enable timed limits", "checkbox", enabled(current.enabled));
    this.button("Discard draft", () => { this.limitDraft = null; this.render(); }, this.content, true);
  }
  render_solar() {
    const current = this.data.solar_offsets; if (!current) return;
    const fields = this.form("Solar and Eco mix thresholds", values => this.mutate("set_solar_offsets", {settings: values}));
    for (const [key, value] of Object.entries(current)) {
      const isCurrent = key.endsWith("current");
      this.field(fields, key, key.replaceAll("_", " ") + (isCurrent ? " (A)" : " (s)"), "number", value, {min:0, max:isCurrent ? 5 : 120, step:isCurrent ? 0.1 : 1, required:true});
    }
    this.content.append(node("p", "Default/session mode, solar enable and Eco mix minimum current remain available as regular entities in the Charging view."));
  }
  render_tariffs() {
    const current = this.data.price; if (!current || Array.isArray(current)) return;
    const fields = this.form("Charging tariffs", values => this.mutate("set_price", {settings: Object.fromEntries(Object.entries(values).filter(([,v]) => v !== "").map(([k,v]) => [k, k === "currencyType" ? Number(v) : v]))}));
    this.field(fields, "averagePrice", "Average price per kWh", "number", current.averagePrice, {min:0, step:0.0001});
    const currencies = rows(this.data.currencies).filter(c => c.currencyType !== undefined);
    if (currencies.length) this.field(fields, "currencyType", "Currency", currencies.map(c => [c.currencyType, c.tag || c.name || c.symbol || c.currencyType]), current.currencyType);
    else this.field(fields, "currencyType", "Currency ID", "number", current.currencyType, {min:0, step:1});
    for (const period of ["offPeak", "midPeak", "onPeak"]) {
      this.field(fields, `${period}St`, `${period} start`, "time", current[`${period}St`]);
      this.field(fields, `${period}Et`, `${period} end`, "time", current[`${period}Et`]);
      this.field(fields, `${period}Price`, `${period} price per kWh`, "number", current[`${period}Price`], {min:0, step:0.0001});
    }
    this.details("Currency identifiers supplied by ChargerSync", this.data.currencies);
  }
  render_reports() {
    const current = this.data.auto_export;
    if (current && !Array.isArray(current)) {
      const fields = this.form("Automatic reports", values => this.mutate("set_auto_export", {settings: {...values, cycle: Number(values.cycle)}}));
      this.field(fields, "enabled", "Enabled", "checkbox", enabled(current.enabled));
      this.field(fields, "email", "Recipient email", "email", current.email, {required:true});
      this.field(fields, "format", "Format", ["csv", "excel", "pdf"], current.format || "csv");
      this.field(fields, "cycle", "Every (months)", [[1,"1"],[3,"3"],[6,"6"]], current.cycle || 1);
      this.field(fields, "isCompanyCarSession", "Company sessions only", "checkbox", enabled(current.isCompanyCarSession));
    }
    const fields = this.form("Export sessions by email", values => {
      values.start_time = apiTime(values.start_time); values.end_time = apiTime(values.end_time);
      return this.mutate("export_sessions", values, `Ask ChargerSync to email this report to ${values.email}?`);
    }, "Send export");
    this.field(fields, "email", "Recipient email", "email", "", {required:true});
    this.field(fields, "format", "Format", ["csv", "excel", "pdf"], "csv");
    this.field(fields, "start_time", "From", "datetime-local", "", {required:true});
    this.field(fields, "end_time", "Until", "datetime-local", "", {required:true});
    this.field(fields, "company_only", "Company sessions only", "checkbox", false);
  }
  render_diagnostics() {
    const d = this.data.diagnostics;
    if (d) {
      this.table([["Check", "name"], ["Result", "value"]], [
        {name:"Cloud online", value:d.cloud_online}, {name:"Remote connected", value:d.remote_available},
        {name:"Model", value:d.model}, {name:"Firmware", value:d.firmware},
      ]);
      this.details("Capability and connection diagnostics", d);
    }
    this.details("Available firmware packages (installation requires the official app)", this.data.firmware);
    const fields = this.form("Read charger logs", values => this.loadLogs(values), "Read logs");
    this.field(fields, "log_from", "Starting serial number", "number", this.logFrom ?? 0, {min:0, step:1, required:true});
    this.field(fields, "limit", "Records (maximum 50)", "number", 50, {min:1, max:50, step:1, required:true});
    if (this.logError) this.content.append(node("p", this.logError));
    if (this.data.log_info) this.details("Log range", this.data.log_info);
    if (this.data.logs) this.table([["Serial", "serial"],["Timestamp", "timestamp"],["Type", "type"],["Code", "code"],["Detail", "detail"]], rows(this.data.logs));
    this.content.append(node("p", "An unsupported capability is different from a temporarily rejected read. Diagnostics show both separately. Log codes retain the vendor values."));
  }
  async loadLogs(values) {
    if (this.busy) return; this.busy = true; this.setDisabled(true);
    try {
      this.data.log_info = await this.call("get_data", {resource:"log_info"});
      this.logFrom = values.log_from || this.data.log_info.first;
      this.data.logs = await this.call("get_data", {resource:"logs", ...values, log_from:this.logFrom});
      this.logError = "";
    } catch (error) { delete this.data.logs; this.logError = error.message || String(error); }
    finally { this.busy = false; this.render(); }
  }
  render_manage() {
    const fields = this.form("Charger name", values => this.mutate("update_charger", values));
    this.field(fields, "name", "Name in ChargerSync", "text", "", {minLength:1, maxLength:100, required:true});
    this.content.append(node("p", "Home Assistant may retain a device name you have explicitly customized."));
    this.button("Refresh charger and cloud inventory", () => this.mutate("refresh"), this.content);
  }
}
if (!customElements.get("chargersync-card")) customElements.define("chargersync-card", ChargerSyncCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "chargersync-card")) {
  window.customCards.push({
    type:"chargersync-card", name:"ChargerSync management",
    description:"Schedules, history, costs, reports, limits and diagnostics",
    documentationURL:"https://github.com/arjenbos/ha-abb-cybersync/blob/main/docs/dashboard.md",
  });
}
