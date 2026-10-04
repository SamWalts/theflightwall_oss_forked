# Wire your FlightWall: a beginner's guide

This guide covers the hardware in this repository: **twenty 5 V, 16×16 WS2812B panels, one classic ESP32, and a 10-panel-wide × 2-panel-high wall**. That is 160×32 pixels, or 5,120 LEDs. It takes you from testing one panel to assembling the full wall.

Start with the [shopping list](flightwall-shopping-list.md) and follow the [build plan](flightwall-build-plan.md). Read this guide once before cutting wire. The examples use US shopping links; choose power supplies and plugs approved for your country. You can reuse suitable items you already own.

The procedure uses **five factory-enclosed, plug-in 5 V / 4 A supplies**, each feeding four panels. All work described here is on their low-voltage DC outputs. The original README's supply and drawing are background references; this guide uses a different power arrangement and an explicitly specified data buffer.

## 1. Understand the five connections

| Term on the part | Plain-language meaning |
| --- | --- |
| `5V`, `+5V`, `VCC`, or `+` | Positive power. The panels need **5 volts DC**. |
| `GND`, `0V`, `V−`, or `−` | Power return and the reference for the data signal. Here, these mean DC ground, not household protective earth. |
| `DIN`, `DI`, or an arrow pointing into the panel | Data input: connect the ESP32/buffer here, or the previous panel's output. |
| `DOUT`, `DO`, or an arrow pointing away | Data output: feeds the next panel's `DIN`. |
| `GPIO25`, `IO25`, or board label `25` | The ESP32's data signal pin in the **physical** firmware. It is not a 25 V connection. |

Electricity needs both a positive wire and a return wire. Data also needs a shared ground. The ESP32 produces a 3.3 V data signal; a **74AHCT125** buffer converts it to the 5 V logic used by the panels. This buffer does not supply LED power.

**Check the purchased panels:** they must be 5 V WS2812B-compatible, have 256 individually addressable RGB LEDs, and have accessible power and data connections. HUB75 panels, 12 V matrices, RGBW panels, and bare non-addressable matrices require different hardware or firmware. Connector colors and pin order are not universal: identify them from the panel markings and seller's pinout, then label them.

## 2. Set a realistic power limit

The current firmware sets `DISPLAY_BRIGHTNESS = 5` out of 255 in [UserConfiguration.h](../firmware/config/UserConfiguration.h). **Keep it at 5 throughout this build.** The bench-test program also uses 5.

For conservative planning, older WS2812B LEDs can use approximately 60 mA each at full white:

```text
20 panels × 256 LEDs = 5,120 LEDs
5,120 × 0.060 A = 307.2 A at full-brightness white
5 V × 307.2 A = 1,536 W
```

That is a possible design maximum, not a measured load for these particular panels. Newer parts may use less. At brightness 5, the light-producing part of that estimate is about 6 A across the wall, **plus electronics/idle current**. Actual idle current and panel behavior must be checked. A supply label alone cannot establish a safe brightness.

The five-supply arrangement below provides up to 4 A per group, with a **3 A main fuse per group and a 1 A fuse per panel**. It is intended for dim flight information and the specified dim test patterns. It cannot support unrestricted full-brightness patterns. A group must remain below its fuse, cable, connector, and supply ratings, with operating margin. Do not fit larger fuses or raise voltage to fix flickering or fuse failures.

The bench program uses FastLED's estimated power limiter. Before using production firmware, add the same kind of limit immediately after `FastLED.addLeds(...)` in [NeoMatrixDisplay.cpp](../firmware/adapters/NeoMatrixDisplay.cpp):

```cpp
FastLED.setMaxPowerInVoltsAndMilliamps(5, 8000); // Estimated whole-wall budget: 8 A
```

This is a software estimate, not a current measurement or protection for each power group. Keep the brightness at 5 and retain all fuses. This guide does not change production firmware for you. Brighter operation needs a new measured power/distribution design.

## 3. Choose a work area and identify every part

