/*
Purpose: Render flight info on a WS2812B NeoPixel matrix via FastLED_NeoMatrix.
Responsibilities:
- Initialize LED matrix based on HardwareConfiguration and user display settings.
- Render a bordered, three-line flight “card” and a minimal loading screen.
- Cycle through multiple flights at a configurable interval.
Inputs: FlightInfo list; UserConfiguration (colors/brightness), TimingConfiguration (cycle),
        HardwareConfiguration (dimensions/pin/tiling).
Outputs: Visual output to LED matrix using FastLED.
*/
#include "adapters/NeoMatrixDisplay.h"

#include <ctype.h>
#include <Adafruit_GFX.h>
#include <FastLED_NeoMatrix.h>
#include <FastLED.h>
#include "config/UserConfiguration.h"
#include "config/HardwareConfiguration.h"
#include "config/TimingConfiguration.h"

NeoMatrixDisplay::NeoMatrixDisplay() {}

NeoMatrixDisplay::~NeoMatrixDisplay()
{
    if (_leds)
    {
        delete[] _leds;
        _leds = nullptr;
    }
    if (_matrix)
    {
        delete _matrix;
        _matrix = nullptr;
    }
}

bool NeoMatrixDisplay::initialize()
{
    _matrixWidth = HardwareConfiguration::DISPLAY_MATRIX_WIDTH;
    _matrixHeight = HardwareConfiguration::DISPLAY_MATRIX_HEIGHT;
    _numPixels = (uint32_t)_matrixWidth * (uint32_t)_matrixHeight;

    _leds = new CRGB[_numPixels];

    _matrix = new FastLED_NeoMatrix(
        _leds,
        HardwareConfiguration::DISPLAY_TILE_PIXEL_W,
        HardwareConfiguration::DISPLAY_TILE_PIXEL_H,
        HardwareConfiguration::DISPLAY_TILES_X,
        HardwareConfiguration::DISPLAY_TILES_Y,
        NEO_MATRIX_BOTTOM + NEO_MATRIX_RIGHT +
            NEO_MATRIX_COLUMNS + NEO_MATRIX_ZIGZAG +
            NEO_TILE_TOP + NEO_TILE_RIGHT + NEO_TILE_COLUMNS + NEO_TILE_ZIGZAG);

    FastLED.addLeds<WS2812B, HardwareConfiguration::DISPLAY_PIN, GRB>(_leds, _numPixels);
    _matrix->setTextWrap(false);
    _matrix->setTextSize(1);
    _matrix->setBrightness(UserConfiguration::DISPLAY_BRIGHTNESS);
    clear();
    _currentFlightIndex = 0;
    _lastCycleMs = millis();
    return true;
}

void NeoMatrixDisplay::clear()
{
    if (_matrix)
    {
        _matrix->fillScreen(0);
        FastLED.show();
    }
}

String NeoMatrixDisplay::makeFlightLine(const FlightInfo &f)
{
    String airline = f.airline_display_name_full.length() ? f.airline_display_name_full
                                                          : (f.operator_iata.length() ? f.operator_iata : f.operator_icao);
    if (airline.length() == 0)
    {
        airline = f.operator_code;
    }
    String origin = f.origin.code_icao;
    String dest = f.destination.code_icao;
    String route = origin + "-" + dest;
    String type = f.aircraft_display_name_short.length() ? f.aircraft_display_name_short : f.aircraft_code;
    String ident = f.ident.length() ? f.ident : f.ident_icao;
    String line = airline;
    if (ident.length())
    {
        line += " ";
        line += ident;
    }
    if (type.length())
    {
        line += " ";
        line += type;
    }
    if (route.length() > 1)
    {
        line += " ";
        line += route;
    }
    return line;
}

void NeoMatrixDisplay::drawTextLine(int16_t x, int16_t y, const String &text, uint16_t color)
{
    _matrix->setCursor(x, y);
    _matrix->setTextColor(color);
    for (size_t i = 0; i < (size_t)text.length(); ++i)
    {
        _matrix->write(text[i]);
    }
}

String NeoMatrixDisplay::truncateToColumns(const String &text, int maxColumns)
{
    if ((int)text.length() <= maxColumns)
        return text;
    if (maxColumns <= 3)
        return text.substring(0, maxColumns);
    return text.substring(0, maxColumns - 3) + String("...");
}

String NeoMatrixDisplay::makeAirlineLogoBadgeText(const FlightInfo &f)
{
    String badge = f.operator_iata.length() ? f.operator_iata
                                            : (f.operator_icao.length() ? f.operator_icao : f.operator_code);
    badge.trim();
    badge.toUpperCase();

    if (badge.length() == 0)
    {
        for (size_t i = 0; i < f.airline_display_name_full.length() && badge.length() < 3; ++i)
        {
            char c = f.airline_display_name_full[i];
            if (isalpha((unsigned char)c))
            {
                badge += (char)toupper((unsigned char)c);
            }
        }
    }

    if (badge.length() == 0)
    {
        badge = String("AIR");
    }
    if (badge.length() > 3)
    {
        badge = badge.substring(0, 3);
    }
    return badge;
}

