# ChargerSync Lovelace dashboard

A Home Assistant dashboard with three views: **Charging**, **Diagnostics**, and **Management**. Charging and Diagnostics use built-in cards. Management uses the integration's bundled `custom:chargersync-card`, automatically loaded by the integration. No separate frontend download or HACS card installation is required.

![Illustrative dashboard preview](assets/dashboard-preview.png)

The preview is a design illustration with synthetic example readings, not a screenshot from a live Home Assistant instance. Exact spacing and colors follow your Home Assistant theme.

## Layout

The Charging view uses up to three columns on a desktop and stacks sections on smaller screens:

1. **This session:** charging status, energy delivered, duration, apparent power, solar energy, and an eight-hour apparent-power graph.
2. **Charge control:** start/stop, a device-bounded current slider, default and current-session modes, cable controls, and skip-delay action.
3. **Solar charging:** solar enable/disable, solar-share gauge, Eco mix minimum current, threshold setting, and a short explanation of charging modes.

The header uses the original app icon, a charger name, live status text, and connection badges. Offline and fault notices appear when the corresponding state is reported. Charging controls are hidden while the remote connection is offline. Opening the cable tile shows Home Assistant's lock controls; the integration rejects cable operations during charging.

The Diagnostics view contains per-phase voltage/current/solar-current readings, current graphs, connection history, fault information, hardware current limit, and installed firmware.

The Management view provides schedules, timed current limits with weekday selection,
tariffs, history and costs, solar thresholds, reports, charger naming, and logs.
It calls the integration's validated Home Assistant actions. Cloud responses stay
in the card rather than being recorded as large entity attributes. Writes happen
only when you submit a form; opening a view performs reads.

Optional measurement cards are hidden when readings are missing, unknown, or unavailable. Phase L2/L3 cards therefore do not require a three-phase charger. The Eco mix minimum-current control appears only when Eco mix is selected and its value is available. Firmware availability remains on the integration's device page because an offered version is not guaranteed to exist on every device.

Charts use Home Assistant Recorder history, not the cloud's charging-session history API. They need recorded entities and do not reconstruct readings from before the integration was installed. Session measurements and their charts may disappear outside an active session; cloud session history remains available through integration actions. No lifetime energy, vehicle SOC, billing estimate, or active-power measurement is invented.

## 1. Match your entity IDs

The template at `dashboards/chargersync.yaml` uses entity IDs such as `sensor.charger_charging_status`. Home Assistant creates IDs from your device name; renamed entities or naming collisions can produce different IDs.

Find the charging-status sensor under **Settings → Devices & services → ABB ChargerSync → your charger**, or in **Developer tools → States**.

For `sensor.driveway_charging_status`, generate a personalized dashboard using `driveway` as the prefix:

```sh
.venv/bin/python scripts/generate_dashboard.py \
  --entity-prefix driveway \
  --name "Driveway charger" \
  --output work/chargersync-driveway.yaml
```

The generator updates cards, visibility conditions, button targets, and entity references inside the Markdown header. It does not connect to Home Assistant or modify the integration.

If you prefer manual editing, replace every `.charger_` prefix in the template with your actual prefix and replace `CHARGER_DISPLAY_NAME` with your desired heading. Do not change the `abb_chargersync` integration domain.

For individually renamed entities, provide a JSON mapping from the original template ID to the actual ID:

```json
{
  "sensor.charger_session_energy": "sensor.ev_session_energy",
  "number.charger_charging_current_limit": "number.ev_charge_limit"
}
```

```sh
.venv/bin/python scripts/generate_dashboard.py \
  --entity-prefix driveway \
  --name "Driveway charger" \
  --entity-map work/entity-map.json \
  --output work/chargersync-driveway.yaml
```

Check entity IDs before importing. The generator cannot inspect your Home Assistant instance and does not guarantee matches for customized names.

## 2. Install the header icon

Copy `custom_components/abb_chargersync/brand/icon.png` to `www/abb_chargersync/icon.png` inside your Home Assistant configuration directory. Create those directories if needed. This makes the image available at `/local/abb_chargersync/icon.png`, which the dashboard header uses. If you created `www` for the first time, restart Home Assistant.

