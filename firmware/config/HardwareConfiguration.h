#pragma once

#include <Arduino.h>

namespace HardwareConfiguration
{
    // Display configuration (FastLED NeoMatrix)
#if defined(WOKWI_DISPLAY_MOCK)
    static const uint8_t DISPLAY_PIN = 5; // Matches Wokwi diagram.json
#else
    static const uint8_t DISPLAY_PIN = 25; // Data pin
#endif

    // Physical tile size (pixels per 16x16 tile commonly)
    static const uint16_t DISPLAY_TILE_PIXEL_W = 16;
    static const uint16_t DISPLAY_TILE_PIXEL_H = 16;

    // Tile arrangement (number of tiles horizontally and vertically)
#if defined(WOKWI_DISPLAY_MOCK)
    static const uint8_t DISPLAY_TILES_X = 4; // 64px wide
    static const uint8_t DISPLAY_TILES_Y = 2; // 32px high
#else
    static const uint8_t DISPLAY_TILES_X = 10; // e.g., 10 tiles wide -> 160px
    static const uint8_t DISPLAY_TILES_Y = 2;  // e.g., 2 tiles high -> 32px
#endif

    // Derived matrix dimensions
    static const uint16_t DISPLAY_MATRIX_WIDTH = DISPLAY_TILE_PIXEL_W * DISPLAY_TILES_X;
    static const uint16_t DISPLAY_MATRIX_HEIGHT = DISPLAY_TILE_PIXEL_H * DISPLAY_TILES_Y;
}
