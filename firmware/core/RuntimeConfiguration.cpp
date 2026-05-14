#include "core/RuntimeConfiguration.h"

#include <Preferences.h>
#include <string.h>
#include "config/APIConfiguration.h"
#include "config/WiFiConfiguration.h"

namespace RuntimeConfiguration
{
    namespace
    {
        static Preferences g_preferences;
        static bool g_ready = false;
        static bool g_storageAvailable = false;

        static char g_wifiSsid[65];
        static char g_wifiPassword[65];
        static char g_openSkyClientId[129];
        static char g_openSkyClientSecret[129];
        static char g_aeroApiKey[129];

        static void copyValue(char *dest, size_t destSize, const String &value)
        {
            if (destSize == 0)
                return;
            snprintf(dest, destSize, "%s", value.c_str());
        }

        static void loadValue(const char *key, const char *fallback, char *dest, size_t destSize)
        {
            String value = g_preferences.getString(key, fallback);
            copyValue(dest, destSize, value);
        }

        static bool putValue(const char *key, const String &value, char *dest, size_t destSize)
        {
            const size_t stored = g_preferences.putString(key, value);
            if (stored != value.length())
            {
                return false;
            }
            copyValue(dest, destSize, value);
            return true;
        }

        static String normalizedKey(const String &key)
        {
            String out = key;
            out.trim();
            out.toUpperCase();
            return out;
        }
    }

    void begin()
    {
        if (g_ready)
        {
            return;
        }

        if (!g_preferences.begin("flightcfg", false))
        {
            copyValue(g_wifiSsid, sizeof(g_wifiSsid), WiFiConfiguration::DEFAULT_WIFI_SSID);
            copyValue(g_wifiPassword, sizeof(g_wifiPassword), WiFiConfiguration::DEFAULT_WIFI_PASSWORD);
            copyValue(g_openSkyClientId, sizeof(g_openSkyClientId), APIConfiguration::DEFAULT_OPENSKY_CLIENT_ID);
            copyValue(g_openSkyClientSecret, sizeof(g_openSkyClientSecret), APIConfiguration::DEFAULT_OPENSKY_CLIENT_SECRET);
            copyValue(g_aeroApiKey, sizeof(g_aeroApiKey), APIConfiguration::DEFAULT_AEROAPI_KEY);
            g_ready = true;
            return;
        }

        g_storageAvailable = true;

        loadValue("wifi_ssid", WiFiConfiguration::DEFAULT_WIFI_SSID, g_wifiSsid, sizeof(g_wifiSsid));
        loadValue("wifi_password", WiFiConfiguration::DEFAULT_WIFI_PASSWORD, g_wifiPassword, sizeof(g_wifiPassword));
        loadValue("opensky_client_id", APIConfiguration::DEFAULT_OPENSKY_CLIENT_ID, g_openSkyClientId, sizeof(g_openSkyClientId));
        loadValue("opensky_client_secret", APIConfiguration::DEFAULT_OPENSKY_CLIENT_SECRET, g_openSkyClientSecret, sizeof(g_openSkyClientSecret));
        loadValue("aeroapi_key", APIConfiguration::DEFAULT_AEROAPI_KEY, g_aeroApiKey, sizeof(g_aeroApiKey));

        g_ready = true;
    }

    const char *wifiSsid()
    {
        return g_wifiSsid;
    }

    const char *wifiPassword()
    {
        return g_wifiPassword;
    }

    const char *openSkyClientId()
    {
        return g_openSkyClientId;
    }

    const char *openSkyClientSecret()
    {
        return g_openSkyClientSecret;
    }

    const char *aeroApiKey()
    {
        return g_aeroApiKey;
    }

    bool setByKey(const String &key, const String &value, String &error)
    {
        if (!g_ready)
        {
            error = "NOT_READY";
            return false;
        }

        String normalized = normalizedKey(key);

        if (!g_storageAvailable)
        {
            error = "NVS_UNAVAILABLE";
            return false;
        }

        if (normalized == "WIFI_SSID" || normalized == "NETWORK_ID")
        {
            if (value.length() > sizeof(g_wifiSsid) - 1)
            {
                error = "VALUE_TOO_LONG_MAX_64";
                return false;
            }
            if (!putValue("wifi_ssid", value, g_wifiSsid, sizeof(g_wifiSsid)))
            {
                error = "WRITE_FAILED";
                return false;
            }
            return true;
        }

        if (normalized == "WIFI_PASSWORD")
        {
            if (value.length() > sizeof(g_wifiPassword) - 1)
            {
                error = "VALUE_TOO_LONG_MAX_64";
                return false;
            }
            if (!putValue("wifi_password", value, g_wifiPassword, sizeof(g_wifiPassword)))
            {
                error = "WRITE_FAILED";
                return false;
            }
            return true;
        }

        if (normalized == "OPENSKY_CLIENT_ID")
        {
            if (value.length() > sizeof(g_openSkyClientId) - 1)
            {
                error = "VALUE_TOO_LONG_MAX_128";
                return false;
            }
            if (!putValue("opensky_client_id", value, g_openSkyClientId, sizeof(g_openSkyClientId)))
            {
                error = "WRITE_FAILED";
                return false;
            }
            return true;
        }

        if (normalized == "OPENSKY_CLIENT_SECRET")
        {
            if (value.length() > sizeof(g_openSkyClientSecret) - 1)
            {
                error = "VALUE_TOO_LONG_MAX_128";
                return false;
            }
            if (!putValue("opensky_client_secret", value, g_openSkyClientSecret, sizeof(g_openSkyClientSecret)))
            {
                error = "WRITE_FAILED";
                return false;
            }
            return true;
        }

        if (normalized == "AEROAPI_KEY")
        {
            if (value.length() > sizeof(g_aeroApiKey) - 1)
            {
                error = "VALUE_TOO_LONG_MAX_128";
                return false;
            }
            if (!putValue("aeroapi_key", value, g_aeroApiKey, sizeof(g_aeroApiKey)))
            {
                error = "WRITE_FAILED";
                return false;
            }
            return true;
        }

        error = "UNKNOWN_KEY";
        return false;
    }

    bool getByKey(const String &key, String &value, String &error)
    {
        if (!g_ready)
        {
            error = "NOT_READY";
            return false;
        }

        String normalized = normalizedKey(key);

        if (normalized == "WIFI_SSID" || normalized == "NETWORK_ID")
        {
            value = g_wifiSsid;
            return true;
        }
        if (normalized == "WIFI_PASSWORD")
        {
            value = g_wifiPassword;
            return true;
        }
        if (normalized == "OPENSKY_CLIENT_ID")
        {
            value = g_openSkyClientId;
            return true;
        }
        if (normalized == "OPENSKY_CLIENT_SECRET")
        {
            value = g_openSkyClientSecret;
            return true;
        }
        if (normalized == "AEROAPI_KEY")
        {
            value = g_aeroApiKey;
            return true;
        }

        error = "UNKNOWN_KEY";
        return false;
    }
}
