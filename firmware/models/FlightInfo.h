#pragma once

#include <Arduino.h>
#include <vector>
#include "AirportInfo.h"

struct FlightInfo
{
    String adsb_icao;
    bool local_feed = false;
    bool on_ground = false;
    double altitude_baro_ft = NAN;
    double ground_speed_kt = NAN;
    double vertical_speed_fpm = NAN;

    // Flight identifiers
    String ident;
    String ident_icao;
    String ident_iata;

    // Operator
    String operator_code;
    String operator_icao;
    String operator_iata;

    // Route
    AirportInfo origin;
    AirportInfo destination;

    // Aircraft
    String aircraft_code;
    String registration;

    // Human-friendly display strings
    String airline_display_name_full;
    String aircraft_display_name_short;
    String aircraft_display_name_full;
    String enrichment_source;
    String enrichment_updated_at;

    // Airline branding
    String airline_logo_url;
};
