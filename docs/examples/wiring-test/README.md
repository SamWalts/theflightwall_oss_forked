# Physical LED bench test

This is a **separate PlatformIO project**. Uploading it replaces the program on your ESP32; upload the production firmware again after testing. It leaves production source/configuration files alone and needs no Wi-Fi, Raspberry Pi, or flight-data account.

Follow the [wiring guide](../../beginner-wiring-guide.md) before connecting power. Use **GPIO25**, the specified 74AHCT125 buffer, independent fused 5 V feeds, and shared DC ground. Brightness is fixed at **5/255**, with an estimated FastLED power budget of **400 mA per panel / 8 A for twenty**. The estimate does not replace per-panel/group fuses or voltage/load checks. There is no command to increase brightness.

## Install and upload with VS Code

1. Install [VS Code](https://code.visualstudio.com/) and its [PlatformIO IDE extension](https://platformio.org/install/ide?install=vscode). Initial installation/builds need internet access for toolchains/libraries.
2. Open **this folder**, `docs/examples/wiring-test`, as the project, rather than the repository's `firmware` folder.
3. Open the PlatformIO sidebar. Under **Project Tasks**, choose the environment for your connected panels:

   | Environment | Connected panels | Geometry |
   | --- | --- | --- |
   | `panel1` | P1 only | 16×16 |
   | `panel4` | One four-panel power module | 32×32, two tile columns |
   | `panel20` | Complete P1–P20 chain | 160×32, ten tile columns |

4. Select that environment's **Build** task. With wiring checked, power the connected LED groups, connect the ESP32 with a **USB data cable**, then select **Upload**. If the computer does not detect the board, check the cable and the board maker's USB-driver instructions. Some boards need the **BOOT** button held as upload starts; follow that board's instructions.
5. Select **Monitor**, at 115200 baud. Reset the ESP32 if you missed its startup help. Type a command and press Enter; the monitor's `send_on_enter` filter sends the complete line. Other serial terminals must append a newline.
6. Start with `off`, then the color and geometry tests below. LEDs start blank until you send a command.

If using the PlatformIO CLI instead, run these from this folder. Substitute `panel4` or `panel20` only when the matching panels are wired and powered:

```sh
pio run -e panel1
pio run -e panel1 -t upload
pio device monitor -b 115200 -f send_on_enter
```

## Commands

| Command | Result |
| --- | --- |
| `help` | Print commands. |
| `off` | Stop walking and blank the LEDs. **Power is still connected.** |
| `red`, `green`, `blue` | All connected pixels show the selected dim color. |
| `white` | All pixels show dim white at brightness 5; use for voltage-drop/load checks. |
| `pixel 0`, `pixel 1` | Light one zero-based pixel white; identify the panel's physical origin/direction. Other indices up to `pixel_count − 1` are accepted. |
| `panel 1` | Light the first LED of that **one-based** panel red. Maximum is 1, 4, or 20 for the selected environment. |
| `walk` | Visit each panel's first LED once per second and print its number. `off` stops it. |
| `corners` | Front-view corners: top left red; top right green; bottom left blue; bottom right white. |
| `border` | Dim white outline around the configured module/wall. |

The tile mapping matches [production NeoMatrixDisplay.cpp](../../../firmware/adapters/NeoMatrixDisplay.cpp): first tile at front-view top right, column snake, the first column's pixel 0 at bottom right with vertical serpentine pixels. **Alternate tile columns are rotated 180° by the library's `NEO_TILE_ZIGZAG` mapping.** Physically orient alternate columns accordingly; see the numbered diagrams and rotation table in the guide. If your purchased panel has another internal pixel order, adjust the matrix flags in **both** programs before mounting it.

The current color order is `GRB`, as in production. If individual colors are wrong despite stable power and correct buffer wiring, confirm the panel's actual color order before editing both programs.

## Completion

Record the colors, walk order, corner positions, and panel voltage readings. Disconnect USB and LED supplies before changing anything. Use the `panel20` tests and the guide's supervised run before hanging the wall. Then upload `firmware`'s **`esp32dev`** environment with the specified production brightness/power settings.

Compilation/host checks do not establish physical electrical acceptance. These tests must still be run on your actual panels, supplies, connectors, and wiring.
