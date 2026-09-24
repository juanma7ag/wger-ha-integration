class WgerWorkoutCard extends HTMLElement {
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
      workout_entity: "sensor.today_s_workout",
      exercises_entity: "sensor.today_s_exercises",
      sets_entity: "sensor.today_s_sets",
      repetitions_entity: "sensor.today_s_repetitions",
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

    const themeLink = document.createElement("link");

    themeLink.rel = "stylesheet";
    themeLink.href =
      "/wger/frontend/wger-theme.css";

    const cardLink = document.createElement("link");

    cardLink.rel = "stylesheet";
    cardLink.href =
      "/wger/frontend/wger-workout-card.css";

    this.shadowRoot.appendChild(themeLink);
    this.shadowRoot.appendChild(cardLink);

    this._cssLoaded = true;
  }

  _getState(entityId) {
    if (!this._hass || !entityId) {
      return null;
    }

    return this._hass.states[entityId] || null;
  }

  _escapeHtml(value) {
    if (value === null || value === undefined) {
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

  _formatNumber(value, decimals = 0) {
    const number = this._number(value);

    return number.toLocaleString("es-ES", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  _formatDate(dateString) {
    if (!dateString) {
      return "";
    }

    const date = new Date(
      `${dateString}T12:00:00`
    );

    if (Number.isNaN(date.getTime())) {
      return dateString;
    }

    return date
      .toLocaleDateString("es-ES", {
        weekday: "short",
        day: "2-digit",
        month: "short",
        year: "numeric",
      })
      .replace(/\./g, "")
      .toUpperCase();
  }

  _render() {
    if (!this._hass) {
      return;
    }

    const workout = this._getState(
      this._config.workout_entity
    );

    if (!workout) {
      this.shadowRoot.innerHTML = `
        <link
          rel="stylesheet"
          href="/wger/frontend/wger-theme.css"
        >

        <link
          rel="stylesheet"
          href="/wger/frontend/wger-workout-card.css"
        >

        <div class="error">
          No se ha encontrado el sensor
          del entrenamiento.
        </div>
      `;

      return;
    }

    const attributes =
      workout.attributes || {};

    const exercises =
      Array.isArray(attributes.exercises)
        ? attributes.exercises
        : [];

    const exerciseCount =
      this._number(
        this._getState(
          this._config.exercises_entity
        )?.state,
        exercises.length
      );

    const totalSets =
      this._number(
        this._getState(
          this._config.sets_entity
        )?.state,
        attributes.total_sets || 0
      );

    const totalRepetitions =
      this._number(
        this._getState(
          this._config.repetitions_entity
        )?.state,
        attributes.total_repetitions || 0
      );

    const date =
      this._formatDate(
        attributes.date
      );

    const workoutName =
      workout.state ||
      attributes.description ||
      "Entrenamiento";

    this.shadowRoot.innerHTML = `
      <link
        rel="stylesheet"
        href="/wger/frontend/wger-theme.css"
      >

      <link
        rel="stylesheet"
        href="/wger/frontend/wger-workout-card.css"
      >

      <article class="wger-card">

        <!-- HEADER -->

        <header class="card-header">

          <div class="header-main">

            <div class="eyebrow">
              ${this._escapeHtml(date)}
            </div>

            <h1>
              ${this._escapeHtml(
                workoutName
              )}
            </h1>

          </div>

          <div class="header-badge">
            WGER
            <span>WORKOUT</span>
          </div>

        </header>


        <!-- KPI -->

        <section class="stats-grid">

          ${this._renderStat(
            "01",
            exerciseCount,
            "EJERCICIOS"
          )}

          ${this._renderStat(
            "02",
            totalSets,
            "SERIES"
          )}

          ${this._renderStat(
            "03",
            totalRepetitions,
            "REPETICIONES"
          )}

        </section>


        <!-- EXERCISES -->

        <section class="exercises-section">

          <div class="exercise-section-header">

            <div>

              <span class="section-kicker">
                SESIÓN
              </span>

              <h2>
                Ejercicios
              </h2>

            </div>

            <div class="exercise-count">

              ${this._formatNumber(
                exerciseCount
              )}

              ejercicios

            </div>

          </div>


          <div class="exercise-list">

            ${exercises
              .map(
                (exercise, index) =>
                  this._renderExercise(
                    exercise,
                    index
                  )
              )
              .join("")}

          </div>

        </section>


        <!-- FOOTER -->

        <footer class="card-footer">

          <span>
            WGER FITNESS
          </span>

          <span>
            TRAINING SESSION
          </span>

        </footer>

      </article>
    `;
  }

  _renderStat(
    number,
    value,
    label
  ) {
    return `
      <div class="stat-card">

        <div class="stat-number">
          ${number}
        </div>

        <div class="stat-content">

          <strong>
            ${this._escapeHtml(value)}
          </strong>

          <span>
            ${this._escapeHtml(label)}
          </span>

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
      "Ejercicio";

    const image =
      exercise.image ||
      exercise.thumbnail_medium ||
      exercise.thumbnail_small ||
      "";

    const muscleTags = Array.isArray(
      exercise.muscle_names
    )
      ? exercise.muscle_names
      : [];

    const secondaryMuscleTags =
      Array.isArray(
        exercise.muscle_names_secondary
      )
        ? exercise.muscle_names_secondary
        : [];

    const sets = Array.isArray(
      exercise.sets
    )
      ? exercise.sets
      : [];

    const muscleTagsCombined = [
      ...muscleTags,
      ...secondaryMuscleTags,
    ]
      .filter(Boolean)
      .filter(
        (value, position, array) =>
          array.indexOf(value) === position
      )
      .slice(0, 4);

    return `
      <article class="exercise-card">


        <!-- EXERCISE HEADER -->

        <div class="exercise-top">

          <div class="exercise-index">

            ${String(
              index + 1
            ).padStart(2, "0")}

          </div>


          <div class="exercise-title">

            <h3>

              ${this._escapeHtml(
                name
              )}

            </h3>


            <div class="exercise-tags">

              ${muscleTagsCombined
                .map(
                  (muscle) => `
                    <span
                      class="tag muscle-tag"
                    >
                      ${this._escapeHtml(
                        muscle
                      )}
                    </span>
                  `
                )
                .join("")}

            </div>

          </div>

        </div>


        <!-- EXERCISE CONTENT -->

        <div class="exercise-body">


          ${
            image
              ? `
                <div
                  class="exercise-image"
                >

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
                <div
                  class="
                    exercise-image
                    image-placeholder
                  "
                >

                  <span>
                    ${String(
                      index + 1
                    ).padStart(
                      2,
                      "0"
                    )}
                  </span>

                </div>
              `
          }


          <!-- PLANNING -->

          <div
            class="planning-container"
          >

            <div
              class="planning-header"
            >

              <span
                class="
                  planning-series
                "
              >
                SERIES
              </span>

              <span
                class="
                  planning-reps
                "
              >
                REPS
              </span>

            </div>


            ${
              sets.length > 0
                ? sets
                    .map(
                      (workoutSet) => `
                        <div
                          class="
                            planning-row
                          "
                        >

                          <span
                            class="
                              planning-series
                            "
                          >

                            ${this._escapeHtml(
                              workoutSet.sets ??
                                "—"
                            )}

                          </span>


                          <span
                            class="
                              planning-reps
                            "
                          >

                            ${this._escapeHtml(
                              workoutSet.repetitions ??
                                "—"
                            )}

                          </span>

                        </div>
                      `
                    )
                    .join("")
                : `
                  <div
                    class="
                      planning-empty
                    "
                  >
                    Sin series configuradas
                  </div>
                `
            }

          </div>

        </div>


        ${
          exercise.notes
            ? `
              <div
                class="
                  exercise-notes
                "
              >

                ${this._escapeHtml(
                  exercise.notes
                )}

              </div>
            `
            : ""
        }


      </article>
    `;
  }

  getCardSize() {
    return 12;
  }

  getGridOptions() {
    return {
      rows: 12,
      columns: 12,
      min_rows: 6,
      min_columns: 6,
    };
  }
}


if (
  !customElements.get(
    "wger-workout-card"
  )
) {
  customElements.define(
    "wger-workout-card",
    WgerWorkoutCard
  );
}


window.customCards =
  window.customCards || [];


window.customCards.push({
  type: "wger-workout-card",
  name: "Wger Workout Card",
  description:
    "Professional fitness workout planning card for Wger.",
  preview: true,
});