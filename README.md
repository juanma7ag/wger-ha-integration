# Wger for Home Assistant

A custom Home Assistant integration for viewing your [wger](https://wger.de/) training data. It creates sensors for workouts, routines, weight, progress, and weekly goals, and includes optional dashboard cards for exploring the results.

> [!NOTE]
> This project is a community integration. It is not part of Home Assistant or wger. The included dashboard cards currently display their text in Spanish; this README and the integration setup flow are available in English.

## What it provides

- Your latest workout, exercise sets, repetitions, load, RIR, and an estimated muscle distribution.
- Workout progress, a comparison with the previous completed session for the same routine day, and a view of planned versus recorded sets.
- Weekly training counts, goal progress, and consistency streaks.
- Today's and the next scheduled workout, plus weight and other summary sensors.
- A workout history card that lets you select one of the 20 most recent completed sessions and loads its detailed records on demand.

The integration reads data from wger. It does not create or change workouts in wger. The regular sensor update interval is **30 minutes**. The history card requests its list and selected workout when you open or use the card.

## Requirements

- Home Assistant **2025.1.0 or newer**, as declared in [`hacs.json`](hacs.json).
- A wger account on [wger.de](https://wger.de/) or a self-hosted wger server that Home Assistant can reach.
- A **permanent wger API token**. In wger, open **User settings → API key** and create/copy a permanent token. This integration sends it using the `Authorization: Token …` header; a JWT access or refresh token is not interchangeable. See [wger's authentication documentation](https://wger.readthedocs.io/en/latest/api/api.html#permanent-token).
- HACS for the HACS installation method. HACS is not required for manual installation.

Use the root URL of your wger server, such as `https://wger.de` or `https://wger.example.com`. **Do not append `/api/v2`**; the integration adds that path itself. Keep your token private. For a self-hosted server, ensure Home Assistant can resolve the hostname and reach its HTTPS endpoint.

## Install with HACS

Until this repository is available in the default HACS catalog, add it as a [custom repository](https://www.hacs.dev/docs/faq/custom_repositories/):

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu and choose **Custom repositories**.
3. Enter `https://github.com/juanma7ag/wger-ha-integration` and select **Integration** as the type.
4. Add the repository, open its HACS page, and download it.
5. **Restart Home Assistant** so it loads the Python integration and its frontend files.
6. Go to **Settings → Devices & services → Add integration**, search for **Wger**, and enter your server URL and permanent API token.

If Wger later appears in the default HACS catalog, you can search for **Wger** there instead of adding a custom repository. HACS downloads the files; you still need to add and configure the integration in Home Assistant. See the [HACS repository guide](https://www.hacs.dev/docs/faq/custom_repositories/).

## Install manually

1. Download or clone this repository.
2. Create `<config>/custom_components/wger/` in your Home Assistant configuration directory.
3. Copy the integration's root Python files, `manifest.json`, `strings.json`, `api/`, `brand/`, `frontend/`, and `translations/` into that `wger` directory. Keep the directory structure intact. The result must include:

   ```text
   <config>/custom_components/wger/
   ├── __init__.py
   ├── manifest.json
   ├── config_flow.py
   ├── coordinator.py
   ├── sensor.py
   ├── api/
   │   ├── __init__.py
   │   └── ...
   ├── brand/
   │   ├── icon.png
   │   └── icon@2x.png
   ├── frontend/
   │   ├── wger-theme.css
   │   └── ...
   └── translations/
       └── ...
   ```

4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**, search for **Wger**, and enter the server URL and permanent API token.

No `configuration.yaml` entry is needed. If the integration does not appear in the Add integration dialog, check the directory name and restart Home Assistant again.

## Configure Wger

| Field | What to enter |
| --- | --- |
| **Server URL** | The base URL of your wger installation, for example `https://wger.de`. |
| **API Token** | A permanent token from wger's **User settings → API key** page. |

After setup, open **Settings → Devices & services → Wger → Configure** to choose a weekly goal from **1 to 21 completed workouts**. The default is **3**. Saving the option reloads the integration.

A session counts toward the weekly goal only when it has finished. The week runs Monday through Sunday in Home Assistant's time zone. New workouts normally appear after the next 30-minute update; reload the integration if you want to fetch them sooner.

## Entities

The integration creates sensors such as:

| Area | Example entities |
| --- | --- |
| Latest training | `sensor.last_workout`, `sensor.last_session`, `sensor.last_workout_duration`, `sensor.days_since_last_workout` |
| Progress and comparison | `sensor.workout_progress`, `sensor.workout_comparison`, `sensor.planned_workout` |
| Weekly goal | `sensor.trainings_this_week`, `sensor.weekly_goal_target`, `sensor.weekly_goal_progress`, `sensor.weekly_goal_remaining`, `binary_sensor.weekly_goal_achieved` |
| Consistency | `sensor.weekly_streak`, `sensor.weekly_best_streak` |
| Other summaries | `sensor.current_weight`, `sensor.weekly_volume`, `sensor.weekly_sets`, `sensor.weekly_repetitions`, and today's/next workout sensors |

Home Assistant may assign a different entity ID, especially if an ID is already in use. Find the actual IDs under **Developer Tools → States** before copying the card examples below. Some sensors expose detailed data in their attributes in addition to their main state.

## Optional dashboard cards

The cards are included in the integration's `frontend/` directory, but **HACS does not register them as dashboard resources automatically**. Register each JavaScript file you want to use as a **JavaScript module** in **Settings → Dashboards → Resources**, then reload the dashboard. The integration serves these files at `/wger/frontend/` after Home Assistant starts. Home Assistant's [resource guide](https://developers.home-assistant.io/docs/frontend/custom-ui/registering-resources/) explains this step.

| Card | Resource URL | Card type | Default data source |
| --- | --- | --- | --- |
| Workout history | `/wger/frontend/wger-workout-history-card.js` | `custom:wger-workout-history-card` | On-demand wger query |
| Last workout | `/wger/frontend/wger-last-workout-card.js` | `custom:wger-last-workout-card` | `sensor.last_workout` |
| Progress | `/wger/frontend/wger-progress-card.js` | `custom:wger-progress-card` | `sensor.workout_progress` |
| Weekly goal | `/wger/frontend/wger-weekly-goal-card.js` | `custom:wger-weekly-goal-card` | `sensor.weekly_goal_progress` |
| Consistency | `/wger/frontend/wger-consistency-card.js` | `custom:wger-consistency-card` | `sensor.weekly_streak` |
| Session comparison | `/wger/frontend/wger-comparison-card.js` | `custom:wger-comparison-card` | `sensor.workout_comparison` |
| Planned vs. recorded | `/wger/frontend/wger-planned-workout-card.js` | `custom:wger-planned-workout-card` | `sensor.planned_workout` |
| KPI summary | `/wger/frontend/wger-kpi-card.js` | `custom:wger-kpi-card` | Several summary sensors |
| Today's workout | `/wger/frontend/wger-workout-card.js` | `custom:wger-workout-card` | Today's workout sensors |

The card type will become available after its resource loads. Registering a card does not add it to a dashboard; add it from the card picker or as a manual card. If you update a card and still see old behavior, refresh the browser and change the resource URL's version query, for example from `?v=1` to `?v=2`.

### Example: workout history

Register `/wger/frontend/wger-workout-history-card.js` and add:

```yaml
type: custom:wger-workout-history-card
title: Workout history
```

The selector shows up to 20 recently completed workouts. Selecting one loads its duration, totals, volume and muscle charts, exercises, and recorded sets. The muscle chart is an estimate based on exercise metadata and recorded volume. Volume is shown in kg × repetitions when all recorded units can be converted; otherwise it is left unavailable.

### Multiple Wger accounts

You can add the integration once per Wger account, including two accounts on the same server. Use each person's own API token. Home Assistant shows the account name in each integration entry. Existing sensor entity IDs are preserved when upgrading; sensors for an additional account receive distinct IDs. Check **Developer Tools → States** for the exact IDs, then set each card's `entity` to the desired account's sensor.

For the workout history card, set `entry_id` to the desired Wger integration entry ID. Without it, the card can choose automatically only when one Wger account is configured:

```yaml
type: custom:wger-workout-history-card
entry_id: YOUR_WGER_CONFIG_ENTRY_ID
```

In a **Sections** dashboard, leave the card height on **Fit to content**. Do not set a fixed `grid_options.rows` value for this card; its detail grows with the number of exercises and sets.

### Example: weekly goal

Register `/wger/frontend/wger-weekly-goal-card.js` and add:

```yaml
type: custom:wger-weekly-goal-card
entity: sensor.weekly_goal_progress
title: Weekly goal
```

### Example: last workout

Register `/wger/frontend/wger-last-workout-card.js` and add:

```yaml
type: custom:wger-last-workout-card
entity: sensor.last_workout
```

### Example: comparison and consistency

After registering their respective JavaScript resources, add either card:

```yaml
type: custom:wger-comparison-card
entity: sensor.workout_comparison
title: Session comparison
```

```yaml
type: custom:wger-consistency-card
entity: sensor.weekly_streak
title: Weekly consistency
```

For the other cards, start with the card type and data source in the table above. Override the `entity` setting if Home Assistant gave your sensor a different ID. More detail about specific calculations is available in the [frontend setup notes](frontend/).

## Updates and troubleshooting

- **Wger does not appear after installation:** Restart Home Assistant and confirm the files are in `<config>/custom_components/wger/`, with `manifest.json` directly inside that directory. Installing through HACS and adding the integration are separate steps.
- **Authentication fails:** Check that you entered a permanent API token, not a JWT refresh token, and that the server URL is the base URL without `/api/v2`. If the token later expires or is revoked, use the integration's reauthentication flow.
- **No data or unavailable sensors:** Check that Home Assistant can reach the wger server, that the account has data, and that the latest refresh succeeded. Look in **Settings → System → Logs** for messages from `custom_components.wger`.
- **A card is missing or says “Custom element doesn't exist”:** Register its exact `.js` URL as a JavaScript module, refresh the browser, and check that `/wger/frontend/<file>.js` loads. The cards are not installed as a separate HACS dashboard package.
- **A card cannot find an entity:** Check **Developer Tools → States** and set the card's `entity` to the ID actually assigned by Home Assistant.
- **Workout history cannot load a detail:** Update both the Python integration and the history card resource, restart Home Assistant, and refresh the browser. If the error remains, check Home Assistant's logs for `wger/workout_detail` or `custom_components.wger` errors.
- **History card overlaps other cards:** In a Sections view, remove any fixed `grid_options.rows` setting and use a current version of the history card resource.

## For repository maintainers

This repository keeps the integration files at its root, so [`hacs.json`](hacs.json) sets `content_in_root` to `true`, which [HACS supports for integration repositories](https://www.hacs.dev/docs/publish/integration/). Adding the repository as a **custom repository** is separate from having it listed in the default HACS catalog. The bundled `brand/icon.png` and `brand/icon@2x.png` show this integration's own house-and-dumbbell icon, inspired by the [wger logo](https://github.com/wger-project/wger/blob/master/wger/core/static/images/logos/logo.png). Home Assistant 2026.3 and newer can load these files directly from the integration's `brand/` folder. Before requesting default catalog inclusion, follow HACS's current [publication requirements](https://github.com/hacs/documentation/blob/main/source/docs/publish/include.md), including a passing brand check.

For bugs and feature requests, use the [GitHub issue tracker](https://github.com/juanma7ag/wger-ha-integration/issues). Include the Home Assistant version, wger version, integration version, affected entity or card, and relevant log lines. Remove tokens and private URLs from logs before sharing them.

## License

This project is licensed under the [MIT License](LICENSE).