1. Work on a clear, dry table with eye protection and good light. Keep metal tools and loose wire ends away from circuit boards.
2. Leave every supply unplugged while making or changing a connection. Unplug ESP32 USB too. Allow capacitors to discharge; verify near 0 V with the meter before handling the wiring.
3. Check the supply label for **regulated 5 V DC, 4 A**, factory-enclosed mains wiring, a compatible local plug/cord, and center-positive output. The shopping list assumes a **5.5 mm outside / 2.1 mm inside barrel plug**; change the matching DC adapter if your selected supply uses something else.
4. Check that the DC jack/adapter is documented for **at least 5 A**, and that fuse blocks and terminals accept 18 AWG stranded copper. Do not assume a small barrel breakout supports the supply's current just because the plug fits.
5. Identify ESP32 `GND` and **GPIO25** using its board pinout. Use a classic ESP32-WROOM-32 development board with GPIO25 available. ESP32-C3/S3 boards have different pin assignments. On an R32 D1, follow the ESP32 GPIO labels, not an assumed Arduino Uno pin number.
6. Label the panels `P1` through `P20`, and the supply groups `A` through `E`. Leave the panels loose until the one-panel test confirms their orientation.

An open metal power supply with terminals marked `L`, `N`, and protective earth has exposed household-voltage connections. **Do not use it for this beginner procedure.** If you already own one, have a qualified person prepare its mains wiring, earthing, enclosure, strain relief, and DC distribution before using a separate design. Never connect a panel or ESP32 to household voltage.

## 4. Learn the multimeter first

A digital multimeter is the volt meter you need. For this build, use its **DC voltage** and **continuity** functions. Practice before connecting the LEDs.

### Measure DC voltage

1. Put the black lead in the socket labeled `COM`.
2. Put the red lead in the socket labeled `V` or `VΩ`. **Leave `A`/`mA` current sockets empty.**
3. Select DC volts, usually `V⎓` or `V` with a straight/dashed line. On a manual-range meter, choose 20 V DC. AC volts (`V~`) is the wrong setting here.
4. Use a suitable insulated DC adapter so the two output terminals cannot touch. With the supply unplugged, clip black to the terminal you expect to be negative and red to positive. Cover adjacent metal and keep the clips apart.
5. Plug in the supply, read the meter, then unplug before moving clips. Expect about **5.0 V**; a useful commissioning target is **4.75–5.25 V**, subject to the panel's own stricter specification. A minus sign means the probes/polarity are reversed; correct the labels before connecting anything.
6. Repeat this for **all five supplies**, independently, before joining grounds.

Measure **across** positive and negative, never across those points in current mode. A meter set to amps can short the supply. If you later want current readings, use a suitably rated **DC-capable clamp meter**, zero it, and clamp one positive wire only. A normal AC-only clamp will not measure this DC load. Do not learn inline multimeter current measurement on this wall.

### Check continuity with power disconnected

Continuity means the meter detects an electrical path, often with a beep. Unplug all supplies and USB, disconnect electronics for cable checks, and verify stored voltage is near zero before selecting it.

- Touch the probes together: the meter should beep/read close to zero ohms.
- Check each end of a wire: that should also show a low resistance.
- Check a loose cable's positive wire against its ground wire: there should be no connection.
- Test a fuse out of circuit: a good fuse has continuity; an open/blown fuse does not.
- Verify modified data cables have continuity only on their intended data and ground conductors.

A capacitor or connected electronics may briefly beep while charging from the meter. A beep on an assembled board is not, by itself, proof of a short. If the positive/ground reading stays close to zero, disconnect branches and find the cause before powering up. Never discharge a capacitor with a screwdriver.

## 5. Make one fused power group

Each group powers **four panels independently**. Every panel gets its own positive and ground feed. The data chain does not carry the panels' positive power.

```text
Factory-enclosed 5 V / 4 A plug-in supply
  positive -> rated DC jack -> 3 A inline main fuse -> covered fuse-block positive input
                                                     |-> 1 A fuse -> panel 1 +5V
                                                     |-> 1 A fuse -> panel 2 +5V
                                                     |-> 1 A fuse -> panel 3 +5V
                                                     `-> 1 A fuse -> panel 4 +5V
  negative -> rated DC jack ------------------------> ground/negative bus
                                                     |-> panel 1 GND
                                                     |-> panel 2 GND
                                                     |-> panel 3 GND
                                                     `-> panel 4 GND

1000 µF capacitor: + to fused positive input; − to ground bus
```

Use a fuse block with covered positive terminals and a separate negative bus, or add a covered negative terminal block. Ordinary blade fuses work at 5 V when appropriately rated for DC; a block's optional blown-fuse indicator may not work at 5 V. Test fuses with the meter instead.

