#include "core/BluetoothConfigService.h"

#include <Arduino.h>
#include <BluetoothSerial.h>
#include <WiFi.h>
#include <string.h>
#include "config/BluetoothConfiguration.h"
#include "core/RuntimeConfiguration.h"

namespace
{
    static BluetoothSerial g_serialBt;
    static bool g_started = false;
    static bool g_authenticated = false;
    static String g_inputLine;
    static constexpr size_t MAX_INPUT_LINE_LENGTH = 255;
    static constexpr unsigned long AUTH_TIMEOUT_MS = 5UL * 60UL * 1000UL;
    static unsigned long g_lastAuthActivityMs = 0;

    static void sendLine(const String &line)
    {
        if (!g_started)
            return;
        g_serialBt.println(line);
        Serial.println(String("[BT] ") + line);
    }

    static String toUpperTrimmed(const String &value)
    {
        String out = value;
        out.trim();
        out.toUpperCase();
        return out;
    }

    static String maskedValue(const String &value)
    {
        if (value.length() == 0)
        {
            return "<empty>";
        }
        return String("<redacted:len=") + String(value.length()) + ">";
    }

    static bool isSensitiveKey(const String &key)
    {
        const String normalized = toUpperTrimmed(key);
        return normalized == "WIFI_PASSWORD" ||
               normalized == "OPENSKY_CLIENT_SECRET" ||
               normalized == "AEROAPI_KEY";
    }

    static bool securePinEquals(const String &provided)
    {
        const size_t expectedLen = strlen(BluetoothConfiguration::PAIRING_PIN);
        const size_t providedLen = provided.length();
        const size_t maxLen = expectedLen > providedLen ? expectedLen : providedLen;

        uint8_t diff = (expectedLen == providedLen) ? 0 : 1;
        for (size_t i = 0; i < maxLen; ++i)
        {
            const char expectedChar = (i < expectedLen) ? BluetoothConfiguration::PAIRING_PIN[i] : 0;
            const char providedChar = (i < providedLen) ? provided.charAt(i) : 0;
            diff |= (uint8_t)(expectedChar ^ providedChar);
        }
        return diff == 0;
    }

    static void markAuthenticated()
    {
        g_authenticated = true;
        g_lastAuthActivityMs = millis();
    }

    static bool authExpired()
    {
        if (!g_authenticated)
        {
            return true;
        }
        return (millis() - g_lastAuthActivityMs) > AUTH_TIMEOUT_MS;
    }

    static bool wifiReconnect()
    {
        const char *ssid = RuntimeConfiguration::wifiSsid();
        const char *password = RuntimeConfiguration::wifiPassword();
        if (strlen(ssid) == 0)
        {
            return false;
        }

        WiFi.mode(WIFI_STA);
        WiFi.disconnect();
        delay(200);
        WiFi.begin(ssid, password);
        for (int i = 0; i < 50 && WiFi.status() != WL_CONNECTED; ++i)
        {
            delay(200);
        }

        return WiFi.status() == WL_CONNECTED;
    }

    static void printHelp()
    {
        sendLine("OK COMMANDS:");
        sendLine("AUTH <PIN>");
        sendLine("GET <KEY>");
        sendLine("GET_RAW <KEY>");
        sendLine("SET <KEY> <VALUE>");
        sendLine("LIST");
        sendLine("RECONNECT_WIFI");
        sendLine("STATUS");
        sendLine("HELP");
        sendLine("KEYS: NETWORK_ID|WIFI_SSID, WIFI_PASSWORD, OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET, AEROAPI_KEY");
    }

    static bool sendKeyValue(const String &key, bool forceMask)
    {
        String value;
        String error;
        if (!RuntimeConfiguration::getByKey(key, value, error))
        {
            sendLine(String("ERR ") + key + "_" + error);
            return false;
        }
        const String output = (forceMask || isSensitiveKey(key)) ? maskedValue(value) : value;
        sendLine(String("OK ") + toUpperTrimmed(key) + "=" + output);
        return true;
    }

