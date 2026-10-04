# FlightWall beginner build plan

**Outcome:** a securely mounted, dim 160×32 WS2812B FlightWall with independently fused panel feeds, verified colors/orientation, and documented electrical tests. The flight-data software is a separate final milestone.

Use the [shopping list](flightwall-shopping-list.md) for purchases and the [wiring guide](beginner-wiring-guide.md) for every connection. The guide specifies five plug-in 5 V / 4 A supplies, four panels per supply, a 3 A main fuse per group, and a 1 A fuse per panel. Keep brightness at 5/255. Do not copy an unrelated LED-wall wiring video or the simulator's direct-USB power connection.

Allow roughly **four to six work sessions / 12–20 hours of hands-on work**, plus shipping, printing, and any new soldering practice. That is a planning allowance, not a deadline. Stop at each pass condition; the next stage assumes the preceding one works.

## Session 1: identify parts and prepare a one-panel order

**Time:** approximately 1–2 hours, excluding delivery.

- Read the wiring guide and identify the expected labels: +5 V, GND, DIN, DOUT, GPIO25.
- Inventory what you own. Reuse the existing Pi/receiver and suitable tools.
- Order one panel, ESP32, approved plug-in 5 V / 4 A supply, rated DC adapter, fuse block, main holder, 1 A/3 A fuses, buffer components, wire/insulation, and essential tools.
- Check panel connector/pixel-order documentation and the supplier's ratings. Plan to return an incompatible part rather than adapting it blindly.
- Install VS Code/PlatformIO and open the [standalone bench project](examples/wiring-test/README.md).

**Pass condition:** actual parts match the shopping specifications; the ESP32 exposes GPIO25; the supply has factory-enclosed mains wiring; the correct connector ratings and pinouts are available.

## Session 2: learn the meter and light one panel

**Time:** approximately 2–4 hours, including soldering practice if needed.

- Practice DC-voltage and unpowered continuity measurements. Keep the meter's amps sockets empty.
- Build group A's jack, 3 A input fuse, distribution block, capacitor, and **one** 1 A panel branch with short 18 AWG copper feeds.
- Assemble the 74AHCT125 signal circuit from the exact pin table; keep it close to the first panel.
- Check polarity, fuse continuity, capacitor polarity, strands, and DIN/DOUT before power-up.
- Build/upload **`panel1`**. Test colors, dim white, pixel 0/1, corners, and border.
- Record voltage under dim white, LED color order, and physical pixel orientation.

**Pass condition:** every LED responds, geometry/colors match, voltage stays within the panel's limits, and the group does not restart or show bad connections. Resolve failures here before scaling up.

## Session 3: make a four-panel module and order the remaining hardware

**Time:** approximately 2–3 hours, excluding delivery.

- After the one-panel test passes, order three matching panels and complete P1–P4, each on its own 1 A branch. P1→P2→P3→P4 data wiring forms the first two columns.
- Remove/insulate positive conductors from the inter-panel links; each link carries **data and ground only**.
- Build/upload **`panel4`**. Verify the walk sequence and 2×2 module's corners/border.
- Measure each panel's input under dim white. Check group current if a suitable DC clamp is available; retain margin below the 3 A main fuse.
- Once the four-panel module passes, buy **sixteen** more panels, four supplies/groups, and remaining mounting materials. This brings the total to twenty panels.

**Pass condition:** four-panel module is stable, separately fused, correctly mapped, and documented. The final order uses the same verified panel specification.

## Session 4: prepare the full structure and five power groups

**Time:** approximately 3–5 hours.

- Measure the actual panels and complete assembly before cutting supports/backer. Trial-fit brackets and spacers first.
- Make groups B–E to the same tested design and label the panel assignments.
- Independently verify the remaining supplies' output polarity and voltage.
- Test each four-panel module using `panel4`, moving the ESP32/buffer only while all relevant power is disconnected. The buffer uses that test module's first-panel fused feed during its isolated test.
- Move the prototype buffer to soldered perfboard or a correctly specified preassembled board; fit its cover and strain relief.
- Mount blocks/supports, secure wires, and keep metal hardware clear of traces and ventilation paths.

**Pass condition:** all five modules pass individually; no terminals or cut positive wire ends are exposed; each panel and supply group is labeled.

