#pragma once

#include <Arduino.h>

namespace TimingConfiguration
{
    // Poll the local Pi; receiver freshness is checked by the service.
    static const uint32_t FETCH_INTERVAL_SECONDS = 2; // seconds

    // Display cycling configuration
    static const uint32_t DISPLAY_CYCLE_SECONDS = 3; // seconds per flight when multiple flights
}
