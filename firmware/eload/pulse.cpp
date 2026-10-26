#include "pulse.h"
#include <core_esp8266_waveform.h>
#include "dac8565.h"

struct PulseCfg {
    uint32_t hi[N_CH], lo[N_CH];     // packed SPI words
    uint32_t hiCcy, loCcy;           // phase lengths, CPU cycles
};
static PulseCfg cfg[2];
static volatile uint8_t act = 0;
static volatile bool running = false, phaseHigh = false;
static volatile uint32_t nextEdge = 0, edges = 0;
static const uint32_t MAX_WAIT = microsecondsToClockCycles(5000);   // re-check at least every 5 ms
static const uint32_t SYNC_BIT = 1UL << PIN_DAC_SYNC;

static inline void IRAM_ATTR spiFrame(uint32_t w) {
    while (SPI1CMD & SPIBUSY) {}
    GPOC = SYNC_BIT;                                            // SYNC low
    SPI1U1 = (SPI1U1 & ~((SPIMMOSI << SPILMOSI) | (SPIMMISO << SPILMISO))) | (23 << SPILMOSI) | (23 << SPILMISO);
    SPI1W0 = w;
    SPI1CMD |= SPIBUSY;
    while (SPI1CMD & SPIBUSY) {}
    GPOS = SYNC_BIT;                                            // SYNC high, the DAC updates
}

static uint32_t IRAM_ATTR pulseCb() {
    uint32_t now = ESP.getCycleCount();
    int32_t rem = (int32_t)(nextEdge - now);
    if (rem > 0) return (uint32_t)rem < MAX_WAIT ? (uint32_t)rem : MAX_WAIT;
    const PulseCfg &c = cfg[act];
    bool h = !phaseHigh; phaseHigh = h;
    const uint32_t *w = h ? c.hi : c.lo;
    for (int i = 0; i < N_CH; i++) spiFrame(w[i]);
    edges++;
    uint32_t ne = nextEdge + (h ? c.hiCcy : c.loCcy);
    now = ESP.getCycleCount();
    if ((int32_t)(ne - now) <= 0) ne = now + (h ? c.hiCcy : c.loCcy);   // fell behind (e.g. long NMI): resync
    nextEdge = ne;
    rem = (int32_t)(ne - now);
    return (uint32_t)rem < MAX_WAIT ? (uint32_t)rem : MAX_WAIT;
}

void pulseSet(const uint16_t hi[N_CH], const uint16_t lo[N_CH], uint32_t hiUs, uint32_t loUs) {
    uint8_t nb = running ? act ^ 1 : act;                       // fill the buffer the ISR is not using
    PulseCfg &c = cfg[nb];
    for (int i = 0; i < N_CH; i++) { c.hi[i] = DAC8565::rawWord(i, hi[i]); c.lo[i] = DAC8565::rawWord(i, lo[i]); }
    c.hiCcy = microsecondsToClockCycles(hiUs);
    c.loCcy = microsecondsToClockCycles(loUs);
    act = nb;                                                   // single byte store: atomic for the ISR
    if (running) return;
    DAC8565 tmp(PIN_DAC_SYNC); tmp.prepareSpi();
    phaseHigh = false;                                          // first edge goes high
    nextEdge = ESP.getCycleCount() + microsecondsToClockCycles(20);
    running = true;
    setTimer1Callback(pulseCb);
}

void pulseStop() {
    if (!running) return;
    setTimer1Callback(nullptr);                                 // the NMI cannot be in progress here (single core)
    running = false;
    while (SPI1CMD & SPIBUSY) {}
    digitalWrite(PIN_DAC_SYNC, HIGH);
}

bool pulseRunning() { return running; }
uint32_t pulseEdges() { return edges; }