The local app icon has a white background and remains legible in both light and dark themes. If you do not want the image, remove the `<img ...>` line from the header Markdown; the rest of the dashboard works without it.

## 3. Add the dashboard

1. Open **Settings → Dashboards** and create a new dashboard from scratch.
2. Open the new dashboard and enter edit mode. Take control if prompted.
3. Open the **Raw configuration editor** from the dashboard's three-dot menu.
4. Paste the complete generated YAML, including `title` and `views`, then save.
5. Exit edit mode to check conditional visibility. Home Assistant can show conditional cards while editing even when their runtime conditions are false.

Use a new dashboard: pasting the complete configuration replaces the contents of the dashboard you are editing. To add the design to an existing dashboard, append the three entries under `views` rather than replacing its complete configuration.

For YAML-mode dashboards, put the generated file at `dashboards/chargersync.yaml` under your Home Assistant configuration directory and add:

```yaml
lovelace:
  dashboards:
    chargersync-dashboard:
      mode: yaml
      title: ChargerSync
      icon: mdi:ev-station
      show_in_sidebar: true
      filename: dashboards/chargersync.yaml
```

Merge this into any existing `lovelace` configuration instead of adding a duplicate key. The dashboard key includes a hyphen as required by Home Assistant.

## Multiple chargers and advanced actions

Generate a separate dashboard for each charger or merge the generated views into one dashboard, giving each view a unique `path` and title. The integration does not automatically install or register Lovelace dashboards.

Schedules, tariff editing, exports, and reports use the documented [integration actions](actions.md) through the Management view. Authorization management and Bluetooth features remain outside scope.

## Add the custom card to an existing dashboard

The integration serves and automatically loads `chargersync-card.js` in Home
Assistant. No manual dashboard resource, separate website, or sidebar panel is
required. After installing or upgrading the integration, restart Home Assistant
and refresh the browser.

In the default resource storage mode, the module is also registered in Lovelace's
resource collection so it is loaded before the custom element is created. Its URL
includes the integration version and is updated in place on upgrade. The asset route is registered before the first cloud refresh, including when the
vendor cloud is temporarily unavailable. The card is deliberately not loaded as
an extra frontend module: it must register after HA installs its scoped
custom-element registry.

If you explicitly manage resources in YAML mode, add this entry under your existing
`lovelace.resources` list to ensure the same ordered loading:

```yaml
- url: /abb_chargersync/chargersync-card.js?v=0.2.2
  type: module
```

1. Open your existing dashboard and choose **Edit dashboard → Add card**.
2. Search for **ChargerSync management** in the community cards section.
3. Choose your charger's **Charging status** sensor in the visual configuration form.
4. Optionally choose a title and default tab, then save.

The card can also be added manually:

```yaml
type: custom:chargersync-card
entity: sensor.driveway_charging_status
title: ChargerSync
tab: schedules
```

Available default tabs: `schedules`, `history`, `limits`, `solar`, `tariffs`,
`reports`, `diagnostics`, and `manage`. You can place multiple copies of the card
on different dashboards, with different chargers or default tabs. Opening a tab
only reads its data. Controls use the integration's validated actions.

The optional complete dashboard template above remains available. It is not
registered automatically and does not replace an existing dashboard. To generate
it from the local Compose instance's actual entity IDs, use:

```sh
.venv/bin/python scripts/generate_dashboard.py \
  --from-registry .local/homeassistant/.storage/core.entity_registry \
  --name "Home charger" \
  --output .local/homeassistant/dashboards/chargersync.yaml
```

For multiple chargers, add `--status-entity sensor.driveway_charging_status`.
Registry mode reads entity metadata only; generated configuration stays in the
Git-ignored local directory.

## References

- [Sections view](https://www.home-assistant.io/dashboards/sections/)
- [Tile controls and card features](https://www.home-assistant.io/dashboards/features/)
- [Conditional cards](https://www.home-assistant.io/dashboards/conditional/)
- [Dashboard actions](https://www.home-assistant.io/dashboards/actions/)
