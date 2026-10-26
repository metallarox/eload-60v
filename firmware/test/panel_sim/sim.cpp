// Host harness: run with build.sh
// Host harness: real panel.cpp rendered into a bitmap, encoder driven through a fake PCF8574.
#include "Arduino.h"
#include "Wire.h"
#include "load.h"
#include "settings.h"
#include "panel.h"
#include "U8g2lib.h"
uint32_t g_ms = 1000; uint8_t g_pcf = 0xFF; TwoWire Wire;
LoadState load; Settings settings;
const char *tripName(Trip t) { return t ? "TRIP" : ""; }
float setMax(Mode m) { return m == MODE_CC ? 20 : (m == MODE_CP ? 300 : 10000); }
bool loadSetOutput(bool on) { load.out = on; return true; }
void loadSetMode(Mode m, float s) { load.mode = m; load.set = s; }
void loadSetpoint(float s) { load.set = clampf(s, 0, setMax(load.mode)); }
void loadClearTrip() { load.trip = TRIP_NONE; }
void loadSetPulse(bool on) { load.pulse = on; }
void loadSetPulseParams(float f, float d) { settings.pulseFreq = pulseClampFreq(f); settings.pulseDuty = pulseClampDuty(settings.pulseFreq, d); }
bool settingsSave() { return true; }
uint8_t *simBuffer();
static void dump(const char *name) {
    panelDraw();
    uint8_t *b = simBuffer();
    FILE *f = fopen(name, "w"); fprintf(f, "P1\n128 64\n");
    for (int y = 0; y < 64; y++) { for (int c = 0; c < 128; c++) fprintf(f, "%d ", (b[(y / 8) * 128 + c] >> (y & 7)) & 1); fprintf(f, "\n"); }
    fclose(f);
}
static void poll() { panelPoll(); }
static void setIn(uint8_t v) { g_pcf = v; g_ms += 10; poll(); }
static void detent(int d) {           // one full quadrature cycle (4 transitions)
    static const uint8_t cw[4] = {0b01, 0b00, 0b10, 0b11};   // A,B gray sequence from 11
    for (int k = 0; k < 4; k++) { uint8_t ab = d > 0 ? cw[k] : cw[3 - ((k + 1) & 3)]; setIn((g_pcf & ~3) | ab); }
    g_ms += 100;
}
static void push(uint32_t ms) { setIn(g_pcf & ~0x04); g_ms += ms; poll(); setIn(g_pcf | 0x04); g_ms += 50; }
int main() {
    panelBegin();
    load.v = 12.42f; load.out = true; load.mode = MODE_CC; load.set = 4.0f;
    for (int c = 0; c < 4; c++) { load.i[c] = 0.505f; load.p[c] = 6.27f; }
    load.iTot = 2.02f; load.pTot = 25.1f;
    load.pulse = true; settings.pulseFreq = 100; settings.pulseDuty = 50;
    dump("main_pulse.pbm");
    push(800);                                          // long push -> menu
    detent(+1);                                         // select Pulse
    dump("menu.pbm");
    detent(+1); push(100);                              // Freq -> edit
    for (int k = 0; k < 3; k++) detent(+1);             // 100 -> 130 Hz
    dump("menu_edit_freq.pbm");
    printf("freq after 3 detents: %.1f  pulse=%d sel-state ok\n", settings.pulseFreq, load.pulse);
    push(100); detent(+1); push(100); for (int k = 0; k < 5; k++) detent(-1); push(100);
    printf("duty after -5: %.0f\n", settings.pulseDuty);
    push(800);                                          // close menu
    dump("main_after.pbm");
    return 0;
}
