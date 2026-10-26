// Persistent settings in LittleFS (/settings.txt, key=value lines).
#pragma once
#include <Arduino.h>
#include "config.h"

struct Settings {
    char ssid[33] = "";
    char pass[65] = "";
    char hostname[24] = "eload";
    float gain[N_CH] = {1, 1, 1, 1};     // per-channel calibration
    float offset[N_CH] = {0, 0, 0, 0};   // A
    bool  autoTrim = true;               // slow closed-loop trim against the INA228
    uint8_t mask = 0x0F;                 // enabled channels
    float vCutoff = 0;                   // V, 0 = disabled (battery test end voltage)
    uint16_t logInterval = 1;            // s
};
extern Settings settings;
bool settingsLoad();
bool settingsSave();
