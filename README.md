# Arctic Spa — Home Assistant Custom Integration

Home Assistant integration for Arctic Spas hot tubs running firmware 3.1.x
or later (WebSocket protocol on the spa controller's port 8765).

This is a fork of [`riversen/arctic_spa`](https://github.com/riversen/arctic_spa)
rewritten for the post-firmware-update protocol. The upstream's
BlueFalls/Yoctub protobuf-over-TCP transport was removed by Arctic Spas in
firmware 3.1.x and replaced with a JSON-over-WebSocket transport — this fork
talks the new protocol and substantially extends the entity coverage.

---

## Requirements

- Home Assistant 2024.4+ (uses `Platform.DATE`)
- Arctic Spas tub running firmware **YOC 3.1.x or later**
- Spa controller reachable on your LAN (default port 8765, no auth)
- Python `websockets >= 11.0` (installed automatically)

---

## Installation

### Via HACS (recommended)

1. HACS → **Integrations** → top-right ⋮ → **Custom repositories**
2. Add `rgerrans/arctic_spa` as type **Integration** → click Add
3. Search for "Arctic Spa" in HACS → **Download** the latest release
4. Settings → System → **Restart Home Assistant**
5. Settings → Devices & Services → **Add Integration** → search "Arctic Spa"
6. Fill in the three fields:
   - **Host** — your spa's IP (e.g. `192.168.100.35`). DHCP-reserve it for stability.
   - **Temperature unit** — F or C; affects sensor unit only, not the spa itself.
   - **Entity name string root** — literal entity_id prefix for every entity
     created. Default `arctic_spa` → entity_ids like `sensor.arctic_spa_*`.
     Pick `hot_tub` → entity_ids like `sensor.hot_tub_*`. Use snake_case.
     Cannot be changed later without deleting and re-adding the integration.

---

## Entity Inventory

The integration registers ~95 entities across 9 platforms. Many are disabled
by default (per-pump-running indicators, per-electrode wear, diagnostics) and
can be enabled per-entity if you want them. Entities are also auto-gated by
the spa's installed-hardware config flags (`cfg_pump`, `cfg_blower`, `cfg_sb`,
`cfg_fg`, `cfg_sds`, `cfg_yess`, `cfg_onzen`, `cfg_lights`) so accessories
your spa doesn't have stay disabled.

Assume entity IDs start with `<platform>.arctic_spa_*` (or your chosen
device name prefix). All entity-name strings below are the **display
names** you'll see in the HA UI; the entity_id slug is shown when it
differs meaningfully.

### Climate (1)

| Entity | Description |
|---|---|
| **Arctic Spa** (climate) | Proper thermostat. Current water temp, settable target temp, HVAC action (heating/idle), dynamic min/max bounds from the spa's reported `setTSPmin`/`setTSPmax`. Always in HEAT mode (spas don't cool). |

### Sensor (40)

#### Temperatures
| Entity | Description |
|---|---|
| Water Temperature | Live water temp from `live.STemp` |
| Target Temperature | Setpoint readback from `sett.TSP` (writable via climate or `number.set_temperature`) |
| Heater Temperature | `live.HTemp` — heater coil temp |
| SpaBoy Cell Temperature | `live.sbTemp` — chlorinator cell temperature |

#### Spa state
| Entity | Description |
|---|---|
| Heater 1 Status | `live.H1` → "Idle" / "Warming Up" / "Heating" / "Cooling Down" |
| Heater 2 Status | `live.H2` → same labels for the secondary heater |
| Filter Status | `live.Filter` → "Idle" / "Filtering" / "Purging" / "Suspended" / "Over Temperature" / "Resuming" / "Boost" / "Sanitizing" |
| Error | Comma-separated list of active ERR codes with friendly labels; "No Error" if clean. `extra_state_attributes.active_codes` carries the integer list. |
| Alarm | Comma-separated list of active alarm-worthy STAT codes; "No Alarm" if clean. PCBID identifiers and TARGET TEMPERATURE REACHED are filtered out to `informational_codes` attribute. |
| Current Draw | `live.Current` — spa pack current (raw integer; units unverified) |

