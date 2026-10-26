// Pure control math, no Arduino dependencies (unit-tested on the host, see firmware/test).
#pragma once
#include <math.h>
#include <stdint.h>
#include "config.h"

enum Mode : uint8_t { MODE_CC = 0, MODE_CP = 1, MODE_CR = 2 };

static inline float clampf(float x, float lo, float hi) { return x < lo ? lo : (x > hi ? hi : x); }

// Maximum current one channel may sink at bus voltage v (current limit, then power limit).
static inline float channelLimit(float v) {
    float vv = v < 0.1f ? 0.1f : v;
    float ip = P_CH_MAX / vv;
    return ip < I_CH_MAX ? ip : I_CH_MAX;
}

// Total current requested by the active mode. set is A (CC), W (CP) or ohm (CR).
static inline float modeTarget(Mode m, float set, float v) {
    if (set <= 0) return 0;
    switch (m) {
        case MODE_CC: return set;
        case MODE_CP: return v > 0.2f ? set / v : 0;
        case MODE_CR: return v / set;
    }
    return 0;
}

// Split the total current evenly over the enabled channels, honouring the per-channel limit.
// Returns the total that will actually flow (may be lower than requested).
static inline float distribute(float total, uint8_t mask, float v, float out[N_CH]) {
    int n = 0;
    for (int c = 0; c < N_CH; c++) if (mask & (1 << c)) n++;
    float lim = channelLimit(v), sum = 0;
    for (int c = 0; c < N_CH; c++) {
        out[c] = 0;
        if (n && (mask & (1 << c))) { out[c] = clampf(total / n, 0, lim); sum += out[c]; }
    }
    return sum;
}

// DAC code for a channel current, with per-channel calibration (gain, offset in A).
static inline uint16_t dacCode(float amps, float gain, float offset) {
    float a = amps * gain + offset;
    if (a <= 0) return 0;
    float vdac = a * DIVIDER * R_SHUNT;
    float code = vdac / DAC_VREF * DAC_FS;
    if (code > DAC_FS) code = DAC_FS;
    return (uint16_t)lroundf(code);
}

// NTC temperature (C) from the raw D1 mini A0 reading (0..1023 = 0..3.2 V at the pin).
static inline float ntcTemperature(int raw) {
    float vn = raw / 1023.0f * A0_DIVIDER;
    if (vn <= 0.01f) return 200.0f;                  // shorted NTC -> treat as hot
    if (vn >= NTC_VCC - 0.01f) return -60.0f;        // open NTC
    float rp = NTC_PULLUP * vn / (NTC_VCC - vn);     // NTC in parallel with the A0 divider
    if (rp >= A0_LOAD) return -60.0f;
    float r = rp * A0_LOAD / (A0_LOAD - rp);
    float t = 1.0f / (1.0f / 298.15f + logf(r / NTC_R25) / NTC_BETA);
    return t - 273.15f;
}

// Fan duty 0..1 from temperature and dissipated power.
static inline float fanDuty(float tC, float pW) {
    float dt = clampf((tC - FAN_T_LOW) / (FAN_T_HIGH - FAN_T_LOW), 0, 1);
    float dp = clampf(pW / 300.0f, 0, 1);
    float d = dt > dp ? dt : dp;
    return FAN_MIN_DUTY + (1 - FAN_MIN_DUTY) * d;
}

// Slow closed-loop trim: nudges the per-channel gain so the INA228 reading matches the setpoint.
static inline float trimGain(float gain, float setA, float measA) {
    if (setA < 0.05f) return gain;                    // too little signal
    float err = (setA - measA) / setA;
    if (fabsf(err) > 0.05f) return gain;              // large error = transient or limit, do not integrate
    float g = gain * (1 + 0.05f * err);
    return clampf(g, 0.95f, 1.05f);
}

// ---- pulsed load timing
static inline float pulseClampFreq(float f) { return clampf(f, PULSE_F_MIN, PULSE_F_MAX); }

// Duty (%) allowed at frequency f: 1..99 %, narrowed so both phases last at least PULSE_T_MIN_US.
static inline float pulseClampDuty(float f, float duty) {
    f = pulseClampFreq(f);
    float dmin = PULSE_T_MIN_US * 1e-6f * f * 100.0f;
    float lo = dmin > PULSE_D_MIN ? dmin : PULSE_D_MIN;
    float hi = 100.0f - lo;
    if (hi > PULSE_D_MAX) hi = PULSE_D_MAX;
    return clampf(duty, lo, hi);
}

// High and low phase durations in microseconds.
static inline void pulseTimes(float f, float duty, uint32_t &hiUs, uint32_t &loUs) {
    f = pulseClampFreq(f);
    duty = pulseClampDuty(f, duty);
    double period = 1e6 / f;
    hiUs = (uint32_t)llround(period * duty / 100.0);
    loUs = (uint32_t)llround(period) - hiUs;
}

// Encoder step for the frequency: two significant digits (100 -> 110, 99 -> 100, 1.0 -> 1.1).
static inline float pulseFreqStep(float f, int dir) {
    float ref = dir < 0 ? f * 0.9999f : f;
    return powf(10.0f, floorf(log10f(ref)) - 1.0f);
}
static inline float pulseFreqNudge(float f, int dir, float mult) {
    float st = pulseFreqStep(f, dir) * mult;
    float n = f + dir * st;
    n = roundf(n / st) * st;                          // stay on the grid of the step
    return pulseClampFreq(n);
}
