class WgerWeeklyGoalCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = {
      entity: "sensor.weekly_goal_progress",
      title: "Objetivo semanal",
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  static getStubConfig() {
    return { entity: "sensor.weekly_goal_progress" };
  }

  _escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    })[char]);
  }

  _date(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return "";
    // Calendar dates must not shift with the browser's timezone.
    return new Date(`${value}T12:00:00`).toLocaleDateString("es-ES", {
      day: "numeric", month: "short",
    });
  }

  _render() {
    if (!this._config || !this._hass) return;
    const state = this._hass.states[this._config.entity];
    const attrs = state?.attributes || {};
    const completed = attrs.completed;
    const target = attrs.target;
    const available = state && !["unknown", "unavailable"].includes(state.state)
      && Number.isInteger(completed) && completed >= 0
      && Number.isInteger(target) && target > 0;
    const achieved = available && completed >= target;
    const progress = available ? Math.min(100, completed / target * 100) : 0;
    const remaining = available ? Math.max(0, target - completed) : 0;
    const message = achieved ? "Objetivo cumplido"
      : completed === 0 ? "Tu semana empieza con la primera sesión"
      : `Te ${remaining === 1 ? "queda 1 sesión" : `quedan ${remaining} sesiones`}`;

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/wger/frontend/wger-theme.css">
      <link rel="stylesheet" href="/wger/frontend/wger-weekly-goal-card.css">
      <ha-card class="goal-card ${achieved ? "achieved" : ""}">
        <header>
          <div><span class="kicker">WGER · CONSTANCIA</span>
            <h2>${this._escape(this._config.title)}</h2></div>
          <ha-icon icon="${achieved ? "mdi:check-decagram" : "mdi:target"}"></ha-icon>
        </header>
        ${available ? `
          <p class="period">${this._escape(this._date(attrs.week_start))} — ${this._escape(this._date(attrs.week_end))}</p>
          <div class="score"><strong>${completed}</strong><span>de ${target}<br>entrenamientos</span></div>
          <div class="progress-label"><span>${this._escape(message)}</span><strong>${Math.round(progress)} %</strong></div>
          <div class="track" role="progressbar" aria-label="Objetivo semanal"
            aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(progress)}"
            aria-valuetext="${completed} de ${target} entrenamientos">
            <div class="fill" style="width:${progress}%"></div>
          </div>
          <footer>Sesiones finalizadas · Lunes a domingo</footer>
        ` : `<p class="unavailable" role="status">${state
          ? "Datos no disponibles. Esperando la próxima actualización."
          : `No se encuentra ${this._escape(this._config.entity)}. Comprueba la entidad configurada.`}</p>`}
      </ha-card>`;
  }

  getCardSize() { return 3; }
  getGridOptions() { return { columns: 12, rows: 4, min_columns: 6, min_rows: 4 }; }
}

if (!customElements.get("wger-weekly-goal-card")) {
  customElements.define("wger-weekly-goal-card", WgerWeeklyGoalCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "wger-weekly-goal-card",
    name: "Wger · Objetivo semanal",
    description: "Sesiones completadas y progreso hacia tu objetivo semanal.",
    preview: true,
  });
}
