#pragma once
#include <cstdint>
extern uint8_t g_pcf;   // simulated PCF8574 inputs
struct TwoWire {
    void beginTransmission(uint8_t) {} size_t write(uint8_t) { return 1; } uint8_t endTransmission() { return 0; }
    uint8_t requestFrom(uint8_t, uint8_t n) { return n; } int read() { return g_pcf; }
};
extern TwoWire Wire;
