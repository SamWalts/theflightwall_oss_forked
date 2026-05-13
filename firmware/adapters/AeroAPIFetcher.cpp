/*
Purpose: Retrieve detailed flight metadata from AeroAPI over HTTPS.
Responsibilities:
- Perform authenticated GET to /flights/{ident} using API key.
- Parse minimal fields into FlightInfo (ident/operator/aircraft and ICAO codes).
- Handle TLS (optionally insecure for dev) and JSON errors gracefully.
Input: flight ident (e.g., callsign).
Output: Populates FlightInfo on success and returns true.
*/
#include "adapters/AeroAPIFetcher.h"

static String safeGetString(JsonVariantConst objectVariant, const char *key)
{
    if (!objectVariant.is<JsonObjectConst>())
        return String("");

    JsonObjectConst object = objectVariant.as<JsonObjectConst>();
    JsonVariantConst value = object[key];
    if (value.isNull())
        return String("");

    const char *asCStr = value.as<const char *>();
    if (asCStr == nullptr)
        return String("");

    return String(asCStr);
}

static String safeGetNestedString(JsonVariantConst objectVariant, const char *nestedObjectKey, const char *key)
{
    if (!objectVariant.is<JsonObjectConst>())
        return String("");

    JsonObjectConst object = objectVariant.as<JsonObjectConst>();
    JsonVariantConst nestedVariant = object[nestedObjectKey];
    if (!nestedVariant.is<JsonObjectConst>())
        return String("");

    return safeGetString(nestedVariant, key);
}

bool AeroAPIFetcher::fetchFlightInfo(const String &flightIdent, FlightInfo &outInfo)
{
    if (strlen(APIConfiguration::AEROAPI_KEY) == 0)
    {
        Serial.println("AeroAPIFetcher: No API key configured");
        return false;
    }

    WiFiClientSecure client;
    if (APIConfiguration::AEROAPI_INSECURE_TLS)
    {
        client.setInsecure();
    }

    HTTPClient http;
    String url = String(APIConfiguration::AEROAPI_BASE_URL) + "/flights/" + flightIdent;
    http.begin(client, url);
    http.addHeader("x-apikey", APIConfiguration::AEROAPI_KEY);
    http.addHeader("Accept", "application/json");

    int code = http.GET();
    if (code != 200)
    {
        Serial.printf("AeroAPIFetcher: HTTP request failed with code %d for flight %s\n", code, flightIdent.c_str());
        http.end();
        return false;
    }

    String payload = http.getString();
    http.end();

    DynamicJsonDocument doc(16384);
    DeserializationError err = deserializeJson(doc, payload);
    if (err)
    {
        Serial.printf("AeroAPIFetcher: JSON parsing failed for flight %s: %s\n", flightIdent.c_str(), err.c_str());
        return false;
    }

    JsonArray flights = doc["flights"].as<JsonArray>();
    if (flights.isNull() || flights.size() == 0)
    {
        Serial.printf("AeroAPIFetcher: No flights found in response for %s\n", flightIdent.c_str());
        return false;
    }

    JsonObject f = flights[0].as<JsonObject>();
    outInfo.ident = safeGetString(f, "ident");
    outInfo.ident_icao = safeGetString(f, "ident_icao");
    outInfo.ident_iata = safeGetString(f, "ident_iata");
    if (f["operator"].is<const char *>())
    {
        outInfo.operator_code = String(f["operator"].as<const char *>());
    }
    else
    {
        outInfo.operator_code = safeGetNestedString(f, "operator", "code");
    }
    outInfo.operator_icao = safeGetString(f, "operator_icao");
    outInfo.operator_iata = safeGetString(f, "operator_iata");
    outInfo.aircraft_code = safeGetString(f, "aircraft_type");
    outInfo.airline_logo_url = safeGetString(f, "operator_logo_url");
    if (outInfo.airline_logo_url.length() == 0)
    {
        outInfo.airline_logo_url = safeGetString(f, "airline_logo_url");
    }
    if (outInfo.airline_logo_url.length() == 0)
    {
        outInfo.airline_logo_url = safeGetString(f, "logo_url");
    }
    if (outInfo.airline_logo_url.length() == 0)
    {
        outInfo.airline_logo_url = safeGetNestedString(f, "operator", "logo_url");
    }
    if (outInfo.airline_logo_url.length() == 0)
    {
        outInfo.airline_logo_url = safeGetNestedString(f, "operator", "logo");
    }
    if (outInfo.airline_logo_url.length() == 0)
    {
        outInfo.airline_logo_url = safeGetNestedString(f, "airline", "logo_url");
    }

    if (f.containsKey("origin") && f["origin"].is<JsonObject>())
    {
        JsonObject o = f["origin"].as<JsonObject>();
        outInfo.origin.code_icao = safeGetString(o, "code_icao");
    }

    if (f.containsKey("destination") && f["destination"].is<JsonObject>())
    {
        JsonObject d = f["destination"].as<JsonObject>();
        outInfo.destination.code_icao = safeGetString(d, "code_icao");
    }

    return true;
}
