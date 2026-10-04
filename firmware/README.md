# TheFlightWall Firmware

This is a high-level overview of the firmware that powers TheFlightWall on ESP32.

### Local flight data

The live firmware polls `GET /v1/flights` from the Raspberry Pi every two seconds.
OpenSky, AeroAPI, and FlightWall CDN adapters are retained as legacy source files
but excluded from both PlatformIO builds. LAN failures have no external fallback.
Aircraft without callsigns or reference matches remain displayable using their hex
address. Local cards show identifier/type, barometric altitude/ground speed, and
vertical speed; absent telemetry displays `?`.

Set Wi-Fi in `config/WiFiConfiguration.h` and `RPI_BASE_URL` in
`config/APIConfiguration.h` to the Pi's LAN address and port, for example
`http://192.168.1.50:8080`. Use the IP if `.local` DNS is unavailable.
Set display wiring/brightness in the hardware and user configuration headers.
The first local feed uses all fresh positioned aircraft received by the Pi, capped
at eight; the old compiled San Francisco location is not applied.

The Pi runs `pi_enrichment/server.py`; see its README and
[local feed contract](../docs/local-flight-api.md). The display distinguishes Wi-Fi
disconnected, Pi unavailable (including unusable feed), receiver stale, and healthy
no-aircraft. The `wokwi` environment remains a display-only mock; it does not test
the Pi HTTP adapter.

This parser consumes the initial flat prototype, not the nested
[M1 contract draft](../docs/api/README.md). Their shared `schema_version=1` does
not imply compatibility. Canonical parsing and monotonic expiry remain M3 work.

Pi address and Wi-Fi are still compiled settings. NVS/BLE provisioning, geographic
filtering, airline reference resolution, actual local logo assets, and full
IAS/TAS display are follow-up milestones in the implementation plan. Hardware
operation has not been validated by the Python tests.

### Build
- PlatformIO project: see `platformio.ini`.

### Wokwi display mock (local macOS + VS Code)
- Added a dedicated PlatformIO environment: `wokwi` (`-D WOKWI_DISPLAY_MOCK`).
- The Wokwi wiring is defined in `diagram.json` and uses a simulated 64x32 NeoPixel matrix.
- The earlier `dev` branch's 20-panel layout is retained in
  [diagram-160x32-reference.json](diagram-160x32-reference.json). It uses GPIO 13
  and is a separate wiring reference; the active 64x32 mock uses GPIO 5. Simulator
  compatibility and physical wiring validation remain M0/M6 work.

CLI flow:
1. `cd firmware`
2. `pio run -e wokwi`
3. `wokwi-cli --interactive .`

VS Code flow:
1. Open `firmware` in VS Code with PlatformIO + Wokwi extensions installed.
2. Build `wokwi` environment.
3. Run **Wokwi: Start Simulator** from the Command Palette.
4. Open the serial monitor and use commands:
   - `help`
   - `demo`
   - `stop`
   - `flight 0`
   - `msg HELLO`
   - `load`
   - `clear`

### Notes
- Display uses `FastLED_NeoMatrix` with WS2812B strips; adjust tiling/orientation in hardware config.
- Build both environments with `pio run -e esp32dev -e wokwi`.
