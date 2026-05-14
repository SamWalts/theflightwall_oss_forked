#pragma once

#include <Arduino.h>

namespace APIConfiguration
{
    // OpenSky API credentials
    static constexpr const char *DEFAULT_OPENSKY_CLIENT_ID = "";
    static constexpr const char *DEFAULT_OPENSKY_CLIENT_SECRET = "";
    static constexpr const char *OPENSKY_CLIENT_ID = DEFAULT_OPENSKY_CLIENT_ID;
    static constexpr const char *OPENSKY_CLIENT_SECRET = DEFAULT_OPENSKY_CLIENT_SECRET;
    static constexpr const char *OPENSKY_TOKEN_URL =
        "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token";

    static constexpr const char *OPENSKY_BASE_URL = "https://opensky-network.org";

    // FlightAware AeroAPI credentials
    static constexpr const char *DEFAULT_AEROAPI_KEY = "";
    static constexpr const char *AEROAPI_KEY = DEFAULT_AEROAPI_KEY;
    static constexpr const char *AEROAPI_BASE_URL = "https://aeroapi.flightaware.com/aeroapi";

    // FlightWall CDN lookup
    static constexpr const char *FLIGHTWALL_CDN_BASE_URL = "https://cdn.theflightwall.com";

    // TLS behavior for external services
    static const bool AEROAPI_INSECURE_TLS = true;
    static const bool FLIGHTWALL_INSECURE_TLS = true;
}
