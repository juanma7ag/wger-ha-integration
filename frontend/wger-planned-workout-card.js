class WgerPlannedWorkoutCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { entity: "sensor.planned_workout", title: "Planificado frente a realizado", ...config };
    this._render();
  }

  set hass(hass) {
    const previous = this._hass?.states[this._config?.entity];
    this._hass = hass;
    if (previous !== hass.states[this._config?.entity]) this._render();
  }

  static getStubConfig() { return { entity: "sensor.planned_workout" }; }

  _escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
    })[char]);
  }

  _number(value) {
    return typeof value === "number" && Number.isFinite(value)
      ? value.toLocaleString("es-ES", { maximumFractionDigits: 2 }) : "—";
  }

  _range(value, max) {
    return max != null && max !== value ? `${this._number(value)}–${this._number(max)}` : this._number(value);
  }

  _date(value) {
    const date = String(value || "").slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return "—";
    return new Date(`${date}T12:00:00`).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" });
  }

  _measurement(data) {
    const unit = this._escape(data.unit || "unidad no indicada");
    const delta = typeof data.delta === "number" && Number.isFinite(data.delta)
      ? `<small class="difference">Δ ${data.delta > 0 ? "+" : ""}${this._number(data.delta)}</small>` : "";
    return `<span>${this._number(data.actual)} / ${this._number(data.target)} ${unit}${delta}</span>`;
  }

  _logs(logs) {
    if (!logs.length) return `<p class="muted">No hay registros vinculados a esta entrada.</p>`;
    return `<div class="table-scroll"><table>
      <caption>Realizado / objetivo guardado · Δ diferencia</caption>
      <thead><tr><th>Serie</th><th>Repeticiones / tiempo / distancia</th><th>Carga</th></tr></thead>
      <tbody>${logs.map((log, index) => `<tr><td>${index + 1}</td><td>${this._measurement(log.repetitions)}</td><td>${this._measurement(log.weight)}</td></tr>`).join("")}</tbody>
    </table></div>`;
  }

  _exercise(row) {
    const labels = {
      covered: "Series cubiertas", extra: "Series adicionales", partial: "Registro parcial",
      no_records: "Sin registros vinculados", uncertain: "Asociación incompleta",
    };
    const status = Object.hasOwn(labels, row.status) ? row.status : "uncertain";
    const plan = row.plan.map((group) => {
      const values = [`${this._range(group.sets, group.max_sets)} series`];
      if (group.repetitions != null) values.push(`${this._range(group.repetitions, group.max_repetitions)} ${group.repetitions_unit || "unidad no indicada"}`);
      if (group.weight != null) values.push(`${this._range(group.weight, group.max_weight)} ${group.weight_unit || "unidad no indicada"}`);
      return `<li>${this._escape(values.join(" · "))}</li>`;
    }).join("");
    return `<details class="exercise ${status}" data-entry="${this._escape(row.slot_entry_id)}">
      <summary><div><strong>${this._escape(row.name)}</strong><span class="badge">${labels[status]}</span></div>
        <span class="sets">${row.recorded_sets} / ${this._range(row.planned_sets, row.max_sets)}<small>series vinculadas / previstas</small></span>
      </summary>
      <div class="exercise-body"><h3>Plan actual de esta entrada</h3><ul class="plan">${plan}</ul>
        ${this._logs(row.logs)}
        ${row.status === "uncertain" ? `<p class="notice">Hay registros que podrían corresponder a esta entrada, pero no se pueden asociar con seguridad.</p>` : ""}
        ${row.missing_sets > 0 ? `<p class="muted">${row.missing_sets} ${row.missing_sets === 1 ? "serie sin registro vinculado" : "series sin registro vinculado"}.</p>` : ""}
        ${row.extra_sets > 0 ? `<p class="muted">${row.extra_sets} series por encima de las previstas. No compensan series de otro ejercicio.</p>` : ""}
      </div>
    </details>`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    const state = this._hass.states[this._config.entity];
    const data = state?.attributes || {};
    const ready = ["ready", "partial_links"].includes(state?.state) && Array.isArray(data.exercises);
    const messages = {
      no_sessions: "Todavía no hay sesiones finalizadas para comparar con el plan.",
      no_day: "La última sesión finalizada no está asociada a una rutina y un día.",
      no_plan: "No se encuentra un plan para el día y la iteración o fecha de esta sesión.",
      ambiguous_plan: "Los datos apuntan a más de una planificación. No se elige una por suposición.",
      invalid_plan: "La planificación no contiene los datos necesarios para contar sus series.",
      invalid_session: "Las fechas de la sesión no son válidas para esta comparación.",
      incomplete_history: "Faltan registros en la respuesta de wger. No se muestra un cumplimiento parcial como completo.",
    };
    const message = !state ? `No se encuentra ${this._config.entity}. Comprueba la entidad configurada.`
      : messages[state.state] || "Datos no disponibles. Esperando la próxima actualización.";
    const progress = typeof data.progress === "number" && Number.isFinite(data.progress) ? data.progress : null;
    // Preserve expanded exercises when a fresh coordinator snapshot arrives.
    const opened = new Set(Array.from(this.shadowRoot.querySelectorAll("details[open][data-entry]"), (el) => el.dataset.entry));
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/wger/frontend/wger-theme.css">
      <link rel="stylesheet" href="/wger/frontend/wger-planned-workout-card.css">
      <ha-card class="planned-card">
        <header><div><span class="kicker">WGER · CUMPLIMIENTO DEL PLAN</span><h2>${this._escape(this._config.title)}</h2></div>
          <ha-icon icon="mdi:clipboard-check-outline"></ha-icon></header>
        ${ready ? `
          <p class="subtitle">${this._escape(data.workout_name || "Última sesión finalizada")} · ${this._escape(this._date(data.date_start))}</p>
          <div class="score"><strong>${data.covered_sets}<small> / ${data.planned_sets}</small></strong>
            <span>series previstas con registro vinculado${data.max_sets > data.planned_sets ? " (mínimo del rango)" : ""}</span></div>
          ${progress !== null ? `<div class="progress-label"><span>Cobertura de series</span><strong>${this._number(progress)} %</strong></div>
            <div class="track" role="progressbar" aria-label="Series previstas con registro vinculado" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress}"><div class="fill" style="width:${progress}%"></div></div>`
            : `<p class="notice">${data.unlinked_count ? `${data.unlinked_count} registros sin asociar. El porcentaje queda sin calcular.` : "El plan no define un número de series mayor que cero."}</p>`}
          <p class="counts">${data.recorded_sets} series vinculadas · ${data.extra_sets} adicionales</p>
          <div class="exercises">${data.exercises.map((row) => this._exercise(row)).join("")}</div>
          ${data.unlinked_count ? `<details class="unlinked"><summary>Registros sin asociar (${data.unlinked_count})</summary>
            <ul>${data.unlinked.map((log) => `<li>${this._escape(log.name)} · Registro sin vínculo verificable con el plan</li>`).join("")}</ul></details>` : ""}
          <footer>Series previstas según la rutina actual: los cambios posteriores pueden alterar esta referencia.
            Las cargas y repeticiones se comparan con el objetivo guardado en cada registro.
            Una serie vinculada no implica haber alcanzado su carga o repeticiones objetivo.</footer>
        ` : `<p class="empty" role="status">${this._escape(message)}</p>`}
      </ha-card>`;
    this.shadowRoot.querySelectorAll("details[data-entry]").forEach((el) => { el.open = opened.has(el.dataset.entry); });
  }

  getCardSize() { return 12; }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }
}

if (!customElements.get("wger-planned-workout-card")) {
  customElements.define("wger-planned-workout-card", WgerPlannedWorkoutCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "wger-planned-workout-card", name: "Wger · Planificado frente a realizado",
    description: "Series previstas, registros vinculados y objetivos guardados de tu última sesión.", preview: true,
  });
}
