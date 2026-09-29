class WgerWorkoutHistoryCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._workouts = [];
    this._selectedId = "";
    this._detail = null;
    this._listLoading = false;
    this._detailLoading = false;
    this._loaded = false;
    this._error = "";
    this._requestId = 0;
  }

  static getStubConfig() { return {}; }
  getCardSize() {
    const height = this.shadowRoot.querySelector(".card")?.scrollHeight;
    return Math.max(3, Math.ceil((height || (this._detail ? 1000 : 250)) / 50));
  }

  getGridOptions() {
    return {
      columns: 12,
      min_columns: 6,
    };
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    const entryChanged = this._config.entry_id !== config.entry_id;
    this._config = { title: "Explorar entrenamientos", ...config };
    if (entryChanged) {
      this._loaded = false;
      this._workouts = [];
      this._selectedId = "";
      this._detail = null;
      this._listLoading = false;
      this._detailLoading = false;
      this._requestId++;
    }
    this._render();
    this._loadList();
  }

  set hass(hass) {
    this._hass = hass;
    this._loadList();
  }

  _message(type, extra = {}) {
    return {
      type,
      ...(this._config.entry_id ? { entry_id: this._config.entry_id } : {}),
      ...extra,
    };
  }

  async _loadList() {
    if (!this._hass?.connection || this._loaded || this._listLoading) return;
    this._listLoading = true;
    this._error = "";
    this._render();
    const requestId = ++this._requestId;
    try {
      const result = await this._hass.connection.sendMessagePromise(
        this._message("wger/workout_history")
      );
      if (requestId !== this._requestId) return;
      this._workouts = Array.isArray(result.workouts) ? result.workouts : [];
      this._loaded = true;
    } catch (error) {
      if (requestId !== this._requestId) return;
      this._error = "No se pudo cargar el historial. Reinténtalo.";
    } finally {
      if (requestId === this._requestId) {
        this._listLoading = false;
        this._render();
      }
    }
  }

  async _select(sessionId) {
    this._selectedId = sessionId;
    this._detail = null;
    this._error = "";
    const requestId = ++this._requestId;
    if (!sessionId) {
      this._render();
      return;
    }
    const session = this._workouts.find((item) => String(item.session_id) === sessionId);
    if (!session) {
      this._selectedId = "";
      this._render();
      return;
    }
    this._detailLoading = true;
    this._render();
    try {
      const result = await this._hass.connection.sendMessagePromise(
        this._message("wger/workout_detail", { session_id: sessionId })
      );
      if (requestId !== this._requestId) return;
      this._detail = result.workout || null;
      if (!this._detail) this._error = "Este entreno no tiene datos disponibles.";
    } catch (error) {
      if (requestId !== this._requestId) return;
      this._error = "No se pudo cargar el detalle. Selecciona el entreno de nuevo.";
    } finally {
      if (requestId === this._requestId) {
        this._detailLoading = false;
        this._render();
      }
    }
  }

  _escape(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  _number(value, digits = 0) {
    if (value === null || value === undefined || value === "" || !Number.isFinite(Number(value))) return "—";
    return Number(value).toLocaleString("es-ES", { maximumFractionDigits: digits });
  }

  _date(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString("es-ES", {
      day: "numeric", month: "short", year: "numeric",
    });
  }

  _time(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleTimeString("es-ES", {
      hour: "2-digit", minute: "2-digit",
    });
  }

  _duration(value) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
    const minutes = Math.max(0, Math.round(Number(value)));
    return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
  }

  _metric(label, value, unit = "") {
    return `<div class="metric"><span>${this._escape(label)}</span><strong>${this._escape(value)}</strong><small>${this._escape(unit)}</small></div>`;
  }

  _barRow(label, value, max, display, color = "cyan") {
    const width = max > 0 ? Math.max(0, Math.min(100, Number(value) / max * 100)) : 0;
    return `<div class="bar-row"><div class="bar-label" title="${this._escape(label)}">${this._escape(label)}</div><div class="bar-track"><div class="bar-fill ${color}" style="width:${width.toFixed(1)}%"></div></div><b>${this._escape(display)}</b></div>`;
  }

  _charts(data) {
    const exercises = Array.isArray(data.exercises) ? data.exercises : [];
    const muscles = Array.isArray(data.muscle_distribution) ? data.muscle_distribution : [];
    const maxVolume = Math.max(0, ...exercises.map((item) => Number(item.total_volume) || 0));
    const hasCompleteVolume = data.totals?.total_volume !== null;
    const exerciseRows = (hasCompleteVolume ? exercises : []).filter((item) => Number(item.total_volume) > 0).map((item) =>
      this._barRow(item.name || `Ejercicio ${item.exercise_id}`, item.total_volume, maxVolume,
        this._number(item.total_volume, 1), "cyan")
    ).join("");
    const muscleRows = muscles.map((item) => this._barRow(
      item.muscle, item.percentage, 100, `${this._number(item.percentage, 1)} %`, "violet"
    )).join("");
    return `<div class="charts">
      <section class="panel"><div class="section-head"><div><span class="eyebrow">DISTRIBUCIÓN</span><h3>Volumen por ejercicio</h3></div><span class="section-icon">↗</span></div>
        ${exerciseRows || `<p class="muted">${hasCompleteVolume ? "No hay cargas registradas para mostrar la gráfica." : "No se puede calcular el volumen completo con las unidades registradas."}</p>`}</section>
      <section class="panel"><div class="section-head"><div><span class="eyebrow">ESTIMACIÓN</span><h3>Grupos musculares</h3></div><span class="section-icon">◎</span></div>
        ${muscleRows || '<p class="muted">No hay distribución muscular disponible.</p>'}
        ${muscleRows ? '<p class="footnote">Reparto estimado a partir del volumen y los músculos asociados a cada ejercicio.</p>' : ''}
      </section></div>`;
  }

  _setValue(actual, target, suffix = "") {
    const current = this._number(actual, 2);
    const planned = this._number(target, 2);
    return `<strong>${this._escape(current)}${current === "—" ? "" : this._escape(suffix)}</strong>${planned !== "—" ? `<small>Objetivo ${this._escape(planned)}${this._escape(suffix)}</small>` : ""}`;
  }

  _exercise(item, index) {
    const sets = Array.isArray(item.sets) ? item.sets : [];
    const maxWeight = Math.max(0, ...sets.map((set) => Number(set.weight) || 0));
    const setRows = sets.map((set, setIndex) => {
      const weight = Number(set.weight);
      const width = maxWeight > 0 && Number.isFinite(weight) ? Math.max(0, Math.min(100, weight / maxWeight * 100)) : 0;
      return `<div class="set-row">
        <span class="set-index">${setIndex + 1}</span>
        <span>${this._setValue(set.repetitions, set.repetitions_target)}${set.repetitions_unit_name ? `<small>${this._escape(set.repetitions_unit_name)}</small>` : ""}</span>
        <span class="weight-cell">${this._setValue(set.weight, set.weight_target, set.weight_unit_name ? ` ${set.weight_unit_name}` : "")}<i style="width:${width.toFixed(1)}%"></i></span>
        <span>${this._setValue(set.rir, set.rir_target)}</span>
        <span>${this._setValue(set.rest, set.rest_target, " s")}</span>
      </div>`;
    }).join("");
    const muscleNames = [...(item.muscle_names || []), ...(item.muscle_names_secondary || [])];
    return `<article class="exercise panel">
      <div class="exercise-title"><div class="number-badge">${String(index + 1).padStart(2, "0")}</div><div><h3>${this._escape(item.name || `Ejercicio ${item.exercise_id}`)}</h3>
        <p>${this._escape(muscleNames.join(" · ") || "Grupo muscular no disponible")}</p></div></div>
      <div class="exercise-stats"><span><b>${this._number(sets.length)}</b> series</span><span><b>${this._number(item.total_repetitions, 1)}</b> reps</span><span><b>${this._number(item.total_volume, 1)}</b> kg·rep</span><span><b>${this._number(item.max_weight, 1)}</b> peso máximo${item.weight_unit_name ? ` (${this._escape(item.weight_unit_name)})` : ""}</span></div>
      <div class="sets-table"><div class="set-header"><span>Serie</span><span>Reps</span><span>Peso</span><span>RIR</span><span>Descanso</span></div>
        ${setRows || '<p class="muted">Sin series registradas.</p>'}</div>
    </article>`;
  }

  _detailHtml(data) {
    const totals = data.totals || {};
    const exercises = Array.isArray(data.exercises) ? data.exercises : [];
    return `<div class="detail">
      <div class="hero"><div><span class="eyebrow">ENTRENAMIENTO COMPLETADO · ${this._escape(this._date(data.date_start || data.date))}</span>
        <h2>${this._escape(data.workout_name || "Entrenamiento")}</h2>
        <p>${this._escape(data.routine_name || "Rutina")}${data.date_start ? ` · ${this._escape(this._time(data.date_start))}${data.date_end ? `–${this._escape(this._time(data.date_end))}` : ""}` : ""}</p></div>
        <div class="duration">${this._escape(this._duration(data.duration))}<small>DURACIÓN</small></div></div>
      <div class="metrics">
        ${this._metric("Ejercicios", this._number(totals.total_exercises), "movimientos")}
        ${this._metric("Series", this._number(totals.total_sets), "registradas")}
        ${this._metric("Repeticiones", this._number(totals.total_repetitions, 1), "totales")}
        ${this._metric("Volumen", this._number(totals.total_volume, 1), "kg × rep.")}
        ${this._metric("RIR medio", this._number(data.average_rir, 1), "repeticiones en reserva")}
      </div>
      ${this._charts(data)}
      <section class="exercise-section"><div class="section-head"><div><span class="eyebrow">DETALLE</span><h3>Ejercicios y series</h3></div><span class="count">${this._number(exercises.length)} ejercicios</span></div>
        ${exercises.length ? exercises.map((item, index) => this._exercise(item, index)).join("") : '<div class="panel empty">Este entreno no tiene series registradas.</div>'}
      </section>
    </div>`;
  }

  _render() {
    const options = this._workouts.map((item) => {
      const id = String(item.session_id);
      const name = item.workout_name || `Entrenamiento ${id}`;
      return `<option value="${this._escape(id)}" ${id === this._selectedId ? "selected" : ""}>${this._escape(this._date(item.date_start))} · ${this._escape(name)}</option>`;
    }).join("");
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="/wger/frontend/wger-theme.css">
      <link rel="stylesheet" href="/wger/frontend/wger-workout-history-card.css">
      <ha-card class="card"><div class="topline"><span class="eyebrow">WGER · HISTORIAL</span><span class="top-count">${this._loaded ? `${this._workouts.length} entrenos recientes` : ""}</span></div>
        <h1>${this._escape(this._config.title || "Explorar entrenamientos")}</h1>
        <p class="intro">Elige un entreno completado para ver sus métricas, distribución y cada serie registrada.</p>
        <label for="workout-picker">Entrenamiento</label>
        <div class="picker-wrap"><select id="workout-picker" ${!this._workouts.length ? "disabled" : ""}>
          <option value="" ${!this._selectedId ? "selected" : ""}>${!this._loaded ? "Cargando entrenos…" : this._workouts.length ? "Selecciona un entrenamiento" : "No hay entrenos completados"}</option>
          ${options}</select><span aria-hidden="true">⌄</span></div>
        ${this._error ? `<div class="notice error" role="alert">${this._escape(this._error)} <button type="button" id="retry">Reintentar</button></div>` : ""}
        ${this._detailLoading ? '<div class="notice loading" role="status">Cargando detalle del entreno…</div>' : ""}
        ${this._detail ? this._detailHtml(this._detail) : !this._selectedId && !this._listLoading && !this._error ? '<div class="empty-prompt"><span>↗</span><strong>Tu historial, en detalle</strong><p>Selecciona una sesión para explorar cómo fue tu entrenamiento.</p></div>' : ""}
      </ha-card>`;
    this.shadowRoot.querySelector("#workout-picker")?.addEventListener("change", (event) => this._select(event.target.value));
    this.shadowRoot.querySelector("#retry")?.addEventListener("click", () => {
      if (this._selectedId) this._select(this._selectedId);
      else { this._loaded = false; this._loadList(); }
    });
  }
}

customElements.define("wger-workout-history-card", WgerWorkoutHistoryCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "wger-workout-history-card",
  name: "Wger · Historial de entrenamientos",
  description: "Selecciona uno de los últimos 20 entrenos completados y consulta su detalle visual.",
});
