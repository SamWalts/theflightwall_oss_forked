/*
Purpose: Look up human-friendly airline and aircraft names from FlightWall CDN.
Responsibilities:
- HTTPS GET small JSON blobs for airline/aircraft codes and parse display names.
- Provide helpers used by FlightDataFetcher for user-facing labels.
Inputs: Airline ICAO code or aircraft ICAO type.
Outputs: Display name strings (short/full) via out parameters.
*/
#include "adapters/FlightWallFetcher.h"

bool FlightWallFetcher::httpGetJson(const String &url, String &outPayload)
{
    HTTPClient http;
    if (url.startsWith("https://"))
    {
        WiFiClientSecure client;
        if (APIConfiguration::FLIGHTWALL_INSECURE_TLS)
        {
            client.setInsecure();
        }
        if (!http.begin(client, url))
        {
            return false;
        }
    }
    else
    {
        if (!http.begin(url))
        {
            return false;
        }
    }
    http.addHeader("Accept", "application/json");

    int code = http.GET();
    if (code != 200)
    {
        http.end();
        return false;
    }
    outPayload = http.getString();
    http.end();
    return true;
}

bool FlightWallFetcher::getAirlineName(const String &airlineIcao, String &outDisplayNameFull)
{
    outDisplayNameFull = String("");
    if (airlineIcao.length() == 0)
        return false;

    String url = String(APIConfiguration::FLIGHTWALL_CDN_BASE_URL) + "/oss/lookup/airline/" + airlineIcao + ".json";
    String payload;
    if (!httpGetJson(url, payload))
        return false;

    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, payload);
    if (err)
        return false;

    if (doc.containsKey("display_name_full"))
    {
        outDisplayNameFull = String(doc["display_name_full"].as<const char *>());
        return outDisplayNameFull.length() > 0;
    }
    return false;
}

bool FlightWallFetcher::getAircraftName(const String &aircraftIcao,
                                        String &outDisplayNameShort,
                                        String &outDisplayNameFull)
{
    outDisplayNameShort = String("");
    outDisplayNameFull = String("");
    if (aircraftIcao.length() == 0)
        return false;

    String url = String(APIConfiguration::FLIGHTWALL_CDN_BASE_URL) + "/oss/lookup/aircraft/" + aircraftIcao + ".json";
    String payload;
    if (!httpGetJson(url, payload))
        return false;

    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, payload);
    if (err)
        return false;

    if (doc.containsKey("display_name_short"))
    {
        outDisplayNameShort = String(doc["display_name_short"].as<const char *>());
    }
    if (doc.containsKey("display_name_full"))
    {
        outDisplayNameFull = String(doc["display_name_full"].as<const char *>());
    }
    return outDisplayNameShort.length() > 0 || outDisplayNameFull.length() > 0;
}

static String safeGetString(JsonVariant v, const char *key)
{
    if (!v.containsKey(key) || v[key].isNull())
    {
        return String("");
    }
    return String(v[key].as<const char *>());
}

bool FlightWallFetcher::getAircraftEnrichmentByAdsbIcao(const String &adsbIcao,
                                                         String &outRegistration,
                                                         String &outOperatorName,
                                                         String &outOperatorIcao,
                                                         String &outAircraftModel,
                                                         String &outAircraftType,
                                                         String &outSource,
                                                         String &outUpdatedAt,
                                                         bool &outFound)
{
    outRegistration = String("");
    outOperatorName = String("");
    outOperatorIcao = String("");
    outAircraftModel = String("");
    outAircraftType = String("");
    outSource = String("");
    outUpdatedAt = String("");
    outFound = false;

    if (adsbIcao.length() == 0 || strlen(APIConfiguration::PI_ENRICHMENT_BASE_URL) == 0)
    {
        return false;
    }

    String normalized = adsbIcao;
    normalized.toUpperCase();

    String url = String(APIConfiguration::PI_ENRICHMENT_BASE_URL) + "/v1/aircraft/" + normalized;
    String payload;
    if (!httpGetJson(url, payload))
    {
        return false;
    }

    DynamicJsonDocument doc(1024);
    DeserializationError err = deserializeJson(doc, payload);
    if (err)
    {
        return false;
    }

    outFound = doc["found"] | false;
    outRegistration = safeGetString(doc, "registration");
    outOperatorName = safeGetString(doc, "operator_name");
    outOperatorIcao = safeGetString(doc, "operator_icao");
    outAircraftModel = safeGetString(doc, "aircraft_model");
    outAircraftType = safeGetString(doc, "aircraft_type");
    outSource = safeGetString(doc, "source");
    outUpdatedAt = safeGetString(doc, "updated_at");

    return true;
}