#### Chemistry (SpaBoy chlorinator)
| Entity | Description |
|---|---|
| pH Level | `live.sbpH / 100` — actual pH reading (e.g. 7.59) |
| ORP (Chlorine) | `live.sbORP` — millivolts |
| pH Status | Firmware band (`sbpHind` 0-4) → "Very Low" / "Low" / "OK" / "High" / "Very High". Raw indicator + pH in attributes. |
| ORP Status | Same banding from `sbORPind` for chlorine ppm range |
| SmartPH State | `live.phSM` → 10 named states (Idle / Check Conditions / Priming / Dosing / etc.) |
| SpaBoy Activity | `live.sbProducing` → "Producing" or "Idle" — matches Customer Portal sanitation tooltip |
| SpaBoy Cell Life Remaining | **Battery class** — `live.sbWear` (% capacity remaining; firmware decreases as the cell ages). Icon auto-changes full → 90 → 80 → ... → outline. |
| SpaBoy Status Code | `live.sbStat` — raw firmware status integer |
| SpaBoy State Machine | `live.sbSM` — raw internal state code |

#### SpaBoy diagnostics (disabled by default)
| Entity | Description |
|---|---|
| SpaBoy Electrode 1 Life Remaining | Per-plate battery (sbWearE1) |
| SpaBoy Electrode 2 Life Remaining | Per-plate battery (sbWearE2) |
| SpaBoy Voltage In | `live.sbVin` — supply voltage (raw, likely mV) |
| SpaBoy Voltage Out | `live.sbVout` — cell voltage (raw) |
| SpaBoy Electrode 1 Current | `live.sbI1` (raw amps) |
| SpaBoy Electrode 2 Current | `live.sbI2` (raw amps) |
| SpaBoy Electrode 1 Positive | `live.sbE1p` (raw — likely positive half-cycle measurement) |
| SpaBoy Electrode 1 Negative | `live.sbE1n` |
| SpaBoy Electrode 2 Positive | `live.sbE2p` |
| SpaBoy Electrode 2 Negative | `live.sbE2n` |

#### Filter cartridges
| Entity | Description |
|---|---|
| Filter 1 Life Remaining | **Battery class** — HA-computed from `date.filter_1_installed_date` + selected lifespan |
| Filter 2 Life Remaining | Same for slot 2 |
| Filter 1 Tag ID | RFID hex of installed cartridge (e.g. `4C008B56C0`) — diagnostic, off by default |
| Filter 2 Tag ID | Same for slot 2 |
| Filter Run Hours Per Day | Computed: `FF × FD` (filter frequency × duration per cycle) |

#### Energy
| Entity | Description |
|---|---|
| Power | Estimated W from current pump/heater/blower state. Heuristic; not measured. |
| Energy | Cumulative kWh integrated from Power. TOTAL_INCREASING; restored across restarts. |

#### Diagnostics (disabled by default)
| Entity | Description |
|---|---|
| Spa Serial Number | `sett.SPASN` |
| Spa Firmware (YOC) | `sett.YOCFWVer` — main controller firmware |
| Spa Firmware (LPC) | `sett.LPCFWVer` — low-power controller firmware |
| Spa Firmware (SpaBoy) | `sett.SBFWVer` — chlorinator firmware |

### Binary Sensor (24)

#### Activity / state
| Entity | Description |
|---|---|
| Connected | WS connection to the spa is alive |
| Heater Active | `H1`/`H2` is WARMUP or HEATING |
| Filter Boost Active | `filter_status == BOOST` |
| Onzen Active | `live.On` |
| Economy Mode | `live.Econ` |
| Ozone Active | `live.Oz` |
| Fan Active | `live.Fan` |
| Fogger Active | `live.Fogger` |
| Bubbles (SDS) Active | `live.SDS` |
| YESS Active | `live.Yess` |
| All On | `live.AllOn` |
| SpaBoy Producing | `live.sbProducing` (same data as the text sensor) |
| SpaBoy Boost Active | `live.sbBoost` |
| Filter 1 Installed | True if `sett.TAG1` has an RFID value |
| Filter 2 Installed | Same for slot 2 |
| Error | At least one active labeled ERR code |
| Alarm | At least one active alarm-worthy STAT code |

#### Per-pump / per-blower running (gated by `cfg_pump`/`cfg_blower`)
| Entity | Description |
|---|---|
| Pump 1..5 Running | True if pump speed > OFF; entity disabled if pump not installed |
| Blower 1..2 Running | Same for blowers |

### Switch (14)

