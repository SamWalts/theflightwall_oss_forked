#include "adapters/PiFlightFeed.h"
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include "config/APIConfiguration.h"

bool PiFlightFeed::fetchFlights(std::vector<FlightInfo> &flights)
{
    flights.clear();
    _status = Status::Unavailable;
    if (WiFi.status() != WL_CONNECTED)
        return false;
    HTTPClient http;
    http.setConnectTimeout(1000);
    http.setTimeout(2000);
    // Redirects remain disabled; the local feed has no cloud fallback.
    if (!http.begin(String(APIConfiguration::RPI_BASE_URL) + "/v1/flights"))
        return false;
    const int code = http.GET();
    const int length = http.getSize();
    if (code != HTTP_CODE_OK || length <= 0 || length > 16384)
    {
        http.end();
        return false;
    }
    // Content-Length is required by our Pi API. Allocate only the bounded body.
    String body;
    if (!body.reserve(length))
    {
        http.end();
        return false;
    }
    auto *stream = http.getStreamPtr();
    const unsigned long started = millis();
    while (body.length() < (size_t)length && millis() - started < 2000)
    {
        while (stream->available() && body.length() < (size_t)length)
            body += (char)stream->read();
        delay(1);
    }
    http.end();
    if (body.length() != (size_t)length)
        return false;
    JsonDocument doc;
    if (deserializeJson(doc, body, DeserializationOption::NestingLimit(6)))
        return false;
    if ((doc["schema_version"] | 0) != 1)
        return false;
    String receiverStatus = doc["receiver_status"] | "";
    if (receiverStatus == "stale")
    {
        _status = Status::Stale;
        return false;
    }
    if (receiverStatus != "ok" || !doc["flights"].is<JsonArray>())
        return false;
    JsonArray records = doc["flights"].as<JsonArray>();
    if (records.size() > 8)
        return false;
    for (JsonObject record : records)
    {
        FlightInfo info;
        info.adsb_icao = record["adsb_icao"] | "";
        if (info.adsb_icao.length() != 6)
            continue;
        info.ident_icao = record["callsign"] | "";
        info.ident = info.ident_icao.length() ? info.ident_icao : info.adsb_icao;
        info.registration = record["registration"] | "";
        info.aircraft_code = record["aircraft_type"] | "";
        info.aircraft_display_name_short = record["aircraft_model"] | "";
        info.enrichment_source = record["aircraft_reference_source"] | "";
        info.operator_icao = record["operator_icao"] | "";
        info.airline_display_name_full = record["operator_name"] | "";
        info.altitude_baro_ft = record["altitude_baro_ft"].isNull() ? NAN : record["altitude_baro_ft"].as<double>();
        info.ground_speed_kt = record["ground_speed_kt"].isNull() ? NAN : record["ground_speed_kt"].as<double>();
        info.vertical_speed_fpm = record["vertical_speed_fpm"].isNull() ? NAN : record["vertical_speed_fpm"].as<double>();
        info.on_ground = record["on_ground"] | false;
        info.local_feed = true;
        flights.push_back(info);
    }
    _status = Status::Ok;
    return true;
}