    static void handleCommand(const String &rawLine)
    {
        String line = rawLine;
        line.trim();
        if (line.length() == 0)
        {
            return;
        }

        int firstSpace = line.indexOf(' ');
        String command = firstSpace < 0 ? line : line.substring(0, firstSpace);
        String args = firstSpace < 0 ? String("") : line.substring(firstSpace + 1);

        String commandUpper = toUpperTrimmed(command);

        if (commandUpper == "HELP")
        {
            printHelp();
            return;
        }

        if (commandUpper == "AUTH")
        {
            String pin = args;
            pin.trim();
            if (securePinEquals(pin))
            {
                markAuthenticated();
                sendLine("OK AUTHENTICATED");
            }
            else
            {
                sendLine("ERR BAD_PIN");
            }
            return;
        }

        if (authExpired())
        {
            g_authenticated = false;
            sendLine("ERR AUTH_REQUIRED");
            return;
        }
        g_lastAuthActivityMs = millis();

        if (!g_authenticated)
        {
            sendLine("ERR AUTH_REQUIRED");
            return;
        }

        if (commandUpper == "GET")
        {
            String key = args;
            key.trim();
            if (key.length() == 0)
            {
                sendLine("ERR MISSING_KEY");
                return;
            }
            String value;
            String error;
            if (!RuntimeConfiguration::getByKey(key, value, error))
            {
                sendLine(String("ERR ") + error);
                return;
            }
            String output = isSensitiveKey(key) ? maskedValue(value) : value;
            sendLine(String("OK ") + toUpperTrimmed(key) + "=" + output);
            return;
        }

        if (commandUpper == "GET_RAW")
        {
            String key = args;
            key.trim();
            if (key.length() == 0)
            {
                sendLine("ERR MISSING_KEY");
                return;
            }
            String value;
            String error;
            if (!RuntimeConfiguration::getByKey(key, value, error))
            {
                sendLine(String("ERR ") + error);
                return;
            }
            sendLine(String("OK ") + toUpperTrimmed(key) + "=" + value);
            return;
        }

        if (commandUpper == "SET")
        {
            int secondSpace = args.indexOf(' ');
            if (secondSpace < 0)
            {
                sendLine("ERR USE_SET_KEY_VALUE");
                return;
            }
            String key = args.substring(0, secondSpace);
            String value = args.substring(secondSpace + 1);
            key.trim();
            value.trim();

            String error;
            if (!RuntimeConfiguration::setByKey(key, value, error))
            {
                sendLine(String("ERR ") + error);
                return;
            }
            sendLine(String("OK SAVED ") + toUpperTrimmed(key));
            return;
        }

        if (commandUpper == "LIST")
        {
            sendKeyValue("WIFI_SSID", false);
            sendKeyValue("WIFI_PASSWORD", true);
            sendKeyValue("OPENSKY_CLIENT_ID", false);
            sendKeyValue("OPENSKY_CLIENT_SECRET", true);
            sendKeyValue("AEROAPI_KEY", true);
            sendLine("OK END");
            return;
        }

        if (commandUpper == "RECONNECT_WIFI")
        {
            if (wifiReconnect())
            {
                sendLine(String("OK WIFI_CONNECTED ") + WiFi.localIP().toString());
            }
            else
            {
                sendLine("ERR WIFI_CONNECT_FAILED");
            }
            return;
        }

        if (commandUpper == "STATUS")
        {
            sendLine(String("OK WIFI_STATUS=") + String((int)WiFi.status()));
            if (WiFi.status() == WL_CONNECTED)
            {
                sendLine(String("OK WIFI_IP=") + WiFi.localIP().toString());
            }
            return;
        }

        sendLine("ERR UNKNOWN_COMMAND");
    }
}

void BluetoothConfigService::begin()
{
    if (g_started || !BluetoothConfiguration::ENABLED)
    {
        return;
    }

    if (!g_serialBt.begin(BluetoothConfiguration::DEVICE_NAME))
    {
        Serial.println("Bluetooth config service failed to start");
        return;
    }

    g_serialBt.setPin(BluetoothConfiguration::PAIRING_PIN, strlen(BluetoothConfiguration::PAIRING_PIN));
    g_started = true;
    Serial.println("Bluetooth config service started");
    sendLine("OK FLIGHTWALL_CONFIG_READY");
    sendLine("OK USE_AUTH_PIN");
    printHelp();
}

void BluetoothConfigService::loop()
{
    if (!g_started)
    {
        return;
    }

    while (g_serialBt.available() > 0)
    {
        const char c = (char)g_serialBt.read();
        if (c == '\r')
        {
            continue;
        }
        if (c == '\n')
        {
            handleCommand(g_inputLine);
            g_inputLine = "";
            continue;
        }
        if (g_inputLine.length() >= MAX_INPUT_LINE_LENGTH)
        {
            g_inputLine = "";
            sendLine("ERR LINE_TOO_LONG");
            continue;
        }
        g_inputLine += c;
    }
}
