// Data logging: 10-minute RAM history for the web chart + CSV file on LittleFS.
#pragma once
#include <Arduino.h>
#include "config.h"

struct HistSample { uint16_t v_cV; uint16_t i_mA; uint16_t p_dW; int8_t t; };   // 7 bytes

void logBegin();
void logTick();                       // once a second
bool logStart(uint16_t intervalS);    // starts a new CSV (old file is replaced)
void logStop();
void logClear();
void logFlush();
bool logActive();
uint32_t logLines();
uint32_t logBytes();
uint32_t fsFree();
const char *logPath();
uint16_t histCount();
const HistSample &histAt(uint16_t i);  // 0 = oldest
uint32_t histT0();                     // uptime (s) of the oldest sample
bool timeValid();
void timeString(char *buf, size_t n);  // "YYYY-MM-DD HH:MM:SS" or uptime
