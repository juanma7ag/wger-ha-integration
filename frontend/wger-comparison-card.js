class WgerComparisonCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { entity: "sensor.workout_comparison", title: "Tu última sesión, en contexto", ...config };
    this._render();
  }

  set hass(hass) { this._hass = hass; this._render(); }

  static getStubConfig() { return { entity: "sensor.workout_comparison" }; }

  _escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    })[char]);
  }

  _number(value) {
    return typeof value === "number" && Number.isFinite(value)
      ? value.toLocaleString("es-ES", { maximumFractionDigits: 1 }) : "—";
  }

  _date(value) {
    // The API snapshot already uses Home Assistant's timezone, not the browser's.
    const date = String(value || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return "—";
    return new Date(`${date}T12:00:00`).toLocaleDateString("es-ES", {
      day: "numeric", month: "short", year: "numeric",
    });
  }

  _metric(key, metric) {
    const labels = { sets: "Series", repetitions: "Repeticiones", volume: "Volumen", duration: "Duración" };
    const delta = metric.delta;
    const valid = typeof delta === "number" && Number.isFinite(delta);
    const signed = (value) => `${value > 0 ? "+" : ""}${this._number(value)}`;
    const change = !valid ? "No comparable" : delta === 0 ? "Sin cambio"
      : `${signed(delta)} ${metric.unit}`;
    const percent = valid && delta !== 0 && typeof metric.percent === "number" && Number.isFinite(metric.percent)
      ? ` (${signed(metric.percent)} %)` : "";
    return `<div class="metric">
      <span class="metric-label">${labels[key]}</span>
      <strong>${this._number(metric.current)} <small>${this._escape(metric.unit)}</small></strong>
      <span class="previous">Anterior: ${this._number(metric.previous)} ${this._escape(metric.unit)}</span>
      <span class="delta ${valid && delta !== 0 ? "changed" : ""}">${this._escape(change + percent)}</span>
    </div>`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    const state = this._hass.states[this._config.entity];
    const data = state?.attributes || {};
    const messages = {
      no_sessions: "Todavía no hay sesiones finalizadas para comparar.",
      no_day: "La última sesión finalizada no tiene un día de rutina asociado. No se puede elegir una sesión equivalente.",
      no_previous: "Es la primera sesión registrada para este día de rutina. La comparativa aparecerá cuando lo repitas.",
      no_logs: "Faltan registros de ejercicios en una de las dos sesiones.",
      incomplete_history: "Los registros recibidos están incompletos. No se muestran totales parciales.",
      invalid_session: "Las fechas o referencias de las sesiones no permiten una comparación fiable.",
    };
    const ready = state?.state === "ready" && data.current && data.previous && data.metrics;
    const unavailable = !state ? `No se encuentra ${this._config.entity}. Comprueba la entidad configurada.`
      : messages[state.state] || "Datos no disponibles. Esperando la próxima actualización.";
    const metrics = ["sets", "repetitions", "volume", "duration"];
    const notes = [];
    if (data.exercise_selection_changed) notes.push("Los ejercicios registrados difieren entre las dos sesiones; tenlo en cuenta al comparar sus totales.");
    if (data.repetitions_comparable === false) notes.push("Repeticiones no comparables: hay registros de tiempo, distancia o valores sin unidad o cantidad válida.");
    if (data.volume_comparable === false) notes.push("Volumen no comparable: requiere repeticiones y cargas en kg o lb en todos los registros. El peso corporal y las placas no se convierten a kg.");

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/wger/frontend/wger-theme.css">
      <link rel="stylesheet" href="/wger/frontend/wger-comparison-card.css">
      <ha-card class="comparison-card">
        <header><div><span class="kicker">WGER · COMPARATIVA</span>
          <h2>${this._escape(this._config.title)}</h2></div>
          <ha-icon icon="mdi:compare-horizontal"></ha-icon>
        </header>
        ${ready ? `
          <p class="routine">${this._escape(data.routine_name || "Misma rutina")} · Mismo día de rutina</p>
          <div class="sessions"><div><span>ANTERIOR</span><strong>${this._escape(this._date(data.previous.date_start))}</strong></div>
            <ha-icon icon="mdi:arrow-right"></ha-icon>
            <div><span>ÚLTIMA FINALIZADA</span><strong>${this._escape(this._date(data.current.date_start))}</strong></div></div>
          <div class="metrics">${metrics.filter((key) => data.metrics[key]).map((key) => this._metric(key, data.metrics[key])).join("")}</div>
          ${notes.length ? `<ul class="notes">${notes.map((note) => `<li>${this._escape(note)}</li>`).join("")}</ul>` : ""}
          <footer>Las diferencias describen cambios, no una valoración del entrenamiento.<br>Volumen = carga en kg × repeticiones.</footer>
        ` : `<p class="empty" role="status">${this._escape(unavailable)}</p>`}
      </ha-card>`;
  }

  getCardSize() { return 10; }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }
}

if (!customElements.get("wger-comparison-card")) {
  customElements.define("wger-comparison-card", WgerComparisonCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "wger-comparison-card", name: "Wger · Comparativa de sesiones",
    description: "Compara tu última sesión finalizada con la anterior del mismo día de rutina.", preview: true,
  });
}
