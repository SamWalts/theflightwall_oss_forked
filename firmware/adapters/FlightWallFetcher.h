#pragma once

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include "config/APIConfiguration.h"

class FlightWallFetcher
{
public:
    FlightWallFetcher() = default;
    ~FlightWallFetcher() = default;

    bool getAirlineName(const String &airlineIcao, String &outDisplayNameFull);

    bool getAircraftName(const String &aircraftIcao,
                         String &outDisplayNameShort,
                         String &outDisplayNameFull);

    bool getAircraftEnrichmentByAdsbIcao(const String &adsbIcao,
                                         String &outRegistration,
                                         String &outOperatorName,
                                         String &outOperatorIcao,
                                         String &outAircraftModel,
                                         String &outAircraftType,
                                         String &outSource,
                                         String &outUpdatedAt,
                                         bool &outFound);

private:
    bool httpGetJson(const String &url, String &outPayload);
};
