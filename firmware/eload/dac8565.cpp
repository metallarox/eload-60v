#include "dac8565.h"

static const SPISettings DAC_SPI(10000000, MSBFIRST, SPI_MODE1);

void DAC8565::frame(uint8_t ctrl, uint16_t data) {
    SPI.beginTransaction(DAC_SPI);
    digitalWrite(_sync, LOW);
    SPI.transfer(ctrl); SPI.transfer(data >> 8); SPI.transfer(data & 0xFF);
    digitalWrite(_sync, HIGH);
    SPI.endTransaction();
}

void DAC8565::begin() {
    pinMode(_sync, OUTPUT); digitalWrite(_sync, HIGH);
    // Internal 2.5 V reference forced on ("always on"): control 0x01, data 0x1000.
    // The DAC8565 powers up with the reference enabled; this makes it explicit after a soft reset.
    frame(0x01, 0x1000);
    allZero();
}

void DAC8565::write(uint8_t ch, uint16_t code) {
    ch &= 3; _last[ch] = code;
    frame(0x10 | (ch << 1), code);
}
