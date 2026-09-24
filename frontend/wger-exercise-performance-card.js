/* =========================================================
   WGER EXERCISE PERFORMANCE CARD
   ========================================================= */

class WgerExercisePerformanceCard extends HTMLElement {
  constructor() {
    super();

    this.attachShadow({
      mode: "open",
    });

    this._config = {};
    this._hass = null;
    this._stylesLoaded = false;
  }

  setConfig(config) {
    this._config = {
      entity: "sensor.wger_exercise_performance",
      title: "Mejor rendimiento",
      ...config,
    };

    this._render();
  }

  set hass(hass) {
    this._hass = hass;

    if (!this._config.entity) {
      return;
    }

    this._render();
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return {
      rows: 8,
      min_rows: 4,
      columns: 12,
      min_columns: 6,
    };
  }

  async _loadStyles() {
    if (this._stylesLoaded) {
      return;
    }

    this._stylesLoaded = true;

    const themeUrl = "/wger/frontend/wger-theme.css";
    const cardUrl = "/wger/frontend/wger-exercise-performance-card.css";

    try {
      const [themeResponse, cardResponse] = await Promise.all([
        fetch(themeUrl),
        fetch(cardUrl),
      ]);

      const themeCss = await themeResponse.text();
      const cardCss = await cardResponse.text();

      const style = document.createElement("style");

      style.textContent = `
        ${themeCss}

        ${cardCss}
      `;

      this.shadowRoot.appendChild(style);

      this._render();
    } catch (error) {
      console.error(
        "Wger Exercise Performance Card: unable to load styles",
        error
      );
    }
  }

  _getExercises() {
    if (!this._hass || !this._config.entity) {
      return [];
    }

    const entity = this._hass.states[this._config.entity];

    if (!entity) {
      return [];
    }

    const exercises = entity.attributes?.exercises;

    if (!Array.isArray(exercises)) {
      return [];
    }

    return exercises;
  }

