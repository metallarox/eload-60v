#include "load.h"
#include <SPI.h>
#include "ina228.h"
#include "dac8565.h"
#include "settings.h"

LoadState load;
static INA228 ina[N_CH] = {INA228(INA_ADDR[0]), INA228(INA_ADDR[1]), INA228(INA_ADDR[2]), INA228(INA_ADDR[3])};
static DAC8565 dac(PIN_DAC_SYNC);
static volatile uint32_t tachPulses = 0;
static uint32_t tachT0 = 0;
static uint8_t cutoffCount = 0;
static bool armed = false;               // ARM_DRV high and confirmed by ARM_FB

static void IRAM_ATTR tachIsr() { tachPulses++; }

const char *tripName(Trip t) {
    switch (t) {
        case TRIP_NONE: return "";
        case TRIP_HW: return "HW TRIP";
        case TRIP_OVP: return "OVP";
        case TRIP_OCP: return "OCP";
        case TRIP_OPP: return "OPP";
        case TRIP_OTP: return "OTP";
        case TRIP_VMAX: return "V>60V";
        case TRIP_CUTOFF: return "CUTOFF";
        case TRIP_SENSOR: return "SENSOR";
    }
    return "?";
}

float setMax(Mode m) { return m == MODE_CC ? N_CH * I_CH_MAX : (m == MODE_CP ? N_CH * P_CH_MAX : 10000.0f); }

static void hardOff() {
    digitalWrite(PIN_ARM_DRV, LOW);          // ARM low -> CLAMP shorts all setpoints in hardware
    armed = false;
    dac.allZero();
    for (int c = 0; c < N_CH; c++) load.iCmd[c] = 0;
    load.out = false;
}

void loadBegin() {
    pinMode(PIN_ARM_DRV, OUTPUT); digitalWrite(PIN_ARM_DRV, LOW);
    SPI.begin();                              // HSPI claims GPIO12 as MISO ...
    pinMode(PIN_ARM_DRV, OUTPUT); digitalWrite(PIN_ARM_DRV, LOW);   // ... take it back: ARM_DRV
    pinMode(PIN_ARM_FB, INPUT);
    dac.begin();
    for (int c = 0; c < N_CH; c++) {
        load.inaOk[c] = ina[c].begin(R_SHUNT, 8.0f);
        if (load.inaOk[c]) { ina[c].setLimits(INA_OVP_V, INA_OCP_A, INA_OPP_W); ina[c].readDiag(); }
    }
    pinMode(PIN_FAN_TACH, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_FAN_TACH), tachIsr, FALLING);
    analogWriteRange(1000); analogWriteFreq(25000);
    hardOff();
}

void loadClearTrip() {
    for (int c = 0; c < N_CH; c++) if (load.inaOk[c]) ina[c].readDiag();   // releases latched ALERTs
    load.trip = TRIP_NONE; load.tripDiag = 0; load.tripCh = -1;
}

bool loadSetOutput(bool on) {
    if (!on) { hardOff(); return true; }
    if (load.out) return true;
    loadClearTrip();
    for (int c = 0; c < N_CH; c++)
        if ((settings.mask & (1 << c)) && !load.inaOk[c]) { load.trip = TRIP_SENSOR; load.tripCh = c; return false; }
    if (load.v > V_MAX + 2) { load.trip = TRIP_VMAX; return false; }
    load.out = true; load.onSince = millis(); cutoffCount = 0;
    loadUpdate();                             // computes and writes the setpoints first
    if (!load.out) return false;              // a protection tripped during that first update
    digitalWrite(PIN_ARM_DRV, HIGH);          // then releases the clamp
    delay(3);
    if (!digitalRead(PIN_ARM_FB)) {           // something holds ARM low (OVP, OTP, ALERT)
        hardOff(); load.trip = TRIP_HW; return false;
    }
    armed = true;
    return true;
}

void loadSetMode(Mode m, float set) { load.mode = m; loadSetpoint(set); }
void loadSetpoint(float set) {
    if (load.mode == MODE_CR) {
        // CR: 0 or an empty field means "open" (highest resistance = least current), never the 0.05 ohm minimum
        load.set = set <= 0 ? setMax(MODE_CR) : clampf(set, 0.05f, setMax(MODE_CR));
        return;
    }
    load.set = clampf(set, 0.0f, setMax(load.mode));
}

