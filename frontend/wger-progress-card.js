class WgerProgressCard extends HTMLElement {
  constructor() {
    super();

    this.attachShadow({ mode: "open" });

    this._config = {
      entity: "sensor.workout_progress",
    };

    this._data = [];
    this._tooltip = null;
    this._cssLoaded = false;
  }

  static getStubConfig() {
    return {
      entity: "sensor.workout_progress",
    };
  }

  setConfig(config) {
    this._config = {
      entity: "sensor.workout_progress",
      ...config,
    };

    this._loadStyles();

    if (this._hass) {
      this._render();
    }
  }

  set hass(hass) {
    this._hass = hass;

    if (!this._config) {
      return;
    }

    this._render();
  }

  getCardSize() {
    return 9;
  }

getGridOptions() {
  return {
    rows: 10,
    columns: 12,
    min_rows: 5,
    min_columns: 6,
  };
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
      "/wger/frontend/wger-progress-card.css";

    this.shadowRoot.appendChild(
      themeLink
    );

    this.shadowRoot.appendChild(
      cardLink
    );

    this._cssLoaded = true;
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
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  _formatNumber(
    value,
    decimals = 0
  ) {
    if (
      value === null ||
      value === undefined ||
      Number.isNaN(Number(value))
    ) {
      return "—";
    }

    return Number(value).toLocaleString(
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
    if (
      value === null ||
      value === undefined ||
      Number.isNaN(Number(value))
    ) {
      return "—";
    }

    return `${this._formatNumber(
      value
    )} kg`;
  }

  _formatRir(value) {
    if (
      value === null ||
      value === undefined ||
      Number.isNaN(Number(value))
    ) {
      return "—";
    }

    return Number(value)
      .toLocaleString(
        "es-ES",
        {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }
      );
  }

  _formatDate(value) {
    if (!value) {
      return "—";
    }

    const date = new Date(
      `${value}T12:00:00`
    );

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
      }
    );
  }

  _getProgress() {
    const entity =
      this._getEntity();

    if (!entity) {
      return [];
    }

    const attributes =
      entity.attributes || {};

    const workouts =
      attributes.workouts || [];

    if (
      !Array.isArray(workouts)
    ) {
      return [];
    }

    return workouts
      .filter(
        (workout) =>
          workout &&
          workout.date
      )
      .sort(
        (a, b) =>
          new Date(a.date) -
          new Date(b.date)
      );
  }

  _getMaxVolume(data) {
    if (!data.length) {
      return 0;
    }

    return Math.max(
      ...data.map(
        (item) =>
          Number(
            item.total_volume
          ) || 0
      )
    );
  }

  _buildChart(data) {
    const width = 760;
    const height = 210;

    const padding = {
      top: 24,
      right: 24,
      bottom: 42,
      left: 58,
    };

    const chartWidth =
      width -
      padding.left -
      padding.right;

    const chartHeight =
      height -
      padding.top -
      padding.bottom;

    const maxVolume =
      this._getMaxVolume(data);

    const safeMax =
      maxVolume > 0
        ? maxVolume * 1.15
        : 100;

    const points = data.map(
      (item, index) => {
        const volume =
          Number(
            item.total_volume
          ) || 0;

        const x =
          data.length === 1
            ? padding.left +
              chartWidth / 2
            : padding.left +
              (
                index /
                (data.length - 1)
              ) *
                chartWidth;

        const y =
          padding.top +
          chartHeight -
          (
            volume /
            safeMax
          ) *
            chartHeight;

        return {
          ...item,
          x,
          y,
          volume,
        };
      }
    );

    const path = points
      .map(
        (point, index) =>
          `${
            index === 0
              ? "M"
              : "L"
          } ${point.x} ${point.y}`
      )
      .join(" ");

    const areaPath =
      points.length > 1
        ? `${path} L ${
            points[
              points.length - 1
            ].x
          } ${
            padding.top +
            chartHeight
          } L ${
            points[0].x
          } ${
            padding.top +
            chartHeight
          } Z`
        : "";

    const gridLines = [
      0,
      0.25,
      0.5,
      0.75,
      1,
    ]
      .map((ratio) => {
        const y =
          padding.top +
          chartHeight -
          ratio * chartHeight;

        const value =
          safeMax * ratio;

        return `
          <line
            x1="${padding.left}"
            y1="${y}"
            x2="${
              width -
              padding.right
            }"
            y2="${y}"
            class="grid-line"
          />

          <text
            x="${
              padding.left - 12
            }"
            y="${y + 4}"
            text-anchor="end"
            class="axis-label"
          >
            ${this._formatNumber(
              value
            )}
          </text>
        `;
      })
      .join("");

    const labels = points
      .map(
        (point) => `
          <text
            x="${point.x}"
            y="${height - 14}"
            text-anchor="middle"
            class="date-label"
          >
            ${this._formatDate(
              point.date
            )}
          </text>
        `
      )
      .join("");

    const circles = points
      .map(
        (point, index) => `
          <g
            class="chart-point"
            data-index="${index}"
          >
            <circle
              cx="${point.x}"
              cy="${point.y}"
              r="6"
              class="point-outer"
            />

            <circle
              cx="${point.x}"
              cy="${point.y}"
              r="3"
              class="point-inner"
            />
          </g>
        `
      )
      .join("");

    return `
      <svg
        class="chart"
        viewBox="0 0 ${width} ${height}"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient
            id="volumeGradient"
            x1="0"
            y1="0"
            x2="0"
            y2="1"
          >
            <stop
              offset="0%"
              class="gradient-start"
            />

            <stop
              offset="100%"
              class="gradient-end"
            />
          </linearGradient>
        </defs>

        ${gridLines}

        ${
          areaPath
            ? `
              <path
                d="${areaPath}"
                class="area"
              />
            `
            : ""
        }

        <path
          d="${path}"
          class="line"
        />

        ${circles}

        ${labels}
      </svg>
    `;
  }

  _renderKpi(
    label,
    value,
    icon
  ) {
    return `
      <div class="kpi">

        <div class="kpi-icon">
          ${icon}
        </div>

        <div class="kpi-content">

          <div class="kpi-label">
            ${label}
          </div>

          <div class="kpi-value">
            ${value}
          </div>

        </div>

      </div>
    `;
  }

  _render() {
    const entity =
      this._getEntity();

    /*
     * IMPORTANT:
     *
     * Every render replaces shadowRoot.innerHTML.
     * Therefore the stylesheet links must also exist
     * inside the HTML generated on every render.
     */

    const styleLinks = `
      <link
        rel="stylesheet"
        href="/wger/frontend/wger-theme.css"
      />

      <link
        rel="stylesheet"
        href="/wger/frontend/wger-progress-card.css"
      />
    `;

    if (!entity) {
      this.shadowRoot.innerHTML = `
        ${styleLinks}

        <article class="card">

          <div class="empty">

            <div class="empty-icon">
              ⚠️
            </div>

            <div>

              <strong>
                Workout Progress
              </strong>

              <div>
                Entidad no encontrada:
                ${this._escapeHtml(
                  this._config.entity
                )}
              </div>

            </div>

          </div>

        </article>
      `;

      return;
    }

    const data =
      this._getProgress();

    const totalWorkouts =
      data.length;

    const totalSets =
      data.reduce(
        (sum, item) =>
          sum +
          (
            Number(
              item.total_sets
            ) || 0
          ),
        0
      );

    const totalRepetitions =
      data.reduce(
        (sum, item) =>
          sum +
          (
            Number(
              item.total_repetitions
            ) || 0
          ),
        0
      );

    const averageRir =
      data.length
        ? data.reduce(
            (sum, item) =>
              sum +
              (
                Number(
                  item.average_rir
                ) || 0
              ),
            0
          ) / data.length
        : null;

    const latest =
      data[
        data.length - 1
      ];

    const latestVolume =
      latest
        ? Number(
            latest.total_volume
          ) || 0
        : 0;

    const title =
      latest?.workout_name ||
      "Training Progress";

    this.shadowRoot.innerHTML = `
      ${styleLinks}

      <article class="card">

        <div class="card-content">

          <div class="hero">

            <div class="hero-icon">
              <span>↗</span>
            </div>

            <div class="hero-content">

              <div class="eyebrow">
                TRAINING ANALYTICS
              </div>

              <div class="title">
                Progreso de entrenamiento
              </div>

              <div class="subtitle">
                Evolución del volumen por sesión
              </div>

            </div>

            <div class="hero-value">

              <div class="hero-value-number">
                ${this._formatVolume(
                  latestVolume
                )}
              </div>

              <div class="hero-value-label">
                última sesión
              </div>

            </div>

          </div>

          <div class="kpi-grid">

            ${this._renderKpi(
              "Entrenamientos",
              this._formatNumber(
                totalWorkouts
              ),
              "🏋️"
            )}

            ${this._renderKpi(
              "Series",
              this._formatNumber(
                totalSets
              ),
              "▤"
            )}

            ${this._renderKpi(
              "Repeticiones",
              this._formatNumber(
                totalRepetitions
              ),
              "↻"
            )}

            ${this._renderKpi(
              "RIR medio",
              this._formatRir(
                averageRir
              ),
              "◎"
            )}

          </div>

          <div class="section-header">

            <div>

              <div class="section-title">
                Volumen
              </div>

              <div class="section-subtitle">
                Carga total por entrenamiento
              </div>

            </div>

            <div class="trend-badge">
              ${totalWorkouts}
              sesiones
            </div>

          </div>

          ${
            data.length
              ? `
                <div
                  class="chart-container"
                  id="chart-container"
                >

                  ${this._buildChart(
                    data
                  )}

                  <div
                    class="tooltip"
                    id="tooltip"
                  ></div>

                </div>
              `
              : `
                <div class="empty-chart">

                  <div class="empty-chart-icon">
                    📈
                  </div>

                  <div>

                    <strong>
                      Sin histórico suficiente
                    </strong>

                    <span>
                      Completa entrenamientos para
                      empezar a ver tu evolución.
                    </span>

                  </div>

                </div>
              `
          }

          ${
            latest
              ? `
                <div class="latest-workout">

                  <div class="latest-icon">
                    ✓
                  </div>

                  <div class="latest-content">

                    <div class="latest-label">
                      ÚLTIMO ENTRENAMIENTO
                    </div>

                    <div class="latest-name">
                      ${this._escapeHtml(
                        title
                      )}
                    </div>

                    <div class="latest-meta">

                      ${this._formatDate(
                        latest.date
                      )}

                      ·

                      ${this._formatNumber(
                        latest.total_sets
                      )}

                      series

                      ·

                      ${this._formatNumber(
                        latest.total_repetitions
                      )}

                      reps

                    </div>

                  </div>

                  <div class="latest-volume">

                    <span>
                      ${this._formatNumber(
                        latest.total_volume
                      )}
                    </span>

                    <small>
                      kg
                    </small>

                  </div>

                </div>
              `
              : ""
          }

          <div class="footer">
            Datos proporcionados por Wger
          </div>

        </div>

      </article>
    `;

    this._bindChartEvents(
      data
    );
  }

  _bindChartEvents(data) {
    const points =
      this.shadowRoot.querySelectorAll(
        ".chart-point"
      );

    const tooltip =
      this.shadowRoot.querySelector(
        "#tooltip"
      );

    const container =
      this.shadowRoot.querySelector(
        "#chart-container"
      );

    if (
      !points.length ||
      !tooltip ||
      !container
    ) {
      return;
    }

    points.forEach(
      (point) => {
        const index =
          Number(
            point.dataset.index
          );

        const workout =
          data[index];

        const showTooltip =
          () => {
            const pointInner =
              point.querySelector(
                ".point-inner"
              );

            if (!pointInner) {
              return;
            }

            const rect =
              pointInner.getBoundingClientRect();

            const containerRect =
              container.getBoundingClientRect();

            const x =
              rect.left -
              containerRect.left +
              rect.width / 2;

            const y =
              rect.top -
              containerRect.top;

            tooltip.innerHTML = `
              <div class="tooltip-date">
                ${this._formatDate(
                  workout.date
                )}
              </div>

              <div class="tooltip-title">
                ${this._escapeHtml(
                  workout.workout_name ||
                  "Entrenamiento"
                )}
              </div>

              <div class="tooltip-volume">

                ${this._formatNumber(
                  workout.total_volume
                )}

                <span>
                  kg
                </span>

              </div>

              <div class="tooltip-stats">

                <span>
                  ${this._formatNumber(
                    workout.total_sets
                  )}
                  series
                </span>

                <span>
                  ${this._formatNumber(
                    workout.total_repetitions
                  )}
                  reps
                </span>

                <span>
                  RIR
                  ${this._formatRir(
                    workout.average_rir
                  )}
                </span>

              </div>
            `;

            tooltip.style.left =
              `${x}px`;

            tooltip.style.top =
              `${Math.max(
                y - 12,
                10
              )}px`;

            tooltip.classList.add(
              "visible"
            );
          };

        const hideTooltip =
          () => {
            tooltip.classList.remove(
              "visible"
            );
          };

        point.addEventListener(
          "mouseenter",
          showTooltip
        );

        point.addEventListener(
          "mouseleave",
          hideTooltip
        );

        point.addEventListener(
          "click",
          () => {
            if (
              tooltip.classList.contains(
                "visible"
              )
            ) {
              hideTooltip();
            } else {
              showTooltip();
            }
          }
        );
      }
    );
  }
}

customElements.define(
  "wger-progress-card",
  WgerProgressCard
);

window.customCards =
  window.customCards || [];

window.customCards.push({
  type: "wger-progress-card",
  name: "Wger Training Progress",
  description:
    "Visual training progress and volume evolution",
  preview: true,
});