1. Cut **18 AWG stranded copper** positive and ground wires. For this layout, keep the jack-to-block leads about 20 cm or less and each block-to-panel lead about 75 cm or less, with small service loops. Put the block near the middle of its four panels. Longer runs need a voltage-drop review.
2. Strip only the length needed by the terminal. Do not nick strands or leave bare copper outside the clamp. Use the manufacturer's terminal style: properly crimped ring terminals on studs, or ferrules on stranded-wire screw terminals **when the terminal manufacturer allows them**.
3. Fit the 3 A main fuse holder close to the DC jack on the positive lead. Use appropriately rated holders and wire. Do not put a fuse in the ground wire instead.
4. Connect jack negative to the negative bus. Verify jack polarity rather than trusting wire colors.
5. Connect four positive panel leads through four separate 1 A fuse positions. Connect four ground leads to the negative bus. Leave unused fuse positions empty and covered.
6. Fit one **1000 µF electrolytic capacitor, rated at least 10 V**, across the block's fused input and ground. The capacitor's stripe normally marks **negative**; confirm the part markings. Insulate its leads, secure it, and keep it out of reach of metal hardware. Reversing an electrolytic can damage it.
7. Use the panel's separate power pigtail or marked `+5V`/`GND` pads. If there are no suitable power leads, solder correctly sized pigtails to those pads using the soldering procedure below. Check the connector and panel lead rating; do not retain a connector rated below the 1 A branch protection.
8. Fit fuses, tug-test connections gently, and inspect every strand. With the supply unplugged, check cable continuity and absence of accidental positive/ground bridges.

For the first test, connect **only P1** to its fused output. Leave the other three panel branches disconnected. P1's fused 5 V output can also feed the low-current data buffer below; its ground joins the same negative bus.

Do not power LEDs through a solderless breadboard, Dupont jumper, USB cable, or the ESP32's `5V`, `VIN`, or `3V3` pin. Do not solder-tin stranded wire and then clamp it under a screw: use the specified crimp/ferrule termination instead.

## 6. Wire the 74AHCT125 data buffer

Use a **14-pin DIP 74AHCT125** for this pin table. A preassembled breakout is also usable if its schematic identifies the equivalent connections; do not apply DIP pin numbers to an unrelated board. A generic bidirectional BSS138/I²C converter, often labeled `LV`/`HV`, is not the specified buffer for the WS2812B data signal.

With the DIP chip's notch at the top, pin 1 is at upper left. Count down the left side to pin 7, then up the right side from pin 8 to pin 14:

```text
          notch
       .---U---.
  1OE  |1    14| VCC
  1A   |2    13| 4OE
  1Y   |3    12| 4A
  2OE  |4    11| 4Y
  2A   |5    10| 3OE
  2Y   |6     9| 3A
  GND  |7     8| 3Y
       '-------'
```

| From | To | Purpose |
| --- | --- | --- |
| P1's **fused** +5 V feed | Buffer pin **14** (`VCC`) | Powers the buffer at 5 V. |
| Group A ground bus | Buffer pin **7** (`GND`) | Shared ground. |
| Buffer pin **1** (`1OE`) | Ground bus | Enables channel 1; this enable is active low. |
| ESP32 **GPIO25** | Buffer pin **2** (`1A`) | 3.3 V data input. |
| Buffer pin **2** | **10 kΩ resistor** → ground | Keeps the input low when GPIO25 is not driving it. |
| Buffer pin **3** (`1Y`) | **330 Ω resistor** → P1 **DIN** | 5 V data output. Place the resistor near P1's DIN. |
| ESP32 **GND** | Group A ground bus | Required data reference. |
| **0.1 µF ceramic capacitor** | Across buffer pins **14 and 7** | Decoupling; place close to the chip with short leads. |
| Buffer pins **4, 10, 13** (unused `OE`) | Fused +5 V | Disables unused channels. |
| Buffer pins **5, 9, 12** (unused `A`) | Ground | Stops unused inputs floating. |
| Buffer pins **6, 8, 11** (unused `Y`) | Leave unconnected | Unused outputs. |

Use a small breadboard for the buffer's **signal circuit only** while practicing. For the finished wall, move it to soldered perfboard with a chip socket, insulated connections, and mounting spacers. Keep the GPIO-to-buffer lead short and the buffer-to-P1 lead about 20 cm or less. Run data with an adjacent ground conductor, away from supply cables.

