> Local migration has begun: the live ESP32 firmware now uses the Pi's
> `/v1/flights` endpoint without OpenSky/AeroAPI/CDN fallback. See
> [firmware setup](firmware/README.md) and the [local feed contract](docs/local-flight-api.md).
> The cloud setup instructions below describe the legacy implementation.

# TheFlightWall

TheFlightWall is an LED wall which shows live information of flights going by your window.

The planned migration to a local readsb → Pi → ESP32 system is documented in
[architecture.md](architecture.md). Follow the [implementation checklist](docs/implementation-plan.md)
and [development guide](CONTRIBUTING.md); AI contributors should start with
[AGENTS.md](AGENTS.md) and [project context](docs/project-context.md). The software
setup below describes the legacy cloud firmware. The initial local feed and
firmware parser differ from the M1 draft; canonical migration remains pending.
See [route lookup research](docs/route-detection.md) for free callsign-to-airport
reference data suitable for overhead flights and Google/manual verification.
The Pi now implements [offline route import and lookup](pi_enrichment/README.md#offline-departuredestination-lookup)
with streamed SQLite storage; its [route contract](docs/api/routes.md) distinguishes
reference routes from dated flight verification.
The [M1 contract draft](docs/api/README.md) now documents the Pi-to-ESP32 feed,
logo assets and diagnostics. See the [ADS-B receiver inventory](docs/adsb-receiver-data.md)
and [enrichment joins](docs/api/enrichment-joins.md) for how telemetry becomes
aircraft details, airline logos and likely departure/destination pairs.

This is the open source version with some basic guides to the panels, mounting them together, data services, and code. Check out our viral build video: [https://www.instagram.com/p/DLIbAtbJxPl](https://www.instagram.com/p/DLIbAtbJxPl)

**Don't feel like building one? Check out the offical product: [theflightwall.com](https://theflightwall.com)**

![Main Image](images/main-image.png)
*Original wall photo. AeroAPI logo metadata belongs to the legacy firmware;
the initial local feed does not yet supply airline logos.*

## New screen designs for review

The [screen review package](docs/screens/README.md) proposes five flight pages with airline emblems, [no-departure options](docs/screens/mockups/no-departure-options.png), system states, and partial-data fallbacks for the 160×32 wall. Open the [interactive mockups](docs/screens/review.html) or [review PDF](docs/screens/flightwall-screen-review.pdf). Firmware integration is separate.


# Component List
- Main components
    - 20x [16x16 LED panels](https://www.aliexpress.us/item/2255800358269772.html)
    - ESP32 dev board (we used the [R32 D1](https://www.amazon.com/HiLetgo-ESP-32-Development-Bluetooth-Arduino/dp/B07WFZCBH8) but any ESP dev board should work)
    - 3D printed brackets (or MDF / cardboard)
    - 2x 6ft wooden trim pieces (for support)
- Power
    - [5V >20A power supply](https://www.amazon.com/dp/B07KC55TJF) (for 20 panels)
    - [3.3V - 5V voltage level shifter](https://www.amazon.com/dp/B07F7W91LC)
- Data
    - [OpenSky](https://opensky-network.org/) for ADS-B flight data
    - [FlightAware AeroAPI](https://www.flightaware.com/commercial/aeroapi/) for route, aircraft, and airline information

# Hardware

## Dimensions

With 20 panels (10x2) - ~63 inches x ~12.6 inches

## LED Panels
[These are the LED panels we used](https://www.aliexpress.us/item/2255800358269772.html), but any similar LED matrix should work.

We designed 3D printable brackets to attach the panels together, this is one approach, but you could also use MDF board or even cardboard (as we did originally haha)

Then two 63 inch horizontal supports for extra strength. We bought wooden floor trim and cut it to size.

![LED Panel Wiring and Brackets](images/led-panel-wiring-and-brackets.jpg)

Obviously this is just one way to hold them together, but we're sure there are better ways!

## Wiring

Here is a wiring diagram for how to connect the whole system together.

![Wiring Diagram](images/wiring-diagram.png)

The entire panel is controlled by one data line - simple electronics in exchange for very low refresh rates, don't expect any 60 FPS gaming on this panel!

# Data and Software

## Data API Keys

The data for this project consists of two main data sources:
1. Core public [ADS-B](https://en.wikipedia.org/wiki/Automatic_Dependent_Surveillance%E2%80%93Broadcast) data for flight positions and callsigns - using [OpenSky](https://opensky-network.org)
2. Flight information lookup - aircraft, airline, and route (origin/destination airport). This is typically the hardest / most expensive information to find. Using [FlightAware AeroAPI](https://flightaware.com/aeroapi)

Optional local enrichment:
- Run the Raspberry Pi FAA enrichment API to map ADS-B ICAO (`hex`) to operator and model data.
- See [pi_enrichment/README.md](pi_enrichment/README.md) for API contract, FAA sync pipeline, and systemd setup.
- For one-machine Docker testing of both Pi enrichment and a FlightWall simulator, see [docker/README.md](docker/README.md).

### Setting up OpenSky
1. Register for an [OpenSky](https://opensky-network.org/) account
2. Go to your [account page](https://opensky-network.org/my-opensky/account)
3. Create a new API client and copy the `client_id` and `client_secret` to the [APIConfiguration.h](firmware/config/APIConfiguration.h) file


### Setting up AeroAPI
1. Go to the [FlightAware AeroAPI](https://flightaware.com/aeroapi) page and create a personal account
3. From the dashboard, open **API Keys**, click **Create API Key** and follow the steps
8. Copy the generated key and add it to [APIConfiguration.h](firmware/config/APIConfiguration.h)


## Software Setup

### Set your WiFi

Enter your WiFi credentials into `WIFI_SSID` and `WIFI_PASSWORD` in [WiFiConfiguration.h](firmware/config/WiFiConfiguration.h)

### Set your location

Set your location to track flights by updating the following values in [UserConfiguration.h](firmware/config/UserConfiguration.h):

- `CENTER_LAT`: Latitude of the center point to track (e.g., your home or city)
- `CENTER_LON`: Longitude of the center point
- `RADIUS_KM`: Search radius in kilometers for flights to include

### Build and flash with PlatformIO

The firmware can be built and uploaded to the ESP32 using [PlatformIO](https://platformio.org/)

1. **Install PlatformIO**: 
   - Install [VS Code](https://code.visualstudio.com/)
   - Add the [PlatformIO IDE extension](https://platformio.org/install/ide?install=vscode)

2. **Configure your settings**:
   - Add your API keys to [APIConfiguration.h](firmware/config/APIConfiguration.h)
   - Add your WiFi credentials to [WiFiConfiguration.h](firmware/config/WiFiConfiguration.h)
   - Set your location (and optional display preferences) in [UserConfiguration.h](firmware/config/UserConfiguration.h)
   - Adjust display hardware (pin, tile layout) in [HardwareConfiguration.h](firmware/config/HardwareConfiguration.h)

3. **Build and upload**:
   - Open the `firmware` folder in PlatformIO
   - Connect your ESP32 via USB
   - Click the "Upload" button (→) in the PlatformIO toolbar

### macOS flight count logger

If you want a simple macOS script that tracks how many flights are near a point and prints CSV rows, use [`opensky_flight_counter.py`](opensky_flight_counter.py).

1. Add your OpenSky `client_id` and `client_secret` either:
   - as `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` environment variables, or
   - on the command line with `--client-id` / `--client-secret`
2. Run it with your desired location and radius:

   ```bash
   python3 opensky_flight_counter.py \
     --latitude 37.7749 \
     --longitude -122.4194 \
     --radius-km 10
   ```

3. The script prints CSV output to stdout, so you can save a 24+ hour run with shell redirection if needed:

   ```bash
   python3 opensky_flight_counter.py --latitude 37.7749 --longitude -122.4194 --radius-km 10 >> flights.csv
   ```

Useful options:
- `--interval-seconds 60` to control polling frequency
- `--run-once` to fetch one row and exit
- `--timeout-seconds 30` to control HTTP timeouts

### Mock the display with Wokwi (macOS + VS Code)

You can run a mock LED display without hardware using Wokwi:

1. Open `firmware/` in VS Code.
2. Build the `wokwi` PlatformIO environment.
3. Start the simulator (Wokwi extension) from VS Code, or run locally:
   - `cd firmware`
   - `pio run -e wokwi`
   - `wokwi-cli --interactive .`
4. In serial monitor, use simple commands:
   - `help`, `demo`, `stop`
   - `flight 0`
   - `msg HELLO`
   - `load`, `clear`

### Customization

- **Brightness**: Controls overall display brightness (0–255)
  - Edit `DISPLAY_BRIGHTNESS` in [UserConfiguration.h](firmware/config/UserConfiguration.h)
- **Text color**: RGB values used for all text/borders
  - Edit `TEXT_COLOR_R`, `TEXT_COLOR_G`, `TEXT_COLOR_B` in [UserConfiguration.h](firmware/config/UserConfiguration.h)

We may add more customization options in the future, but of course this being open source the whole thing is customizable to your liking.

# Thanks
We really appreciate all the support on this project!

If you don't want to build one but still find it cool, check out our offical displays: **[https://theflightwall.com](https://theflightwall.com)**

Excited to see your builds :) Tag @theflightwall on IG