  _formatNumber(value, decimals = 0) {
    if (value === null || value === undefined) {
      return "—";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "—";
    }

    return number.toLocaleString("es-ES", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  _formatWeight(value) {
    if (value === null || value === undefined) {
      return "—";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "—";
    }

    return `${this._formatNumber(number, 2)} kg`;
  }

  _formatVolume(value) {
    if (value === null || value === undefined) {
      return "—";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
      return "—";
    }

    return `${this._formatNumber(number, 2)} kg`;
  }

  _formatDate(value) {
    if (!value) {
      return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return "—";
    }

    return date.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  _hasWeight(exercise) {
    return (
      exercise?.best_weight &&
      exercise.best_weight.value !== null &&
      exercise.best_weight.value !== undefined
    );
  }

  _hasVolume(exercise) {
    return (
      exercise?.best_volume &&
      exercise.best_volume.value !== null &&
      exercise.best_volume.value !== undefined
    );
  }

  _hasRepetitions(exercise) {
    return (
      exercise?.best_repetitions &&
      exercise.best_repetitions.value !== null &&
      exercise.best_repetitions.value !== undefined
    );
  }

  _renderMetric({
    icon,
    label,
    value,
    secondary = null,
    className = "",
  }) {
    return `
      <div class="metric ${className}">
        <div class="metric-header">
          <span class="metric-icon">${icon}</span>
          <span class="metric-label">
            ${label}
          </span>
        </div>

        <div class="metric-value">
          ${value}
        </div>

        ${
          secondary
            ? `
              <div class="metric-secondary">
                ${secondary}
              </div>
            `
            : ""
        }
      </div>
    `;
  }

  _renderExercise(exercise, index) {
    const name =
      exercise.exercise_name ||
      `Ejercicio ${exercise.exercise_id}`;

    const bestWeight = exercise.best_weight;
    const bestVolume = exercise.best_volume;
    const bestRepetitions = exercise.best_repetitions;

    const hasWeight = this._hasWeight(exercise);
    const hasVolume = this._hasVolume(exercise);
    const hasRepetitions = this._hasRepetitions(exercise);

    const weightValue = hasWeight
      ? this._formatWeight(bestWeight.value)
      : "—";

    const weightSecondary =
      hasWeight && bestWeight.repetitions !== null
        ? `${this._formatNumber(bestWeight.repetitions)} repeticiones`
        : null;

    const volumeValue = hasVolume
      ? this._formatVolume(bestVolume.value)
      : "—";

    const volumeSecondary =
      hasVolume &&
      bestVolume.weight !== null &&
      bestVolume.repetitions !== null
        ? `${this._formatWeight(bestVolume.weight)} × ${this._formatNumber(bestVolume.repetitions)}`
        : null;

    const repetitionsValue = hasRepetitions
      ? this._formatNumber(bestRepetitions.value)
      : "—";

    const repetitionsSecondary =
      hasRepetitions && bestRepetitions.weight !== null
        ? `@ ${this._formatWeight(bestRepetitions.weight)}`
        : null;

    let metrics = "";

    if (hasWeight) {
      metrics += this._renderMetric({
        icon: "🏆",
        label: "MEJOR PESO",
        value: weightValue,
        secondary: weightSecondary,
        className: "metric-weight",
      });
    }

    if (hasVolume) {
      metrics += this._renderMetric({
        icon: "📊",
        label: "MEJOR VOLUMEN",
        value: volumeValue,
        secondary: volumeSecondary,
        className: "metric-volume",
      });
    }

    if (hasRepetitions) {
      metrics += this._renderMetric({
        icon: "🔥",
        label: "MEJORES REPS",
        value: repetitionsValue,
        secondary: repetitionsSecondary,
        className: "metric-repetitions",
      });
    }

    const date =
      bestWeight?.date ||
      bestVolume?.date ||
      bestRepetitions?.date ||
      null;

    return `
      <article
        class="exercise"
        data-index="${index}"
      >
        <div class="exercise-top">
          <div class="exercise-number">
            ${String(index + 1).padStart(2, "0")}
          </div>

          <div class="exercise-info">
            <div class="exercise-name">
              ${name}
            </div>

            <div class="exercise-id">
              Ejercicio #${exercise.exercise_id}
            </div>
          </div>
        </div>

        <div class="metrics">
          ${metrics}
        </div>

        ${
          date
            ? `
              <div class="exercise-footer">
                <span class="footer-icon">📅</span>
                <span>
                  Mejor marca registrada:
                  ${this._formatDate(date)}
                </span>
              </div>
            `
            : ""
        }
      </article>
    `;
  }

  _renderEmpty() {
    return `
      <div class="empty">
        <div class="empty-icon">
          🏋️
        </div>

        <div class="empty-title">
          Sin datos de rendimiento
        </div>

        <div class="empty-text">
          Todavía no hay registros de ejercicios disponibles.
        </div>
      </div>
    `;
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    if (!this._config.entity) {
      return;
    }

    this._loadStyles();

    const exercises = this._getExercises();

    const entity = this._hass?.states?.[
      this._config.entity
    ];

    const totalExercises =
      entity?.attributes?.total_exercises ??
      exercises.length;

    this.shadowRoot.innerHTML = `
      <style>
        .loading {
          min-height: 100px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--wger-muted);
          font-family: var(--wger-font);
        }
      </style>

      <ha-card class="card">

        <div class="hero">

          <div class="hero-icon">
            🏆
          </div>

          <div class="hero-content">

            <div class="hero-title">
              ${this._config.title}
            </div>

            <div class="hero-subtitle">
              Récords personales por ejercicio
            </div>

          </div>

          <div class="hero-count">
            <span class="hero-count-value">
              ${totalExercises}
            </span>

            <span class="hero-count-label">
              ejercicios
            </span>
          </div>

        </div>

        <div class="separator"></div>

        ${
          exercises.length
            ? `
              <div class="exercise-grid">
                ${exercises
                  .map((exercise, index) =>
                    this._renderExercise(
                      exercise,
                      index
                    )
                  )
                  .join("")}
              </div>
            `
            : this._renderEmpty()
        }

      </ha-card>
    `;
  }
}

customElements.define(
  "wger-exercise-performance-card",
  WgerExercisePerformanceCard
);

window.customCards = window.customCards || [];

window.customCards.push({
  type: "wger-exercise-performance-card",
  name: "Wger Exercise Performance Card",
  description:
    "Tarjeta de rendimiento histórico de ejercicios Wger",
  preview: true,
});