#pragma once

#include <stdint.h>

namespace BluetoothConfiguration
{
    static constexpr bool ENABLED = true;
    static constexpr const char *DEVICE_NAME = "FlightWall-Setup";
    // Change this before production deployment.
    static constexpr const char *PAIRING_PIN = "4913";
    static constexpr uint8_t PAIRING_PIN_LENGTH = 4;
}
