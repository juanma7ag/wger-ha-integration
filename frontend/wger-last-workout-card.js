class WgerLastWorkoutCard extends HTMLElement {
  constructor() {
    super();

    this.attachShadow({ mode: "open" });

    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = {
      entity: "sensor.last_workout",
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
    if (this.shadowRoot.querySelector("link")) {
      return;
    }

    const themeLink =
      document.createElement("link");

    themeLink.rel = "stylesheet";

    themeLink.href =
      "/wger/frontend/wger-theme.css";

    const cardLink =
      document.createElement("link");

    cardLink.rel = "stylesheet";

    cardLink.href =
      "/wger/frontend/wger-last-workout-card.css";

    this.shadowRoot.appendChild(
      themeLink
    );

    this.shadowRoot.appendChild(
      cardLink
    );
  }

  _getEntity() {
    if (!this._hass) {
      return null;
    }

    return this._hass.states[
      this._config.entity
    ];
  }

  _escapeHtml(value) {
    if (
      value === null ||
      value === undefined
    ) {
      return "";
    }

    return String(value)
      .replace(
        /&/g,
        "&amp;"
      )
      .replace(
        /</g,
        "&lt;"
      )
      .replace(
        />/g,
        "&gt;"
      )
      .replace(
        /"/g,
        "&quot;"
      )
      .replace(
        /'/g,
        "&#039;"
      );
  }

  _formatNumber(
    value,
    decimals = 0
  ) {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {
      return "—";
    }

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

  _formatDecimal(
    value,
    decimals = 1
  ) {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {
      return "—";
    }

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

  _formatDate(value) {
    if (!value) {
      return "—";
    }

    const date =
      new Date(value);

    if (
      Number.isNaN(
        date.getTime()
      )
    ) {
      return value;
    }

    return date.toLocaleDateString(
      "es-ES",
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }
    );
  }

  _formatRir(value) {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {
      return "—";
    }

    return number.toLocaleString(
      "es-ES",
      {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }
    );
  }

  _formatWeight(value) {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {
      return "—";
    }

    return `${number.toLocaleString(
      "es-ES",
      {
        maximumFractionDigits: 2,
      }
    )} kg`;
  }

  _formatVolume(value) {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {
      return "—";
    }

    return `${number.toLocaleString(
      "es-ES",
      {
        maximumFractionDigits: 1,
      }
    )} kg`;
  }

  _formatDuration(value) {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    const number =
      Number(value);

    if (
      !Number.isFinite(number)
    ) {
      return "—";
    }

    return `${Math.round(
      number
    )} min`;
  }

  _getMuscleColor(index) {
    const colors = [
      "#38bdf8",
      "#818cf8",
      "#22c55e",
      "#f59e0b",
      "#f472b6",
      "#a78bfa",
      "#2dd4bf",
      "#fb7185",
    ];

    return colors[
      index % colors.length
    ];
  }

  _buildMuscleGradient(
    muscles
  ) {
    if (
      !muscles ||
      muscles.length === 0
    ) {
      return "conic-gradient(#1e293b 0deg 360deg)";
    }

    let currentAngle = 0;

    const segments =
      muscles
        .map(
          (
            muscle,
            index
          ) => {
            const percentage =
              Number(
                muscle.percentage
              );

            if (
              !Number.isFinite(
                percentage
              ) ||
              percentage <= 0
            ) {
              return null;
            }

            const start =
              currentAngle;

            currentAngle +=
              (percentage / 100) *
              360;

            const color =
              this._getMuscleColor(
                index
              );

            return `${color} ${start}deg ${currentAngle}deg`;
          }
        )
        .filter(Boolean);

    if (
      segments.length === 0
    ) {
      return "conic-gradient(#1e293b 0deg 360deg)";
    }

    return `conic-gradient(${segments.join(
      ", "
    )})`;
  }

  _renderKpi(
    value,
    label,
    modifier = ""
  ) {
    return `
      <div class="kpi ${modifier}">

        <div class="kpi-value">
          ${this._escapeHtml(
            value
          )}
        </div>

        <div class="kpi-label">
          ${this._escapeHtml(
            label
          )}
        </div>

      </div>
    `;
  }

  _renderExercise(
    exercise,
    index
  ) {
    const name =
      exercise.name ||
      `Ejercicio ${exercise.exercise_id}`;

    const muscles = [
      ...(exercise.muscle_names || []),
      ...(exercise.muscle_names_secondary || []),
    ];

    const muscleHtml =
      muscles.length
        ? muscles
            .map(
              (muscle) => `
                <span class="muscle-tag">
                  ${this._escapeHtml(
                    muscle
                  )}
                </span>
              `
            )
            .join("")
        : `
            <span class="muscle-tag muted">
              Sin datos musculares
            </span>
          `;

    const image =
      exercise.image;

    const imageHtml =
      image
        ? `
          <div class="exercise-image">

            <img
              src="${this._escapeHtml(
                image
              )}"
              alt="${this._escapeHtml(
                name
              )}"
              loading="lazy"
            />

          </div>
        `
        : `
          <div class="exercise-image no-image">
            <span>W</span>
          </div>
        `;

    const sets =
      exercise.sets || [];

    const setRows =
      sets
        .map(
          (
            set,
            setIndex
          ) => {
            const reps =
              set.repetitions;

            const target =
              set.repetitions_target;

            const repsHtml =
              reps !== null &&
              reps !== undefined
                ? `
                    <span class="actual-value">
                      ${this._escapeHtml(
                        this._formatNumber(
                          reps
                        )
                      )}
                    </span>

                    ${
                      target !== null &&
                      target !== undefined
                        ? `
                          <span class="target-value">
                            /
                            ${this._escapeHtml(
                              this._formatNumber(
                                target
                              )
                            )}
                          </span>
                        `
                        : ""
                    }
                  `
                : "—";

            const rir =
              set.rir !== null &&
              set.rir !== undefined
                ? this._formatRir(
                    set.rir
                  )
                : "—";

            const rirTarget =
              set.rir_target !== null &&
              set.rir_target !== undefined
                ? this._formatRir(
                    set.rir_target
                  )
                : null;

            const rirHtml =
              rir !== "—"
                ? `
                    <span class="rir-value">
                      ${this._escapeHtml(
                        rir
                      )}
                    </span>

                    ${
                      rirTarget !== null
                        ? `
                          <span class="target-value">
                            /
                            ${this._escapeHtml(
                              rirTarget
                            )}
                          </span>
                        `
                        : ""
                    }
                  `
                : "—";

            const weight =
              set.weight !== null &&
              set.weight !== undefined
                ? this._formatWeight(
                    set.weight
                  )
                : "—";

            return `
              <div class="set-row">

                <div class="set-number">
                  ${setIndex + 1}
                </div>

                <div class="set-reps">
                  ${repsHtml}
                </div>

                <div class="set-weight">
                  ${this._escapeHtml(
                    weight
                  )}
                </div>

                <div class="set-rir">
                  ${rirHtml}
                </div>

              </div>
            `;
          }
        )
        .join("");

    return `
      <article class="exercise-card">

        <div class="exercise-header">

          ${imageHtml}

          <div class="exercise-heading">

            <div class="exercise-number">
              ${String(
                index + 1
              ).padStart(
                2,
                "0"
              )}
            </div>

            <div class="exercise-title-block">

              <h3>
                ${this._escapeHtml(
                  name
                )}
              </h3>

              <div class="muscle-tags">
                ${muscleHtml}
              </div>

            </div>

          </div>

        </div>

        <div class="sets-table">

          <div class="set-header">

            <div>
              SET
            </div>

            <div>
              REPS
            </div>

            <div>
              PESO
            </div>

            <div>
              RIR
            </div>

          </div>

          ${setRows}

        </div>

        <div class="exercise-summary">

          <div class="summary-item">

            <span>
              REPS
            </span>

            <strong>
              ${this._escapeHtml(
                this._formatNumber(
                  exercise.total_repetitions
                )
              )}
            </strong>

          </div>

          <div class="summary-item">

            <span>
              VOLUMEN
            </span>

            <strong>
              ${this._escapeHtml(
                this._formatVolume(
                  exercise.total_volume
                )
              )}
            </strong>

          </div>

          <div class="summary-item">

            <span>
              MÁX.
            </span>

            <strong>
              ${this._escapeHtml(
                this._formatWeight(
                  exercise.max_weight
                )
              )}
            </strong>

          </div>

          <div class="summary-item">

            <span>
              RIR MEDIO
            </span>

            <strong>
              ${this._escapeHtml(
                this._formatRir(
                  exercise.average_rir
                )
              )}
            </strong>

          </div>

        </div>

      </article>
    `;
  }

  _renderMuscleDistribution(
    muscles
  ) {
    if (
      !Array.isArray(
        muscles
      ) ||
      muscles.length === 0
    ) {
      return `
        <section class="muscle-section">

          <div class="section-heading">

            <span class="section-kicker">
              MUSCLE ANALYTICS
            </span>

            <h2>
              Distribución muscular
            </h2>

          </div>

          <div class="empty-muscles">
            No hay datos musculares disponibles
            para este entrenamiento.
          </div>

        </section>
      `;
    }

    const gradient =
      this._buildMuscleGradient(
        muscles
      );

    const legend =
      muscles
        .map(
          (
            muscle,
            index
          ) => `
            <div class="muscle-legend-row">

              <div
                class="legend-dot"
                style="background:${this._getMuscleColor(
                  index
                )}"
              ></div>

              <div class="legend-name">
                ${this._escapeHtml(
                  muscle.muscle
                )}
              </div>

              <div class="legend-percentage">
                ${this._escapeHtml(
                  this._formatDecimal(
                    muscle.percentage,
                    1
                  )
                )}%
              </div>

            </div>
          `
        )
        .join("");

    return `
      <section class="muscle-section">

        <div class="section-heading">

          <span class="section-kicker">
            MUSCLE ANALYTICS
          </span>

          <h2>
            Distribución muscular
          </h2>

        </div>

        <div class="muscle-layout">

          <div class="donut-wrapper">

            <div
              class="muscle-donut"
              style="background:${gradient}"
            >

              <div class="donut-center">

                <strong>
                  ${muscles.length}
                </strong>

                <span>
                  músculos
                </span>

              </div>

            </div>

          </div>

          <div class="muscle-legend">
            ${legend}
          </div>

        </div>

      </section>
    `;
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    if (!this._config) {
      return;
    }

    const entity =
      this._getEntity();

    /*
     * IMPORTANT:
     *
     * Every render replaces
     * shadowRoot.innerHTML.
     *
     * Therefore the stylesheet
     * links must also exist inside
     * the HTML generated on every
     * render.
     */

    const styleLinks = `
      <link
        rel="stylesheet"
        href="/wger/frontend/wger-theme.css"
      />

      <link
        rel="stylesheet"
        href="/wger/frontend/wger-last-workout-card.css"
      />
    `;

    if (!entity) {
      this.shadowRoot.innerHTML = `
        ${styleLinks}

        <ha-card class="card">

          <div class="loading">
            Esperando datos de Wger...
          </div>

        </ha-card>
      `;

      return;
    }

    const attributes =
      entity.attributes || {};

    const workoutName =
      attributes.workout_name ||
      "Último entrenamiento";

    const routineName =
      attributes.routine_name ||
      "Wger Fitness";

    const date =
      attributes.date ||
      null;

    const duration =
      attributes.duration;

    const totals =
      attributes.totals ||
      {};

    const exercises =
      Array.isArray(
        attributes.exercises
      )
        ? attributes.exercises
        : [];

    const muscles =
      Array.isArray(
        attributes.muscle_distribution
      )
        ? attributes.muscle_distribution
        : [];

    const averageRir =
      attributes.average_rir;

    const dateText =
      this._formatDate(
        date
      );

    const exerciseHtml =
      exercises.length
        ? exercises
            .map(
              (
                exercise,
                index
              ) =>
                this._renderExercise(
                  exercise,
                  index
                )
            )
            .join("")
        : `
          <div class="empty-state">
            No hay ejercicios registrados
            en el último entrenamiento.
          </div>
        `;

    this.shadowRoot.innerHTML = `
      ${styleLinks}

      <ha-card class="card">

        <div class="card-content">

          <!-- HEADER -->

          <header class="hero">

            <div class="hero-top">

              <div class="hero-label">

                <span class="pulse"></span>

                LAST WORKOUT

              </div>

              <div class="hero-date">

                ${this._escapeHtml(
                  dateText
                )}

              </div>

            </div>

            <div class="hero-main">

              <div>

                <h1>

                  ${this._escapeHtml(
                    workoutName
                  )}

                </h1>

                <div class="routine">

                  ${this._escapeHtml(
                    routineName
                  )}

                </div>

              </div>

              <div class="duration-badge">

                <span class="duration-icon">
                  ⏱
                </span>

                <span>

                  ${this._escapeHtml(
                    this._formatDuration(
                      duration
                    )
                  )}

                </span>

              </div>

            </div>

          </header>

          <!-- KPIs -->

          <section class="kpi-grid">

            ${this._renderKpi(
              this._formatNumber(
                totals.total_exercises
              ),
              "EJERCICIOS",
              "cyan"
            )}

            ${this._renderKpi(
              this._formatNumber(
                totals.total_sets
              ),
              "SERIES",
              "indigo"
            )}

            ${this._renderKpi(
              this._formatNumber(
                totals.total_repetitions
              ),
              "REPETICIONES",
              "green"
            )}

            ${this._renderKpi(
              this._formatVolume(
                totals.total_volume
              ),
              "VOLUMEN",
              "orange"
            )}

          </section>

          <!-- MUSCLE DISTRIBUTION -->

          ${this._renderMuscleDistribution(
            muscles
          )}

          <!-- RIR -->

          <div class="performance-strip">

            <div class="performance-icon">
              RIR
            </div>

            <div class="performance-copy">

              <span>
                RIR MEDIO
              </span>

              <strong>

                ${this._escapeHtml(
                  this._formatRir(
                    averageRir
                  )
                )}

              </strong>

            </div>

            <div class="performance-description">

              Reserva media de repeticiones
              durante la sesión

            </div>

          </div>

          <!-- EXERCISES -->

          <section class="exercises-section">

            <div class="section-heading">

              <span class="section-kicker">
                PERFORMANCE
              </span>

              <h2>
                Ejercicios
              </h2>

            </div>

            <div class="exercises-list">

              ${exerciseHtml}

            </div>

          </section>

          <!-- FOOTER -->

          <footer class="footer">

            <div class="footer-brand">
              WGER FITNESS
            </div>

            <div class="footer-separator"></div>

            <div>
              TRAINING ANALYTICS
            </div>

          </footer>

        </div>

      </ha-card>
    `;
  }

  getCardSize() {
    return 14;
  }

  getGridOptions() {
    return {
      rows: 14,
      columns: 12,
      min_rows: 8,
      min_columns: 6,
    };
  }
}

customElements.define(
  "wger-last-workout-card",
  WgerLastWorkoutCard
);

window.customCards =
  window.customCards || [];

window.customCards.push({
  type: "wger-last-workout-card",
  name: "Wger Last Workout Card",
  description:
    "Premium Wger card showing the latest completed workout.",
  preview: true,
});