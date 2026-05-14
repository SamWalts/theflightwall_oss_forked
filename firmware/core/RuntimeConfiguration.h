#pragma once

#include <Arduino.h>

namespace RuntimeConfiguration
{
    void begin();

    const char *wifiSsid();
    const char *wifiPassword();
    const char *openSkyClientId();
    const char *openSkyClientSecret();
    const char *aeroApiKey();

    bool setByKey(const String &key, const String &value, String &error);
    bool getByKey(const String &key, String &value, String &error);
}
