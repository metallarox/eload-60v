#include "ina228.h"

bool INA228::write16(uint8_t reg, uint16_t v) {
    Wire.beginTransmission(_addr); Wire.write(reg); Wire.write(v >> 8); Wire.write(v & 0xFF);
    return Wire.endTransmission() == 0;
}
bool INA228::readN(uint8_t reg, uint8_t n, uint8_t *buf) {
    Wire.beginTransmission(_addr); Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(_addr, n) != n) return false;
    for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
    return true;
}
uint16_t INA228::read16(uint8_t reg) {
    uint8_t b[2] = {0, 0}; readN(reg, 2, b); return (uint16_t)(b[0] << 8 | b[1]);
}
int32_t INA228::read20s(uint8_t reg) {
    uint8_t b[3] = {0, 0, 0}; readN(reg, 3, b);
    int32_t v = ((int32_t)b[0] << 16 | (int32_t)b[1] << 8 | b[2]) >> 4;
    if (v & 0x80000) v -= 0x100000;   // sign-extend 20 bits
    return v;
}

bool INA228::begin(float rShunt, float maxCurrent) {
    _ok = false; _rShunt = rShunt;
    if ((read16(MANUFACTURER_ID)) != 0x5449) return false;          // "TI"
    if (((read16(DEVICE_ID) >> 4) & 0x0FFF) != 0x228) return false;
    write16(CONFIG, 0x8000);                                         // reset
    delay(2);
    _cfg = 0x0000;                       // ADCRANGE = 0 (+-163.84 mV), no temp compensation
    write16(CONFIG, _cfg);
    // MODE=0xF continuous bus+shunt+temp, VBUSCT=VSHCT=VTCT=540 us (code 4), AVG=16 (code 2)
    write16(ADC_CONFIG, (0xF << 12) | (4 << 9) | (4 << 6) | (4 << 3) | 2);
    _currentLsb = maxCurrent / 524288.0f;                            // 2^19
    write16(SHUNT_CAL, (uint16_t)lroundf(13107.2e6f * _currentLsb * rShunt));
    _ok = true;
    return true;
}

void INA228::setLimits(float ovpV, float ocpA, float oppW) {
    // ALATCH=1 (latched), SLOWALERT=0 (compare every conversion, before averaging), APOL=0 (active low)
    write16(DIAG_ALRT, F_ALATCH);
    write16(SOVL, (uint16_t)lroundf(ocpA * _rShunt / 5e-6f));        // 5 uV/LSB at ADCRANGE=0
    write16(BOVL, (uint16_t)lroundf(ovpV / 3.125e-3f));              // 3.125 mV/LSB
    write16(PWR_LIMIT, (uint16_t)lroundf(oppW / (256.0f * 3.2f * _currentLsb)));
}

float INA228::busVoltage() { return read20s(VBUS) * 195.3125e-6f; }
float INA228::current()    { return read20s(CURRENT) * _currentLsb; }
float INA228::power() {
    uint8_t b[3] = {0, 0, 0}; readN(POWER, 3, b);
    uint32_t v = (uint32_t)b[0] << 16 | (uint32_t)b[1] << 8 | b[2];
    return v * 3.2f * _currentLsb;
}
double INA228::energy() {
    uint8_t b[5] = {0}; readN(ENERGY, 5, b);
    uint64_t v = 0; for (int i = 0; i < 5; i++) v = v << 8 | b[i];
    return (double)v * 16.0 * 3.2 * _currentLsb;
}
double INA228::charge() {
    uint8_t b[5] = {0}; readN(CHARGE, 5, b);
    int64_t v = 0; for (int i = 0; i < 5; i++) v = v << 8 | b[i];
    if (v & ((int64_t)1 << 39)) v -= ((int64_t)1 << 40);
    return (double)v * _currentLsb;
}
float INA228::dieTemp() { return (int16_t)read16(DIETEMP) * 7.8125e-3f; }
uint16_t INA228::readDiag() { return read16(DIAG_ALRT); }
void INA228::resetAccumulators() { write16(CONFIG, _cfg | (1 << 14)); }