Power the ESP32 through its **USB connector** from a computer during testing and a suitable USB charger afterward. Do **not** connect any LED supply's positive output to the ESP32's USB/5 V rail in this procedure. ESP32 ground still connects to the wall's DC ground.

For a test, power the connected LED group first, then connect ESP32 USB. To shut down, unplug ESP32 USB first, then the LED supply. Do not leave an active data signal connected to an unpowered panel chain. Make every wiring change with both disconnected.

## 7. Practice on one panel

The [standalone bench-test project](examples/wiring-test/README.md) needs no Wi-Fi, Pi, or API key. It checks the LEDs independently of the flight software. Follow its install/upload steps and use the **`panel1`** environment first; the Wokwi environment is not a physical wiring test.

1. With power unplugged, check all connections against the power diagram and buffer table. Confirm P1 `DIN`, not `DOUT`, receives the signal.
2. Clip the voltmeter across P1's power input, black to GND and red to +5 V. Make sure the clips cannot touch.
3. Power group A. Check correct voltage/polarity, then connect ESP32 USB and upload the `panel1` test.
4. Open its serial monitor at **115200 baud**. Send `off`, then `red`, `green`, and `blue`, one at a time. Use **Send/Newline** after each command. Colors should match; odd colors can mean a different LED color order.
5. Send `white`. This means white **at brightness 5**, not maximum brightness. Check panel voltage under load. Aim for 4.75–5.25 V, within the panel's specification; the supply must not repeatedly restart. Do not raise brightness during this test.
6. Send `pixel 0`, then `pixel 1`. Note the physical LED positions. This firmware expects pixel 0 at the **front-view bottom-right** of each tile and pixel 1 immediately above it, followed by vertical serpentine columns.
7. Send `corners`: **red = top left; green = top right; blue = bottom left; white = bottom right**, as viewed from the lit front. Send `border` to check the outline.
8. If the geometry is wrong, compare the panel's real pixel path with the matrix flags in the bench program and production display adapter. A rotation may fix a rotated path; another panel design may need different row/column/serpentine flags. Make the same mapping choice in both places before mounting twenty tiles. Do not change the signal to GPIO5; that pin belongs to Wokwi only.
9. Send `off`, disconnect USB, and unplug the supply. Gently tug each joint. During later powered operation, look for discoloration, softening, smell, or unstable voltage; disconnect power immediately if any appears. Do not reach into an energized circuit to inspect it.

**Pass:** all 256 LEDs respond, colors and corner positions match, voltage is stable with the dim white pattern, and connections remain mechanically secure. Fix a failure here before buying or assembling the remaining groups.

## 8. Lay out the twenty-panel data chain

The physical firmware currently uses `NEO_TILE_TOP + NEO_TILE_RIGHT + NEO_TILE_COLUMNS + NEO_TILE_ZIGZAG`. The tile numbers below match those flags. **The matrix library also flips the internal pixel origin in alternate tile columns**, so those physical columns need a 180° rotation relative to the first column. Checking only the tile numbers is not enough.

**Front view — you are looking at the illuminated LEDs:**

```text
Top:     P20  P17  P16  P13  P12  P09  P08  P05  P04  P01
Bottom:  P19  P18  P15  P14  P11  P10  P07  P06  P03  P02
          E    E    D    D    C    C    B    B    A    A
```

**Back view — you are looking at the wires, with the wall's top still up:**

```text
Top:     P01  P04  P05  P08  P09  P12  P13  P16  P17  P20
Bottom:  P02  P03  P06  P07  P10  P11  P14  P15  P18  P19
          A    A    B    B    C    C    D    D    E    E
```

Connect **buffer → P1 DIN → P1 DOUT → P2 DIN → … → P20 DIN**. P20 DOUT remains unconnected and insulated. This snakes vertically in pairs of panels, across columns. A left-to-right snake along the whole top row will not match the current firmware.

| Physical orientation, viewed from the lit front | Panels |
| --- | --- |
| Same orientation as the tested P1: pixel 0 bottom right, pixel 1 above it | P1–P2, P5–P6, P9–P10, P13–P14, P17–P18 |
| Rotated **180°** from P1: pixel 0 top left, pixel 1 below it | P3–P4, P7–P8, P11–P12, P15–P16, P19–P20 |