| Entity | Description |
|---|---|
| Cabinet Lights | Toggle the cabin lights on/off |
| Filter Boost | One-shot extra filter cycle |
| SpaBoy Boost | Chlorinator overproduction mode |
| Onzen | Toggle Onzen system |
| Bubbles (SDS) | Toggle SDS bubbles |
| YESS | Toggle YESS |
| Fogger | Toggle fogger |
| Stop Filter Above Setpoint+3° | When ON, filter stops if water is 3°F above setpoint (`FS`/`setFS`) |
| Pump 2..5 | On/off for each single-speed jet pump (gated by `cfg_pump`) |
| Blower 1..2 | On/off for each blower (gated by `cfg_blower`) |

### Select (6)

| Entity | Description |
|---|---|
| Pump 1 Speed | Off / Low / High — Pump 1 is the 3-speed circulation pump |
| Blower 1 Speed | Off / Low / High (if your model has variable-speed blowers) |
| Blower 2 Speed | same |
| Lights Pattern | Solid / Fade In / Blinking / Spectrum — RDT light pattern from `setRDTpattern` |
| Chlorine Level | Low / Medium / High — Customer Portal's 3 ORP-band presets (also resets `SBHr=0`) |
| Filter Replacement Frequency | 90 days / 180 days / 365 days — drives the filter life-remaining calculation |

### Light (1)

| Entity | Description |
|---|---|
| Cabinet Lights (light) | RGB color picker + brightness for `RDT_*` LEDs. Pairs with the Cabinet Lights switch (the switch toggles power; the light entity controls color when on). |

### Number (5)

| Entity | Description |
|---|---|
| Filter Frequency | Filter cycles per day (`setFF`) |
| Filter Duration | Filter cycle length in hours (`setFD`) |
| Chlorine Target (ORP) | Manual ORP setpoint (sets `SBORPhi/lo`). Use this for custom values outside Low/Medium/High presets. |
| pH Target | Manual pH setpoint (sets `SBpHhi/lo` × 100). May be empty if your firmware doesn't expose pH bands. |
| SpaBoy Hours / Day | Chlorinator duty cycle hours (`setSBHrs`); typically auto-managed by chlorine level select |

### Button (4)

| Entity | Description |
|---|---|
| pH Boost | One-shot pH correction (`PHboost`) |
| Ozone Peak 1 | Toggle ozone peak schedule 1 |
| Ozone Peak 2 | Toggle ozone peak schedule 2 |
| System Reset | `Reset: all` — full spa controller reset (restart-class button) |

### Date (2)

| Entity | Description |
|---|---|
| Filter 1 Installed Date | Writable date entity. Auto-set on first integration start (if tag present) and on cartridge swap (TAG ID change). Override manually any time via the UI. |
| Filter 2 Installed Date | Same for slot 2 |

---

## Notes

### Spa firmware doesn't expose filter wear
Filter cartridges are only tracked by RFID tag presence in the firmware
(the portal just shows "Good" or "No Filter Present"). The Filter Life
Remaining sensor is **HA-computed** from the installed date + your selected
lifespan (90/180/365 days). When a TAG ID change is detected (you swap a
cartridge), the install date auto-resets to today.

### Energy is estimated, not measured
Arctic Spa controllers don't include a true power meter. The Power sensor
estimates wattage from current pump/heater/blower state using hardcoded
constants. Energy is integrated from this estimate. Use for trends, not
billing.

### Some values are raw
The SpaBoy electrical diagnostics (Vin, Vout, electrode currents) are
exposed as raw firmware integers because the units aren't documented and
the Customer Portal doesn't display them for comparison. They're useful
for relative monitoring (changes over time) even without absolute units.

### STAT codes not on `error` topic
Critical bugfix from v2.0.7: status codes (`STAT0`-`STAT63`) arrive on the
WS `status` topic, separate from the `error` topic. Earlier versions
mistakenly read only the `error` topic, missing all status alarms. PCBID
identifiers and "Target Temperature Reached" are filtered out of the
alarm sensor (they're operational signals, not problems).

---

## Credits

- Original integration: [riversen/arctic_spa](https://github.com/riversen/arctic_spa) (protobuf protocol)
- This fork: WebSocket protocol rewrite + extensive entity expansion for
  Arctic Spas firmware 3.1.x

---

## Issues

Report at [github.com/rgerrans/arctic_spa/issues](https://github.com/rgerrans/arctic_spa/issues).
