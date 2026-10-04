# TheFlightWall Firmware

This is a high-level overview of the firmware that powers TheFlightWall on ESP32.

### What it does
- **Fetch nearby aircraft** from OpenSky Network using OAuth (states/all) filtered by location, radius, and bearing.
- **Enrich flights** with readable airline/aircraft info and airline logo metadata from AeroAPI/TheFlightWall CDN.
- **Render** a clean, minimal three-line flight card on a WS2812B LED matrix.

### Key components
- **src/main.cpp**: Entry point. Initializes serial, Wi‑Fi, fetchers, and display. Periodically fetches/enriches and renders.
- **core/FlightDataFetcher**: Orchestrates: fetch state vectors → fetch flight metadata → enrich names.
- **adapters/OpenSkyFetcher**: Queries OpenSky states/all with OAuth; parses and filters by geo.
- **adapters/AeroAPIFetcher**: Retrieves flight details by ident via AeroAPI.
- **adapters/FlightWallFetcher**: Looks up airline/aircraft names from CDN and optional local Pi enrichment service.
- **adapters/NeoMatrixDisplay**: Draws bordered, centered three‑line flight card; cycles flights; shows loading.
- **config/**: User/API/timing/hardware/Wi‑Fi settings.
- **models/**: Lightweight structs for `StateVector`, `FlightInfo`, `AirportInfo`.
- **utils/GeoUtils.h**: Haversine distance and bounding boxes.

### Configuration quickstart
- Set Wi‑Fi in `config/WiFiConfiguration.h`.
- Set location and display preferences in `config/UserConfiguration.h`.
- Set intervals in `config/TimingConfiguration.h`.
- Set display dimensions/pin in `config/HardwareConfiguration.h`.
- Provide API credentials/URLs in `config/APIConfiguration.h` (OpenSky OAuth, AeroAPI key, CDN base, optional `PI_ENRICHMENT_BASE_URL`).

### Optional local Pi enrichment
- Set `PI_ENRICHMENT_BASE_URL` in `config/APIConfiguration.h` to your Pi service (for example `http://192.168.1.50:8080`).
- Firmware will query `GET /v1/aircraft/{adsb_icao}` first and fall back to CDN enrichment when local data is unavailable.

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
- OpenSky OAuth is required for `states/all`. Token auto‑refreshes with a safety skew.
- Display uses `FastLED_NeoMatrix` with WS2812B strips; adjust tiling/orientation in hardware config.
- Raspberry Pi API migration stubs are available in `config/APIConfiguration.h`:
  - `USE_RPI_API_STUBS` toggles local-RPi path selection.
  - `RPI_BASE_URL` + `RPI_FLIGHT_INFO_PATH` and `RPI_LOOKUP_PATH` are placeholders for flight/lookup APIs.
  - `RPI_LOGO_BASE_URL` + `RPI_LOGO_PATH` is a separate logo endpoint placeholder.
