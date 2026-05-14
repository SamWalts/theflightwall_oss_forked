/*
Purpose: Firmware entry point for ESP32.
Responsibilities:
- Initialize serial, connect to Wi‑Fi, and construct fetchers and display.
- Periodically fetch state vectors (OpenSky), enrich flights (AeroAPI), and render.
Configuration: UserConfiguration (location/filters/colors), TimingConfiguration (intervals),
               WiFiConfiguration (SSID/password), HardwareConfiguration (display specs).
*/
#include <vector>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include "config/UserConfiguration.h"
#include "config/WiFiConfiguration.h"
#include "config/TimingConfiguration.h"
#include "adapters/OpenSkyFetcher.h"
#include "adapters/AeroAPIFetcher.h"
#include "core/FlightDataFetcher.h"
#include "core/BluetoothConfigService.h"
#include "core/RuntimeConfiguration.h"
#include "adapters/NeoMatrixDisplay.h"

static OpenSkyFetcher g_openSky;
static AeroAPIFetcher g_aeroApi;
static FlightDataFetcher *g_fetcher = nullptr;
static NeoMatrixDisplay g_display;
static BluetoothConfigService g_bluetoothConfig;

static unsigned long g_lastFetchMs = 0;

void setup()
{
    Serial.begin(115200);
    delay(200);
    RuntimeConfiguration::begin();
    g_bluetoothConfig.begin();

    g_display.initialize();
    g_display.displayMessage(String("FlightWall"));

    if (strlen(RuntimeConfiguration::wifiSsid()) > 0)
    {
        WiFi.mode(WIFI_STA);
        g_display.displayMessage(String("WiFi: ") + RuntimeConfiguration::wifiSsid());
        WiFi.begin(RuntimeConfiguration::wifiSsid(), RuntimeConfiguration::wifiPassword());
        Serial.print("Connecting to WiFi");
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 50)
        {
            delay(200);
            Serial.print(".");
            attempts++;
        }
        Serial.println();
        if (WiFi.status() == WL_CONNECTED)
        {
            Serial.print("WiFi connected: ");
            Serial.println(WiFi.localIP());
            g_display.displayMessage(String("WiFi OK ") + WiFi.localIP().toString());
            delay(3000);
            g_display.showLoading();
        }
        else
        {
            Serial.println("WiFi not connected; proceeding without network");
            g_display.displayMessage(String("WiFi FAIL"));
        }
    }

    g_fetcher = new FlightDataFetcher(&g_openSky, &g_aeroApi);
}

void loop()
{
    g_bluetoothConfig.loop();

    const unsigned long intervalMs = TimingConfiguration::FETCH_INTERVAL_SECONDS * 1000UL;
    const unsigned long now = millis();
    if (now - g_lastFetchMs >= intervalMs)
    {
        g_lastFetchMs = now;

        std::vector<StateVector> states;
        std::vector<FlightInfo> flights;
        size_t enriched = g_fetcher->fetchFlights(states, flights);

        Serial.print("OpenSky state vectors: ");
        Serial.println((int)states.size());
        Serial.print("AeroAPI enriched flights: ");
        Serial.println((int)enriched);

        for (const auto &s : states)
        {
            Serial.print(" ");
            Serial.print(s.callsign);
            Serial.print(" @ ");
            Serial.print(s.distance_km, 1);
            Serial.print("km bearing ");
            Serial.println(s.bearing_deg, 1);
        }

        for (const auto &f : flights)
        {
            Serial.println("=== FLIGHT INFO ===");
            Serial.print("Ident: ");
            Serial.println(f.ident);
            Serial.print("Ident ICAO: ");
            Serial.println(f.ident_icao);
            Serial.print("Ident IATA: ");
            Serial.println(f.ident_iata);
            Serial.print("Airline: ");
            Serial.println(f.airline_display_name_full);
            Serial.print("Aircraft: ");
            Serial.println(f.aircraft_display_name_short.length() ? f.aircraft_display_name_short : f.aircraft_code);
            Serial.print("Operator Code: ");
            Serial.println(f.operator_code);
            Serial.print("Operator ICAO: ");
            Serial.println(f.operator_icao);
            Serial.print("Operator IATA: ");
            Serial.println(f.operator_iata);

            Serial.println("--- Origin ---");
            Serial.print("Code ICAO: ");
            Serial.println(f.origin.code_icao);

            Serial.println("--- Destination ---");
            Serial.print("Code ICAO: ");
            Serial.println(f.destination.code_icao);
            Serial.println("===================");
        }

        g_display.displayFlights(flights);
    }
    delay(10);
}
