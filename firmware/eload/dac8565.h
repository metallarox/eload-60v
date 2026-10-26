// DAC8565 quad 16-bit DAC, 24-bit SPI frame:
//   DB23..22 = 0, DB21..20 = load command (01 = write and update the selected DAC),
//   DB19 = don't care, DB18..17 = DAC select, DB16 = PD0, DB15..0 = data.
// Data is latched on the falling SCLK edge -> SPI mode 1.
#pragma once
#include <Arduino.h>
#include <SPI.h>

class DAC8565 {
public:
    explicit DAC8565(uint8_t syncPin) : _sync(syncPin) {}
    void begin();
    void write(uint8_t ch, uint16_t code);     // write and update one channel
    void allZero() { for (uint8_t c = 0; c < 4; c++) write(c, 0); }
    uint16_t last(uint8_t ch) const { return _last[ch & 3]; }
private:
    uint8_t _sync; uint16_t _last[4] = {0, 0, 0, 0};
    void frame(uint8_t ctrl, uint16_t data);
};
