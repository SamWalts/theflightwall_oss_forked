// Standalone electrical/geometry diagnostic. No Wi-Fi or flight-data services.
// Keep the fused 5 V power design described in ../../../beginner-wiring-guide.md.
#include <Arduino.h>
#include <FastLED.h>
#include <FastLED_NeoMatrix.h>
#include <stdlib.h>

#ifndef FLIGHTWALL_TEST_PANELS
#define FLIGHTWALL_TEST_PANELS 1
#endif

static_assert(FLIGHTWALL_TEST_PANELS == 1 || FLIGHTWALL_TEST_PANELS == 4 ||
                  FLIGHTWALL_TEST_PANELS == 20,
              "Choose the panel1, panel4, or panel20 environment.");

static constexpr uint8_t kDataPin = 25;
static constexpr uint8_t kBrightness = 5;
static constexpr uint8_t kPanels = FLIGHTWALL_TEST_PANELS;
static constexpr uint16_t kPixelsPerPanel = 256;
static constexpr uint16_t kPixelCount = kPanels * kPixelsPerPanel;
static constexpr uint8_t kTilesX = kPanels == 1 ? 1 : kPanels / 2;
static constexpr uint8_t kTilesY = kPanels == 1 ? 1 : 2;
static constexpr uint16_t kWidth = kTilesX * 16;
static constexpr uint16_t kHeight = kTilesY * 16;

static CRGB leds[kPixelCount];
// Match production mapping. NEO_TILE_ZIGZAG rotates alternate tile columns
// by 180 degrees: see the front/back diagrams in the wiring guide.
static FastLED_NeoMatrix matrix(
    leds, 16, 16, kTilesX, kTilesY,
    NEO_MATRIX_BOTTOM + NEO_MATRIX_RIGHT + NEO_MATRIX_COLUMNS + NEO_MATRIX_ZIGZAG +
        NEO_TILE_TOP + NEO_TILE_RIGHT + NEO_TILE_COLUMNS + NEO_TILE_ZIGZAG);

static bool walking = false;
static uint8_t nextPanel = 0;
static unsigned long lastWalkMs = 0;
static String commandLine;
static bool discardLine = false;

static void clearPixels()
{
    fill_solid(leds, kPixelCount, CRGB::Black);
}

static void showPanel(uint8_t index)
{
    clearPixels();
    leds[index * kPixelsPerPanel] = CRGB::Red;
    FastLED.show();
    Serial.printf("First pixel of P%u\n", unsigned(index + 1));
}

static void printHelp()
{
    Serial.println("Commands (press Enter / send a newline):");
    Serial.println("  off | red | green | blue | white   (all at brightness 5)");
    Serial.println("  pixel N   one white pixel; zero-based index");
    Serial.println("  panel N   first pixel of panel; one-based number");
    Serial.println("  walk      visit each panel once per second; off stops it");
    Serial.println("  corners   TL red, TR green, BL blue, BR white (front view)");
    Serial.println("  border    dim white outline | help");
    Serial.println("off blanks LEDs; it does NOT disconnect electrical power.");
}

static bool readIndex(const String &value, unsigned long &result)
{
    if (value.length() == 0 || value[0] < '0' || value[0] > '9')
        return false;
    char *end = nullptr;
    result = strtoul(value.c_str(), &end, 10);
    return end != value.c_str() && *end == '\0';
}

static void handleCommand(String line)
{
    line.trim();
    if (line.length() == 0)
        return;
    if (line == "help")
    {
        printHelp();
        return;
    }

    walking = false;
    if (line == "walk")
    {
        walking = true;
        nextPanel = 0;
        lastWalkMs = millis() - 1000UL;
        return;
    }

    if (line.startsWith("pixel ") || line.startsWith("panel "))
    {
        const bool panel = line.startsWith("panel ");
        String value = line.substring(6);
        value.trim();
        unsigned long index = 0;
        if (!readIndex(value, index) ||
            (panel ? (index < 1 || index > kPanels) : index >= kPixelCount))
        {
            Serial.println("Index out of range. Type help.");
            return;
        }
        if (panel)
            showPanel(uint8_t(index - 1));
        else
        {
            clearPixels();
            leds[index] = CRGB::White;
            FastLED.show();
        }
        return;
    }

    clearPixels();
    if (line == "off")
    {
        // Keep the cleared buffer.
    }
    else if (line == "red")
        fill_solid(leds, kPixelCount, CRGB::Red);
    else if (line == "green")
        fill_solid(leds, kPixelCount, CRGB::Green);
    else if (line == "blue")
        fill_solid(leds, kPixelCount, CRGB::Blue);
    else if (line == "white")
        fill_solid(leds, kPixelCount, CRGB::White);
    else if (line == "corners")
    {
        matrix.drawPixel(0, 0, matrix.Color(255, 0, 0));
        matrix.drawPixel(kWidth - 1, 0, matrix.Color(0, 255, 0));
        matrix.drawPixel(0, kHeight - 1, matrix.Color(0, 0, 255));
        matrix.drawPixel(kWidth - 1, kHeight - 1, matrix.Color(255, 255, 255));
    }
    else if (line == "border")
        matrix.drawRect(0, 0, kWidth, kHeight, matrix.Color(255, 255, 255));
    else
        Serial.println("Unknown command. Display blanked. Type help.");
    FastLED.show();
}

void setup()
{
    Serial.begin(115200);
    delay(200);
    FastLED.addLeds<WS2812B, kDataPin, GRB>(leds, kPixelCount);
    FastLED.setBrightness(kBrightness);
    // Estimated 400 mA per panel: 8 A for twenty. Not a fuse substitute.
    FastLED.setMaxPowerInVoltsAndMilliamps(5, uint32_t(kPanels) * 400);
    clearPixels();
    FastLED.show();
    Serial.printf("FlightWall bench: %u panels, %ux%u, GPIO25, brightness 5\n",
                  unsigned(kPanels), unsigned(kWidth), unsigned(kHeight));
    printHelp();
}

void loop()
{
    while (Serial.available() > 0)
    {
        const char c = char(Serial.read());
        if (c == '\r')
            continue;
        if (c == '\n')
        {
            if (!discardLine)
                handleCommand(commandLine);
            commandLine = "";
            discardLine = false;
        }
        else if (!discardLine)
        {
            if (commandLine.length() < 48)
                commandLine += c;
            else
            {
                commandLine = "";
                discardLine = true;
                Serial.println("Command too long; send a newline then try again.");
            }
        }
    }
    if (walking && millis() - lastWalkMs >= 1000UL)
    {
        lastWalkMs = millis();
        showPanel(nextPanel);
        nextPanel = (nextPanel + 1) % kPanels;
    }
    delay(5);
}