void loadResetCounters() { for (int c = 0; c < N_CH; c++) if (load.inaOk[c]) ina[c].resetAccumulators(); }

static Trip classify(uint16_t diag) {
    if (diag & INA228::F_BUSOL) return TRIP_OVP;
    if (diag & INA228::F_SHNTOL) return TRIP_OCP;
    if (diag & INA228::F_POL) return TRIP_OPP;
    return TRIP_NONE;
}

void loadUpdate() {
    // ---- measure
    float vsum = 0; int nv = 0; double wh = 0, ah = 0;
    load.iTot = load.pTot = 0;
    for (int c = 0; c < N_CH; c++) {
        if (!load.inaOk[c]) { load.i[c] = load.p[c] = 0; continue; }
        float v = ina[c].busVoltage(); vsum += v; nv++;
        load.i[c] = ina[c].current(); load.p[c] = ina[c].power();
        load.iTot += load.i[c]; load.pTot += load.p[c];
        wh += ina[c].energy() / 3600.0; ah += ina[c].charge() / 3600.0;
    }
    if (nv) load.v = vsum / nv;
    load.wh = wh; load.ah = ah;
    load.tSpreader = ntcTemperature(analogRead(PIN_NTC));
    static uint8_t slow = 0;
    if (++slow >= 20) {                       // once a second: die temperatures and fan speed
        slow = 0;
        for (int c = 0; c < N_CH; c++) if (load.inaOk[c]) load.tDie[c] = ina[c].dieTemp();
        uint32_t now = millis(), p = tachPulses; tachPulses = 0;
        uint32_t dt = now - tachT0; if (dt < 1) dt = 1;
        load.rpm = tachT0 ? (uint16_t)(p * 30000UL / dt) : 0;   // 2 pulses / rev
        tachT0 = now;
    }

    // ---- fan (gate of the open-drain FET is inverted)
    load.fan = fanDuty(load.tSpreader, load.pTot);
    analogWrite(PIN_FAN_PWM, (int)((1.0f - load.fan) * 1000));

    if (!load.out) return;

    // ---- protections
    if (armed && !digitalRead(PIN_ARM_FB)) {  // hardware tripped: OVP/OTP comparators or an INA228 ALERT
        hardOff();
        load.trip = TRIP_HW;
        for (int c = 0; c < N_CH; c++) {
            if (!load.inaOk[c]) continue;
            uint16_t d = ina[c].readDiag();
            Trip t = classify(d);
            if (t != TRIP_NONE) { load.trip = t; load.tripDiag = d; load.tripCh = c; break; }
        }
        if (load.trip == TRIP_HW && load.tSpreader > 90) load.trip = TRIP_OTP;
        if (load.trip == TRIP_HW && load.v > 62) load.trip = TRIP_OVP;
        return;
    }
    if (load.v > V_MAX + 2) { hardOff(); load.trip = TRIP_VMAX; return; }
    if (load.tSpreader > T_SPREADER_MAX) { hardOff(); load.trip = TRIP_OTP; return; }
    if (settings.vCutoff > 0 && millis() - load.onSince > 1000) {
        cutoffCount = load.v < settings.vCutoff ? cutoffCount + 1 : 0;
        if (cutoffCount >= 3) { hardOff(); load.trip = TRIP_CUTOFF; return; }
    }

    // ---- setpoints
    float target = modeTarget(load.mode, load.set, load.v);
    float ich[N_CH];
    distribute(target, settings.mask, load.v, ich);
    for (int c = 0; c < N_CH; c++) {
        bool en = settings.mask & (1 << c);
        float a = en ? (ich[c] > I_KEEPALIVE ? ich[c] : I_KEEPALIVE) : 0;
        if (en && settings.autoTrim && millis() - load.onSince > 500)
            settings.gain[c] = trimGain(settings.gain[c], load.iCmd[c], load.i[c]);
        load.iCmd[c] = a;
        dac.write(c, dacCode(a, settings.gain[c], settings.offset[c]));
    }
}