void NeoMatrixDisplay::displaySingleFlightCard(const FlightInfo &f)
{
    // Border
    const uint16_t borderColor = _matrix->Color(UserConfiguration::TEXT_COLOR_R,
                                                UserConfiguration::TEXT_COLOR_G,
                                                UserConfiguration::TEXT_COLOR_B);
    _matrix->drawRect(0, 0, _matrixWidth, _matrixHeight, borderColor);

    // Calculate columns for 6x8 default font (5x7 glyphs + 1px spacing)
    const int charWidth = 6;
    const int charHeight = 8;
    const int padding = 2;                                   // Small padding from border
    const int innerWidth = _matrixWidth - 2 - (2 * padding); // Account for border and padding
    const int innerHeight = _matrixHeight - 2 - (2 * padding);
    const int maxCols = innerWidth / charWidth;
    const bool hasAirlineLogo = f.airline_logo_url.length() > 0;
    const int logoBadgeWidth = 22;

    // Lines per display:
    // 1: airline
    // 2: route
    // 3: aircraft

    String airline = f.airline_display_name_full.length() ? f.airline_display_name_full
                                                          : (f.operator_iata.length() ? f.operator_iata : (f.operator_icao.length() ? f.operator_icao : f.operator_code));

    String origin = f.origin.code_icao;
    String dest = f.destination.code_icao;
    String line2 = origin + String(">") + dest;

    String line3 = f.aircraft_display_name_short.length() ? f.aircraft_display_name_short : f.aircraft_code;

    int line1MaxCols = maxCols;
    if (hasAirlineLogo)
    {
        const int logoBadgeColumnPadding = 1;
        const int reservedCols = (logoBadgeWidth / charWidth) + logoBadgeColumnPadding;
        line1MaxCols = maxCols - reservedCols;
        if (line1MaxCols < 3)
        {
            line1MaxCols = 3;
        }
    }

    String line1 = truncateToColumns(airline, line1MaxCols);
    line2 = truncateToColumns(line2, maxCols);
    line3 = truncateToColumns(line3, maxCols);

    const uint16_t textColor = _matrix->Color(UserConfiguration::TEXT_COLOR_R,
                                              UserConfiguration::TEXT_COLOR_G,
                                              UserConfiguration::TEXT_COLOR_B);
    const int lineCount = 3;
    const int lineSpacing = 1; // 1px spacing between lines
    const int totalTextHeight = lineCount * charHeight + (lineCount - 1) * lineSpacing;
    const int topOffset = 1 + padding + (innerHeight - totalTextHeight) / 2; // center inside border with padding
    const int16_t startX = 1 + padding;                                      // left padding inside border

    int16_t y = topOffset;
    drawTextLine(startX, y, line1, textColor);
    y += charHeight + lineSpacing;
    drawTextLine(startX, y, line2, textColor);
    y += charHeight + lineSpacing;
    drawTextLine(startX, y, line3, textColor);

    if (hasAirlineLogo)
    {
        const int badgeHeight = charHeight + 2;
        const int badgeX = _matrixWidth - 1 - padding - logoBadgeWidth;
        const int badgeY = 1 + padding;
        _matrix->drawRect(badgeX, badgeY, logoBadgeWidth, badgeHeight, textColor);
        drawTextLine(badgeX + 2, badgeY + 1, makeAirlineLogoBadgeText(f), textColor);
    }
}

void NeoMatrixDisplay::displayFlights(const std::vector<FlightInfo> &flights)
{
    if (_matrix == nullptr)
        return;

    _matrix->fillScreen(0);

    if (!flights.empty())
    {
        const unsigned long now = millis();
        const unsigned long intervalMs = TimingConfiguration::DISPLAY_CYCLE_SECONDS * 1000UL;

        if (flights.size() > 1)
        {
            if (now - _lastCycleMs >= intervalMs)
            {
                _lastCycleMs = now;
                _currentFlightIndex = (_currentFlightIndex + 1) % flights.size();
            }
        }
        else
        {
            _currentFlightIndex = 0;
        }

        const size_t index = _currentFlightIndex % flights.size();
        displaySingleFlightCard(flights[index]);
    }
    else
    {
        displayLoadingScreen();
    }

    FastLED.show();
}

void NeoMatrixDisplay::displayLoadingScreen()
{
    if (_matrix == nullptr)
        return;

    _matrix->fillScreen(0);

    const uint16_t borderColor = _matrix->Color(255, 255, 255);
    _matrix->drawRect(0, 0, _matrixWidth, _matrixHeight, borderColor);

    const int charWidth = 6;
    const int charHeight = 8;
    const String loadingText = "...";
    const int textWidth = loadingText.length() * charWidth;

    const int16_t x = (_matrixWidth - textWidth) / 2;
    const int16_t y = (_matrixHeight - charHeight) / 2 - 2;

    const uint16_t textColor = _matrix->Color(UserConfiguration::TEXT_COLOR_R,
                                              UserConfiguration::TEXT_COLOR_G,
                                              UserConfiguration::TEXT_COLOR_B);
    drawTextLine(x, y, loadingText, textColor);

    FastLED.show();
}

void NeoMatrixDisplay::displayMessage(const String &message)
{
    if (_matrix == nullptr)
        return;

    _matrix->fillScreen(0);

    const int charWidth = 6;
    const int charHeight = 6;

    const uint16_t textColor = _matrix->Color(UserConfiguration::TEXT_COLOR_R,
                                              UserConfiguration::TEXT_COLOR_G,
                                              UserConfiguration::TEXT_COLOR_B);

    // Simple single-line message; truncate if needed
    const int innerWidth = _matrixWidth;
    const int maxCols = innerWidth / charWidth;
    String line = truncateToColumns(message, maxCols);

    const int16_t x = 0;
    const int16_t y = (_matrixHeight - charHeight) / 2;
    drawTextLine(x, y, line, textColor);
    FastLED.show();
}

void NeoMatrixDisplay::showLoading()
{
    displayLoadingScreen();
}
