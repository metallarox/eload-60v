// Minimal INA228 driver (TI 85 V, 20-bit power monitor), tuned for this load.
#pragma once
#include <Arduino.h>
#include <Wire.h>

class INA228 {
public:
    // registers
    enum : uint8_t { CONFIG = 0x00, ADC_CONFIG = 0x01, SHUNT_CAL = 0x02, VSHUNT = 0x04, VBUS = 0x05,
                     DIETEMP = 0x06, CURRENT = 0x07, POWER = 0x08, ENERGY = 0x09, CHARGE = 0x0A,
                     DIAG_ALRT = 0x0B, SOVL = 0x0C, SUVL = 0x0D, BOVL = 0x0E, BUVL = 0x0F,
                     TEMP_LIMIT = 0x10, PWR_LIMIT = 0x11, MANUFACTURER_ID = 0x3E, DEVICE_ID = 0x3F };
    // DIAG_ALRT flags
    enum : uint16_t { F_MEMSTAT = 1 << 0, F_CNVRF = 1 << 1, F_POL = 1 << 2, F_BUSUL = 1 << 3, F_BUSOL = 1 << 4,
                      F_SHNTUL = 1 << 5, F_SHNTOL = 1 << 6, F_TMPOL = 1 << 7, F_MATHOF = 1 << 9,
                      F_CHARGEOF = 1 << 10, F_ENERGYOF = 1 << 11, F_ALATCH = 1 << 15 };

    explicit INA228(uint8_t addr = 0x40) : _addr(addr) {}
    bool begin(float rShunt, float maxCurrent);
    bool present() const { return _ok; }
    void setLimits(float ovpV, float ocpA, float oppW);   // hardware ALERT thresholds (latched)
    float busVoltage();     // V
    float current();        // A
    float power();          // W
    double energy();        // J since last resetAccumulators()
    double charge();        // C
    float dieTemp();        // C
    uint16_t readDiag();    // reading also clears latched flags and releases ALERT
    void resetAccumulators();
    void setAdcConfig(uint16_t v) { write16(ADC_CONFIG, v); }

private:
    uint8_t _addr; bool _ok = false; float _currentLsb = 0, _rShunt = 0.02f; uint16_t _cfg = 0;
    bool write16(uint8_t reg, uint16_t v);
    bool readN(uint8_t reg, uint8_t n, uint8_t *buf);
    uint16_t read16(uint8_t reg);
    int32_t read20s(uint8_t reg);   // 20-bit two's complement in a 24-bit register
};
