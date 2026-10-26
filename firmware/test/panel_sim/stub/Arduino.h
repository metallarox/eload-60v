#pragma once
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <algorithm>
#define IRAM_ATTR
#define INPUT_PULLUP 2
#define FALLING 2
#define A0 17
extern uint32_t g_ms;
inline uint32_t millis() { return g_ms; }
inline void pinMode(int, int) {}
inline int digitalPinToInterrupt(int p) { return p; }
inline void attachInterrupt(int, void (*)(), int) {}
using std::max; using std::min;
#define PROGMEM
