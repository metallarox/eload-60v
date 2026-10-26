// Load controller: measurement, setpoint distribution, protections, fan.
#pragma once
#include <Arduino.h>
#include "config.h"
#include "control.h"

enum Trip : uint8_t { TRIP_NONE, TRIP_HW, TRIP_OVP, TRIP_OCP, TRIP_OPP, TRIP_OTP, TRIP_VMAX, TRIP_CUTOFF, TRIP_SENSOR };
const char *tripName(Trip t);

struct LoadState {
    float v = 0;                     // bus voltage (remote sense), V
    float i[N_CH] = {0}, p[N_CH] = {0};
    float iTot = 0, pTot = 0;
    float iCmd[N_CH] = {0};          // per-channel command, A
    float tSpreader = 25, tDie[N_CH] = {0};
    double wh = 0, ah = 0;           // since the last counter reset
    bool out = false;
    Mode mode = MODE_CC;
    float set = 0;                   // A, W or ohm depending on mode
    Trip trip = TRIP_NONE;
    uint16_t tripDiag = 0;           // INA228 DIAG flags of the channel that tripped
    int8_t tripCh = -1;
    float fan = 0; uint16_t rpm = 0;
    bool inaOk[N_CH] = {false};
    uint32_t onSince = 0;
};
extern LoadState load;

void loadBegin();                    // call first in setup(): forces the load off
void loadUpdate();                   // every CONTROL_PERIOD_MS
bool loadSetOutput(bool on);         // returns false if it cannot arm (trip, sensors missing)
void loadSetMode(Mode m, float set);
void loadSetpoint(float set);
void loadResetCounters();
void loadClearTrip();
float setMax(Mode m);                // UI limit for the setpoint of a mode
