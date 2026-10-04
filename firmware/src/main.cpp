/*
Purpose: Firmware entry point for ESP32.
Responsibilities:
- Initialize serial, connect to Wi‑Fi, and construct fetchers and display.
- Fetch local readsb flights from the Pi and render.
Configuration: UserConfiguration (location/filters/colors), TimingConfiguration (intervals),
               WiFiConfiguration (SSID/password), HardwareConfiguration (display specs).
*/
#include <vector>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <stdlib.h>
#include "config/UserConfiguration.h"
#include "config/WiFiConfiguration.h"
#include "config/TimingConfiguration.h"
#include "adapters/PiFlightFeed.h"
#include "adapters/NeoMatrixDisplay.h"

static PiFlightFeed g_feed;
static std::vector<FlightInfo> g_flights;
static NeoMatrixDisplay g_display;

static unsigned long g_lastFetchMs = 0;

#if defined(WOKWI_DISPLAY_MOCK)
static std::vector<FlightInfo> g_mockFlights;
static String g_mockLineBuffer;
static bool g_mockAutoCycle = false;
static size_t g_mockSelectedFlightIndex = 0;

static FlightInfo makeMockFlight(const char *airline, const char *ident, const char *origin, const char *dest, const char *aircraft, bool withLogo)
{
    FlightInfo f;
    f.airline_display_name_full = airline;
    f.ident = ident;
    f.origin.code_icao = origin;
    f.destination.code_icao = dest;
    f.aircraft_display_name_short = aircraft;
    f.airline_logo_url = withLogo ? "https://cdn.theflightwall.com/mock/logo.png" : "";
    return f;
}

static void loadMockFlights()
{
    g_mockFlights.clear();
    g_mockFlights.push_back(makeMockFlight("Delta Air Lines", "DL1184", "KATL", "KLAX", "A321", true));
    g_mockFlights.push_back(makeMockFlight("United Airlines", "UA932", "KEWR", "EGLL", "B767", false));
    g_mockFlights.push_back(makeMockFlight("American Airlines", "AA22", "KJFK", "KLAX", "A321", true));
}

static void showMockHelp()
{
    Serial.println("Wokwi display mock commands:");
    Serial.println("  help               - show commands");
    Serial.println("  demo               - auto-cycle demo flights");
    Serial.println("  stop               - stop auto-cycle");
    Serial.println("  flight <index>     - render a single flight (0-based)");
    Serial.println("  msg <text>         - show a text message");
    Serial.println("  load               - show loading screen");
    Serial.println("  clear              - clear display");
}

static void renderMockFlight(size_t index)
{
    if (g_mockFlights.empty())
    {
        g_display.showLoading();
        return;
    }
    g_mockSelectedFlightIndex = index % g_mockFlights.size();
    std::vector<FlightInfo> single;
    single.push_back(g_mockFlights[g_mockSelectedFlightIndex]);
    g_display.displayFlights(single);
}

static void handleMockCommand(const String &line)
{
    String cmd = line;
    cmd.trim();
    if (cmd.length() == 0)
    {
        return;
    }

    if (cmd == "help")
    {
        showMockHelp();
        return;
    }

    if (cmd == "demo")
    {
        g_mockAutoCycle = true;
        Serial.println("Mock demo enabled");
        return;
    }

    if (cmd == "stop")
    {
        g_mockAutoCycle = false;
        Serial.println("Mock demo stopped");
        return;
    }

    if (cmd == "load")
    {
        g_mockAutoCycle = false;
        g_display.showLoading();
        Serial.println("Rendered loading screen");
        return;
    }

    if (cmd == "clear")
    {
        g_mockAutoCycle = false;
        g_display.clear();
        Serial.println("Display cleared");
        return;
    }

    if (cmd.startsWith("msg "))
    {
        g_mockAutoCycle = false;
        g_display.displayMessage(cmd.substring(4));
        Serial.println("Rendered message");
        return;
    }

    if (cmd.startsWith("flight "))
    {
        g_mockAutoCycle = false;
        const long index = strtol(cmd.substring(7).c_str(), nullptr, 10);
        if (index < 0)
        {
            Serial.println("flight index must be >= 0");
            return;
        }
        renderMockFlight((size_t)index);
        Serial.println("Rendered flight index");
        return;
    }

    Serial.println("Unknown command. Type 'help'.");
}

static void pollMockCommands()
{
    while (Serial.available() > 0)
    {
        const char c = (char)Serial.read();
        if (c == '\r')
        {
            continue;
        }
        if (c == '\n')
        {
            handleMockCommand(g_mockLineBuffer);
            g_mockLineBuffer = "";
            continue;
        }
        g_mockLineBuffer += c;
    }
}
#endif

void setup()
{
    Serial.begin(115200);
    delay(200);

    g_display.initialize();
    g_display.displayMessage(String("FlightWall"));

#if defined(WOKWI_DISPLAY_MOCK)
    loadMockFlights();
    renderMockFlight(0);
    showMockHelp();
    Serial.println("Type commands in the Wokwi serial monitor.");
    return;
#endif

    if (strlen(WiFiConfiguration::WIFI_SSID) > 0)
    {
        WiFi.mode(WIFI_STA);
        g_display.displayMessage(String("WiFi: ") + WiFiConfiguration::WIFI_SSID);
        WiFi.begin(WiFiConfiguration::WIFI_SSID, WiFiConfiguration::WIFI_PASSWORD);
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

    // Live operation uses only the configured local Pi.
}

void loop()
{
#if defined(WOKWI_DISPLAY_MOCK)
    pollMockCommands();
    if (g_mockAutoCycle)
    {
        g_display.displayFlights(g_mockFlights);
    }
    delay(10);
    return;
#endif

    const unsigned long intervalMs = TimingConfiguration::FETCH_INTERVAL_SECONDS * 1000UL;
    const unsigned long now = millis();
    if (WiFi.status() != WL_CONNECTED)
    {
        g_flights.clear();
        g_display.displayMessage("WiFi disconnected");
        delay(10);
        return;
    }
    if (g_lastFetchMs == 0 || now - g_lastFetchMs >= intervalMs)
    {
        g_lastFetchMs = now;
        g_feed.fetchFlights(g_flights);
        Serial.print("Local Pi flights: ");
        Serial.println((int)g_flights.size());
    }
    if (g_feed.status() == PiFlightFeed::Status::Stale)
        g_display.displayMessage("Receiver stale");
    else if (g_feed.status() == PiFlightFeed::Status::Unavailable)
        g_display.displayMessage("Pi unavailable");
    else if (g_flights.empty())
        g_display.displayMessage("No aircraft");
    else
        g_display.displayFlights(g_flights);
    delay(10);
}
