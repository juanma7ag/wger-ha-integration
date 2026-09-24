class WgerKpiCard extends HTMLElement {
  constructor() {
    super();

    this.attachShadow({ mode: "open" });

    this._hass = null;
    this._config = {};
    this._cssLoaded = false;
  }

  setConfig(config) {
    if (!config) {
      throw new Error("Invalid configuration");
    }

    this._config = {
      trainings_entity:
        "sensor.trainings_this_week",

      sets_entity:
        "sensor.weekly_sets",

      repetitions_entity:
        "sensor.weekly_repetitions",

      volume_entity:
        "sensor.weekly_volume",

      duration_entity:
        "sensor.last_workout_duration",

      days_since_entity:
        "sensor.days_since_last_workout",

      ...config,
    };

    this._loadStyles();
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get hass() {
    return this._hass;
  }

  _loadStyles() {
    if (this._cssLoaded) {
      return;
    }

    const link = document.createElement("link");

    link.rel = "stylesheet";
    link.href = "/wger/frontend/wger-kpi-card.css";

    this.shadowRoot.appendChild(link);

    this._cssLoaded = true;
  }

  _getState(entityId) {
    if (!this._hass || !entityId) {
      return null;
    }

    return this._hass.states[entityId] || null;
  }

  _escapeHtml(value) {
    if (
      value === null ||
      value === undefined
    ) {
      return "";
    }

    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  _number(value, fallback = 0) {
    const number = Number(value);

    return Number.isFinite(number)
      ? number
      : fallback;
  }

  _formatNumber(
    value,
    decimals = 0
  ) {
    const number = this._number(value);

    return number.toLocaleString(
      "es-ES",
      {
        minimumFractionDigits:
          decimals,

        maximumFractionDigits:
          decimals,
      }
    );
  }

  _formatVolume(value) {
    const number = this._number(value);

    return `${number.toLocaleString(
      "es-ES",
      {
        maximumFractionDigits: 0,
      }
    )} kg`;
  }

  _formatDuration(value) {
    const number = this._number(value);

    if (number <= 0) {
      return "—";
    }

    const rounded =
      Math.round(number);

    return `${rounded} min`;
  }

  _formatDays(value) {
    const number = this._number(value);

    if (number < 0) {
      return "—";
    }

    if (number === 0) {
      return "Hoy";
    }

    if (number === 1) {
      return "Hace 1 día";
    }

    return `Hace ${number} días`;
  }

  _render() {
    if (!this._hass) {
      return;
    }

    const trainings =
      this._getState(
        this._config.trainings_entity
      );

    const sets =
      this._getState(
        this._config.sets_entity
      );

    const repetitions =
      this._getState(
        this._config.repetitions_entity
      );

    const volume =
      this._getState(
        this._config.volume_entity
      );

    const duration =
      this._getState(
        this._config.duration_entity
      );

    const daysSince =
      this._getState(
        this._config.days_since_entity
      );

    if (
      !trainings &&
      !sets &&
      !repetitions &&
      !volume &&
      !duration &&
      !daysSince
    ) {
      this.shadowRoot.innerHTML = `
        <link
          rel="stylesheet"
          href="/wger/frontend/wger-kpi-card.css"
        >

        <div class="error">
          No se han encontrado
          los sensores de entrenamiento.
        </div>
      `;

      return;
    }

    const trainingsValue =
      this._number(
        trainings?.state
      );

    const setsValue =
      this._number(
        sets?.state
      );

    const repetitionsValue =
      this._number(
        repetitions?.state
      );

    const volumeValue =
      this._number(
        volume?.state
      );

    const durationValue =
      this._number(
        duration?.state
      );

    const daysSinceValue =
      this._number(
        daysSince?.state,
        -1
      );

    this.shadowRoot.innerHTML = `
      <link
        rel="stylesheet"
        href="/wger/frontend/wger-kpi-card.css"
      >

      <article class="wger-kpi-card">


        <!-- HEADER -->

        <header class="card-header">

          <div>

            <span class="section-kicker">
              TRAINING OVERVIEW
            </span>

            <h1>
              Workout KPIs
            </h1>

          </div>


          <div class="period-badge">

            THIS WEEK

          </div>

        </header>


        <!-- WEEKLY KPIs -->

        <section class="kpi-grid">


          ${this._renderKpi(
            "01",
            this._formatNumber(
              trainingsValue
            ),
            "ENTRENAMIENTOS",
            "workouts"
          )}


          ${this._renderKpi(
            "02",
            this._formatNumber(
              setsValue
            ),
            "SERIES",
            "sets"
          )}


          ${this._renderKpi(
            "03",
            this._formatNumber(
              repetitionsValue
            ),
            "REPETICIONES",
            "repetitions"
          )}


        </section>


        <!-- VOLUME -->

        <section class="volume-card">

          <div class="volume-label">

            <span>
              WEEKLY VOLUME
            </span>

            <strong>
              VOLUMEN
            </strong>

          </div>


          <div class="volume-value">

            ${this._escapeHtml(
              this._formatVolume(
                volumeValue
              )
            )}

          </div>

        </section>


        <!-- RECENT ACTIVITY -->

        <section class="activity-section">


          <div class="activity-card">

            <div class="activity-icon duration-icon">
              ⏱
            </div>


            <div class="activity-content">

              <span>
                ÚLTIMO ENTRENAMIENTO
              </span>

              <strong>
                ${this._escapeHtml(
                  this._formatDuration(
                    durationValue
                  )
                )}
              </strong>

            </div>

          </div>


          <div class="activity-card">

            <div class="activity-icon days-icon">
              ◷
            </div>


            <div class="activity-content">

              <span>
                ÚLTIMA ACTIVIDAD
              </span>

              <strong>
                ${this._escapeHtml(
                  this._formatDays(
                    daysSinceValue
                  )
                )}
              </strong>

            </div>

          </div>


        </section>


        <!-- FOOTER -->

        <footer class="card-footer">

          <span>
            WGER FITNESS
          </span>

          <span>
            TRAINING ANALYTICS
          </span>

        </footer>


      </article>
    `;
  }

  _renderKpi(
    number,
    value,
    label,
    type
  ) {
    return `
      <div
        class="
          kpi-card
          kpi-${this._escapeHtml(
            type
          )}
        "
      >

        <div class="kpi-number">

          ${this._escapeHtml(
            number
          )}

        </div>


        <div class="kpi-content">

          <strong>

            ${this._escapeHtml(
              value
            )}

          </strong>


          <span>

            ${this._escapeHtml(
              label
            )}

          </span>

        </div>

      </div>
    `;
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return {
      rows: 6,
      columns: 12,
      min_rows: 4,
      min_columns: 6,
    };
  }
}


if (
  !customElements.get(
    "wger-kpi-card"
  )
) {
  customElements.define(
    "wger-kpi-card",
    WgerKpiCard
  );
}


window.customCards =
  window.customCards || [];


window.customCards.push({
  type: "wger-kpi-card",

  name: "Wger Workout KPIs",

  description:
    "Training overview and workout KPI card for Wger.",

  preview: true,
});