## Session 5: connect and commission all twenty panels

**Time:** approximately 2–3 hours, including the supervised run.

- Follow the guide's front/back numbered diagrams and alternate-column 180° rotations. Connect P1→…→P20 in the vertical column snake.
- Connect all group ground buses; keep every group's positive bus separate. Verify before attaching/powering the complete assembly.
- Recheck all fuses, power polarities, short circuits, and cable terminations.
- Build/upload **`panel20`**. Use `walk`, `corners`, `border`, and dim color/white tests.
- Measure voltage at every panel under load, moving clips only with power off. Investigate losses or instability; never increase supply voltage or fuse ratings to compensate.
- Supervise at least 30 minutes of dim-pattern operation. Power down and inspect connections, covers, and strain relief.

**Pass condition:** P1–P20 are in order, all colors/corners/borders are correct, every panel voltage passes, and there are no resets, flickering, fuse failures, or signs of overheated connections.

## Session 6: flight software, mounting, and handover

**Time:** approximately 2–3 hours for current firmware setup/mounting; any remaining local-Pi feature implementation is additional.

- Keep the bench project as a known-good electrical test. Upload production with the physical **`esp32dev`** environment, GPIO25, 10×2 tiles, brightness 5, and the estimated 8 A limiter described in the guide.
- Configure Wi-Fi and `RPI_BASE_URL` using [local firmware setup](../firmware/README.md#local-flight-data). The current firmware polls the Pi's `/v1/flights` endpoint with no cloud fallback. BLE configuration, airline/logo enrichment, and other follow-up work remain in the [local-Pi plan](flightwall-local-plan.md).
- Run the display on the table first. Verify Pi/LAN/receiver operation and the separate offline acceptance checklist. A successful wiring test does not establish software integration or finish remaining software milestones.
- Weigh the complete assembly. Choose appropriate structural mounting, check for utilities before drilling, and have help lifting it.
- Use the approved power strip and ESP32 USB charger for normal use. Keep the disconnect accessible; remove the computer USB connection before using the strip as the shared disconnect.
- Leave a labeled wiring photograph, supply/connector specifications, voltage record, fuse spares, and firmware settings with the wall.

**Pass condition:** securely mounted wall, accessible disconnect, stable chosen flight display, reproducible bench test, and a complete build record. Never leave an unfinished electrical assembly running unattended.

## Fill in this commissioning sheet

Keep an electronic copy or print this section. Supply output values are unloaded; panel values are measured at the panel input under the bench program's **dim white** pattern.

| Group | Supply model / measured output | Main fuse | Panels / measured input voltage | Result / corrections |
| --- | --- | --- | --- | --- |
| A | ___ / ___ V | 3 A | P1 ___ V; P2 ___ V; P3 ___ V; P4 ___ V | ___ |
| B | ___ / ___ V | 3 A | P5 ___ V; P6 ___ V; P7 ___ V; P8 ___ V | ___ |
| C | ___ / ___ V | 3 A | P9 ___ V; P10 ___ V; P11 ___ V; P12 ___ V | ___ |
| D | ___ / ___ V | 3 A | P13 ___ V; P14 ___ V; P15 ___ V; P16 ___ V | ___ |
| E | ___ / ___ V | 3 A | P17 ___ V; P18 ___ V; P19 ___ V; P20 ___ V | ___ |

```text
Builder/date:                         __________________________
Panel make/model + connector pinout:   __________________________
DC-jack/connector documented ratings:  __________________________
ESP32 board + GPIO25 header location:  __________________________
Power-wire gauge + longest feed:       18 AWG / _________________
Panel branch fuses:                    20 × 1 A
Color order + matrix mapping changes:  __________________________
Firmware brightness / power estimate:  5 / 8 A whole-wall limit
Walk / colors / corners / border:      __________________________
30-minute run / post-run inspection:   __________________________
Mounted weight + hanging system:       __________________________
Flight software + acceptance result:   __________________________
Disconnect location / photo location:  __________________________
```

When servicing, unplug all five supplies and ESP32 USB before opening a cover. Check capacitor voltage has fallen near zero. Replace a fuse only with its labeled value after finding the cause. Re-run the bench checks after a panel, connector, supply, mapping, or brightness change.
