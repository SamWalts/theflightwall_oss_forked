#pragma once

#include <Arduino.h>

namespace APIConfiguration
{
    // OpenSky API credentials
    static const char *OPENSKY_CLIENT_ID = "";
    static const char *OPENSKY_CLIENT_SECRET = "";
    static constexpr const char *OPENSKY_TOKEN_URL =
        "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token";

    static constexpr const char *OPENSKY_BASE_URL = "https://opensky-network.org";

    // FlightAware AeroAPI credentials
    static const char *AEROAPI_KEY = "";
    static constexpr const char *AEROAPI_BASE_URL = "https://aeroapi.flightaware.com/aeroapi";

    // FlightWall CDN lookup
    static constexpr const char *FLIGHTWALL_CDN_BASE_URL = "https://cdn.theflightwall.com";

    // Optional local Pi enrichment service (e.g. http://192.168.1.50:8080)
    static constexpr const char *PI_ENRICHMENT_BASE_URL = "";

    // Production flight source. Use the Pi LAN IP if .local resolution is unavailable.
    // No external fallback. BLE/NVS configuration will replace this compiled setting.
    static constexpr const char *RPI_BASE_URL = "http://raspberrypi.local:8080";

    // TLS behavior for external services
    static const bool AEROAPI_INSECURE_TLS = true;
    static const bool FLIGHTWALL_INSECURE_TLS = true;
}