Mark each panel's physical pixel-zero corner before mounting. This rotation rule follows the library's zigzag-tile behavior; it is separate from reversing the tile order. If you change the mapping, validate all module/full-wall corner tests again. The [Framebuffer_GFX pixel-mapping source](https://github.com/marcmerlin/Framebuffer_GFX/blob/master/Framebuffer_GFX.cpp) documents the alternate-column corner flip.

| Group / supply | Its four independently fused panels |
| --- | --- |
| A | P1, P2, P3, P4; also powers the buffer through P1's fused branch |
| B | P5, P6, P7, P8 |
| C | P9, P10, P11, P12 |
| D | P13, P14, P15, P16 |
| E | P17, P18, P19, P20 |

**Important with multiple supplies:** their positive outputs must stay separate. Use **data + ground only** for every inter-panel link. If using a supplied three-wire connector, remove its +5 V conductor and insulate both abandoned ends; verify the result with the meter. Do not simply plug all three-wire panel connectors together. Each panel already receives positive power from its own fuse.

Join the five **negative/ground buses** with 18 AWG ground links and connect ESP32/buffer ground to group A. This gives the data chain a shared reference. Before attaching panels, with supplies unplugged, confirm continuity among the ground buses and **no continuity among different groups' positive buses**. Inspect cable pinouts rather than trusting the connectors' genders or colors.

Build group A as a four-panel module first. Use the bench project's **`panel4`** environment, verify P1–P4 using `walk`, and check `corners`/`border` on that 2×2 module. Build and test the other four modules individually before connecting the complete chain.

## 9. Assemble, test, and mount the full wall

1. Lay out all panels in the verified order. Keep them supported; flexible panels are not structural parts. Measure your actual panel size before cutting the backer or rails. The original build was about 63 × 12.6 inches (160 × 32 cm).
2. Use a rigid backer or the repository's [printed brackets](../brackets/) with two rigid horizontal supports. Provide clearance for wires, cooling, and solder joints. Do not let metal mounting hardware touch pads or let screw tips reach LEDs/traces. Keep electronics and connections away from combustible packing materials.
3. Mount the five distribution blocks near their four-panel groups and cover the terminals. Secure the buffer in an insulated enclosure. Mount each factory-enclosed supply with ventilation and according to its instructions; do not bury it in insulation or close it inside an unventilated box.
4. Route each panel's fused positive and ground leads to its assigned block. Add strain relief to cables so connectors and solder pads do not carry pulling forces. Label supply voltage, group, fuse values, and each branch.
5. Unplug everything and repeat polarity, cable, fuse, ground-continuity, and positive-isolation checks. Check for reversed capacitor leads and exposed cut +5 V ends in data cables.
6. Connect all five tested power groups and the 19 data/ground links. Power the groups, connect USB, and upload the bench **`panel20`** environment.
7. Send `walk`. Its single red pixel should visit **P1, P2, …, P20** in that order. Then send `corners` and `border`; verify the entire 160×32 outline and front-view corner colors.
8. Test `red`, `green`, `blue`, and dim `white`. Measure voltage at **every panel's own input** under dim white, not just at the supply. Power down before relocating meter clips. A large drop calls for better/shorter wire or better connections, not a higher supply voltage. For this commissioning target, more than about 0.25 V from supply output to panel input merits investigation.
9. Supervise a 30-minute dim-pattern test. Check for resets, fuse failures, flickering, smells, discoloration, and warm connector housings visible with power off. If measuring current, use the optional DC clamp on one group's positive lead and retain margin below 3 A. Inability to run the prescribed pattern means that group needs investigation or a revised design.
10. Send `off`, unplug USB and all supplies, and inspect again. Install covers and cable restraints. Keep the main disconnect accessible.
11. Only after bench tests pass, configure and upload production firmware using **`esp32dev`**, with GPIO25, 10×2 tiles, brightness 5, and the estimated 8 A limiter described above. Set Wi-Fi in [WiFiConfiguration.h](../firmware/config/WiFiConfiguration.h) and `RPI_BASE_URL` in [APIConfiguration.h](../firmware/config/APIConfiguration.h) to the Pi's LAN address/port. See [local firmware setup](../firmware/README.md#local-flight-data).
12. Keep the working assembly on the table for a supervised flight-display test before hanging it. Use wall fasteners appropriate to the measured assembly weight and the wall material; anchor a long/heavy display to suitable structure. Get help lifting it and avoid drilling where utilities may run.

Use a listed power strip with enough sockets for five supplies and the ESP32 USB charger. Keep adapters and plugs accessible and within the strip's rating. A single switched strip is a convenient finished-wall disconnect once the computer USB cable has been removed. Do not leave the computer powering the ESP32 while the wall supplies are switched off.

## 10. Connect the flight data separately

The Pi sends flight information over your **LAN/Wi-Fi**; it does not power the LED wall. There is no Pi-to-ESP32 GPIO, serial, or LED-power cable in this design. Keep the Pi and existing SDR on their own normal supply.

The current production firmware polls the Pi's local **`GET /v1/flights`** feed, without an OpenSky/AeroAPI/CDN fallback. Set the Pi address and Wi-Fi in the compiled configuration headers; follow the [Pi service setup](../pi_enrichment/README.md) and [local feed contract](local-flight-api.md). The [local implementation plan](flightwall-local-plan.md) assumes an existing Pi/readsb/SDR installation and includes remaining work such as BLE configuration, airline/logo enrichment, and additional telemetry display. Those features are not prerequisites for wiring tests. Do not buy a second receiver or paid API subscription to build this wall.

## 11. Solder only where needed

A permanent DIP-buffer board and panels without power pigtails require soldering. Buy prewired panels and a correctly specified preassembled buffer if you want to reduce it.

1. Unplug all power and USB. Practice on spare wire/perfboard first.
2. Use a temperature-controlled iron, its stand, electronics solder, compatible flux, eye protection, and ventilation/fume extraction. Follow the solder manufacturer's temperature guidance; use electronics flux, not plumbing flux.
3. For a wire-to-pad solder joint, place heat-shrink on the wire first, strip a short end, lightly tin that end and the pad, then join them with brief heat. Let the joint cool without moving it. Do not overheat flexible panel pads.
4. Inspect for bridges, exposed strands, and loose joints. Check the disconnected cable/board electrically before powering it.
5. Insulate the joint and secure the cable nearby for strain relief. Use a heat gun carefully to shrink insulation, keeping heat away from the LEDs and panel plastic. Never use a flame.

The tinned-wire step applies to a soldered joint, **not** a screw-clamped terminal. If a pad lifts or a joint cannot be made reliably, stop and have an experienced builder repair that joint.

## 12. Troubleshooting

Disconnect supplies and USB before changing any wiring. Start with the first failing panel; the fault can be in the preceding panel's output or the link between them.

| Symptom | Check in this order |
| --- | --- |
| Nothing lights | Correct 5 V polarity at P1; intact main/branch fuses; ESP32 USB power; physical `panel1`/`panel20` environment; GPIO25; buffer pin 1 grounded; P1 DIN rather than DOUT. |
| One group is dark | That supply's voltage; its 3 A main fuse; four 1 A branch fuses; ground/input terminals. Avoid sending data into a partly unpowered chain. |
| First panels work, later ones fail | Last working DOUT → first failed DIN; shared ground; the failed panel's fused feed; connector pin order. |
| Flicker, random colors, or resets | Voltage at the affected panel under load; loose ground; buffer type/wiring; short data lead paired with ground; capacitor polarity; supply overload. |
| Red/green/blue do not match | Actual panel color order vs firmware `GRB`; check both the bench sketch and production adapter. |
| Text is mirrored or tiles are scrambled | Front/back labels; P1–P20 chain; each tile's pixel-zero position; matrix row/column/zigzag flags. Changing brightness will not fix mapping. |
| A fuse opens | Unplug everything. Find a short, reversed capacitor/panel, excessive load, or damaged cable. Replace only with the same value after the cause is resolved. |
| Dim white causes a group to restart | Current/idle load or a poor connector can exceed this design. Retest one panel at a time at brightness 5; do not bypass fuses. |
| LEDs pass tests but flights do not appear | Diagnose Wi-Fi and the chosen data software separately. Successful wiring does not establish Pi/API integration. |

## 13. Keep a commissioning record

Record supply make/model and voltage, panel model/pinout, connector ratings, fuse values, cable lengths, mapping changes, test environment, and the measured voltage at each panel under dim white. Keep a photograph of each finished group's wiring and a copy of the firmware settings. Label any change from this guide.

Before calling the wall complete, confirm: all 20 panels pass the color/geometry checks; each has its own fused power feed; group positives stay separate; grounds are common; all terminals are covered; the main disconnect is accessible; and the chosen flight software has passed its own end-to-end test.
