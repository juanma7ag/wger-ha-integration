class WgerConsistencyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { entity: "sensor.weekly_streak", title: "Tu constancia", ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  static getStubConfig() { return { entity: "sensor.weekly_streak" }; }

  _escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    })[char]);
  }

  _date(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return "";
    return new Date(`${value}T12:00:00`).toLocaleDateString("es-ES", {
      day: "2-digit", month: "2-digit",
    });
  }

  _week(week) {
    const statuses = {
      achieved: { label: "Objetivo cumplido", icon: "mdi:check" },
      in_progress: { label: "Semana en curso", icon: "mdi:progress-clock" },
      missed: { label: "Objetivo no alcanzado", icon: "mdi:minus" },
    };
    const status = statuses[week.status] || statuses.missed;
    const style = Object.hasOwn(statuses, week.status) ? week.status : "missed";
    const start = this._date(week.week_start);
    const end = this._date(week.week_end);
    const label = `${start}–${end}: ${week.completed} de ${week.target} sesiones. ${status.label}`;
    return `<li class="week ${style} ${week.is_current ? "current" : ""}"
        aria-label="${this._escape(label)}" title="${this._escape(label)}">
      <span class="week-date">${this._escape(start)}</span>
      <ha-icon icon="${status.icon}" aria-hidden="true"></ha-icon>
      <strong>${this._escape(week.completed)}<span>/${this._escape(week.target)}</span></strong>
      <span class="week-caption">${week.is_current ? "Actual" : "sesiones"}</span>
    </li>`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    const state = this._hass.states[this._config.entity];
    const data = state?.attributes || {};
    const available = state && !["unknown", "unavailable"].includes(state.state)
      && data.history_complete === true && Array.isArray(data.weeks)
      && Number.isInteger(data.current_streak) && data.current_streak >= 0
      && Number.isInteger(data.best_streak) && data.best_streak >= 0;
    const streak = data.current_streak;
    const message = data.current_week_achieved
      ? "Esta semana ya suma a tu racha."
      : streak > 0
        ? `Tu racha sigue viva. ${data.remaining === 1 ? "Falta 1 sesión" : `Faltan ${data.remaining} sesiones`} esta semana.`
        : "Completa tu objetivo esta semana para iniciar una racha.";
    const unavailable = !state
      ? `No se encuentra ${this._config.entity}. Comprueba la entidad configurada.`
      : state.state !== "unavailable" && data.history_complete === false
        ? "El historial recibido está incompleto. No se puede calcular una racha fiable."
        : "Datos no disponibles. Esperando la próxima actualización.";

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/wger/frontend/wger-theme.css">
      <link rel="stylesheet" href="/wger/frontend/wger-consistency-card.css">
      <ha-card class="consistency-card">
        <header><div><span class="kicker">WGER · SEMANA A SEMANA</span>
          <h2>${this._escape(this._config.title)}</h2></div>
          <ha-icon class="hero-icon" icon="mdi:fire"></ha-icon>
        </header>
        ${available ? `
          <section class="metrics" aria-label="Rachas semanales">
            <div class="streak"><strong>${streak}${data.streak_at_least ? "+" : ""}</strong>
              <span>${streak === 1 && !data.streak_at_least ? "semana consecutiva" : "semanas consecutivas"}</span></div>
            <div class="best"><ha-icon icon="mdi:trophy-outline"></ha-icon>
              <strong>${data.best_streak}</strong><span>Mejor racha<br>en ${this._escape(data.history_weeks)} semanas</span></div>
          </section>
          <p class="message">${this._escape(message)}</p>
          <div class="history-heading"><h3>Últimas ${data.weeks.length} semanas</h3>
            <span>Objetivo: ${this._escape(data.target)} / semana</span></div>
          <ol class="weeks">${data.weeks.map((week) => this._week(week)).join("")}</ol>
          <div class="legend"><span><i class="achieved"></i>Cumplido</span>
            <span><i class="in_progress"></i>En curso</span><span><i class="missed"></i>No alcanzado</span></div>
          <footer>Calculado con tu objetivo actual · Lunes a domingo.
            ${data.streak_at_least ? "La racha puede comenzar antes del período consultado." : ""}
          </footer>
        ` : `<p class="unavailable" role="status">${this._escape(unavailable)}</p>`}
      </ha-card>`;
  }

  getCardSize() { return 12; }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }
}

if (!customElements.get("wger-consistency-card")) {
  customElements.define("wger-consistency-card", WgerConsistencyCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "wger-consistency-card", name: "Wger · Constancia semanal",
    description: "Racha de objetivos cumplidos e historial de las últimas semanas.", preview: true,
  });
}
