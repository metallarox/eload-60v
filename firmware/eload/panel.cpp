#include "panel.h"
#include <Wire.h>
#include <U8g2lib.h>
#include "config.h"
#include "load.h"
#include "logo_xbm.h"

// Pick the controller of your module (default: 2.42" SSD1309; define DISPLAY_SH1106 for the 1.3" boards).
#ifdef DISPLAY_SH1106
static U8G2_SH1106_128X64_NONAME_1_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);
#else
static U8G2_SSD1309_128X64_NONAME0_1_HW_I2C oled(U8G2_R0, U8X8_PIN_NONE);
#endif

// PCF8574 bits
#define B_ENC_A   0x01
#define B_ENC_B   0x02
#define B_ENC_SW  0x04
#define B_OUT     0x08
#define B_LED     0x10   // output, low = LED on

static bool oledOk = false, pcfOk = false;
static volatile bool expIrq = true;
static uint8_t lastIn = 0xFF, encState = 0;
static int8_t encAcc = 0;
static uint32_t swDown = 0, outDown = 0, lastPollMs = 0;
static bool longDone = false;
static uint8_t stepIdx = 1;
static bool ledOn = false;
static char note[22] = ""; static uint32_t noteUntil = 0;

static const float STEPS_CC[] = {1.0f, 0.1f, 0.01f, 0.001f};
static const float STEPS_CP[] = {10.0f, 1.0f, 0.1f};
static const float STEPS_CR[] = {100.0f, 10.0f, 1.0f, 0.1f};
static const float *steps(uint8_t &n) {
    switch (load.mode) {
        case MODE_CP: n = 3; return STEPS_CP;
        case MODE_CR: n = 4; return STEPS_CR;
        default: n = 4; return STEPS_CC;
    }
}

static void IRAM_ATTR expIsr() { expIrq = true; }

static bool probe(uint8_t a) { Wire.beginTransmission(a); return Wire.endTransmission() == 0; }
static void pcfWrite(uint8_t v) { Wire.beginTransmission(PCF8574_ADDR); Wire.write(v); Wire.endTransmission(); }
static int pcfRead() { if (Wire.requestFrom((uint8_t)PCF8574_ADDR, (uint8_t)1) != 1) return -1; return Wire.read(); }
static void setLed(bool on) { if (pcfOk && on != ledOn) { ledOn = on; pcfWrite(on ? (0xFF & ~B_LED) : 0xFF); } }
static void flash(const char *s) { strncpy(note, s, sizeof note - 1); noteUntil = millis() + 1500; }

bool panelPresent() { return oledOk || pcfOk; }

void panelBegin() {
    pcfOk = probe(PCF8574_ADDR);
    oledOk = probe(OLED_ADDR);
    if (pcfOk) {
        pcfWrite(0xFF);                                   // all quasi-inputs high, LED off
        int v = pcfRead(); if (v >= 0) { lastIn = v; encState = v & 3; }
        pinMode(PIN_EXP_INT, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(PIN_EXP_INT), expIsr, FALLING);
    }
    if (oledOk) { oled.setI2CAddress(OLED_ADDR << 1); oled.begin(); oled.setBusClock(400000); oled.setContrast(200); }
}

void panelSplash(const char *line2) {
    if (!oledOk) return;
    oled.firstPage();
    do {
        oled.drawXBMP(0, 0, LOGO_W, LOGO_H, logo_xbm);
        oled.setFont(u8g2_font_7x13B_tf); oled.drawStr(68, 14, "E-LOAD");
        oled.setFont(u8g2_font_6x10_tf);
        oled.drawStr(68, 28, "60V 20A");
        oled.drawStr(68, 40, "v" FW_VERSION);
        oled.drawStr(66, 56, line2);
    } while (oled.nextPage());
}

// ---- encoder / buttons
static void onDetent(int d) {
    uint8_t n; const float *st = steps(n);
    if (stepIdx >= n) stepIdx = n - 1;
    loadSetpoint(load.set + d * st[stepIdx]);
}

static void onShortSw() { uint8_t n; steps(n); stepIdx = (stepIdx + 1) % n; }

static void onLongSw() {
    if (load.out) { flash("OUTPUT IS ON"); return; }
    loadSetMode((Mode)((load.mode + 1) % 3), 0);   // new mode starts from zero
    stepIdx = 1;
}

static void onOut() {
    if (load.trip != TRIP_NONE && !load.out) { loadClearTrip(); return; }   // first press acknowledges a trip
    if (!loadSetOutput(!load.out)) flash(tripName(load.trip));
}

void panelPoll() {
    if (!pcfOk) return;
    uint32_t now = millis();
    if (!expIrq && now - lastPollMs < 5 && !(swDown || outDown)) return;
    expIrq = false; lastPollMs = now;
    int v = pcfRead(); if (v < 0) return;
    uint8_t in = v;
    // quadrature: full-step table, 4 transitions per detent
    static const int8_t tbl[16] = {0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0};
    uint8_t ab = in & 3;
    encAcc += tbl[(encState << 2) | ab]; encState = ab;
    if (encAcc >= 4) { encAcc -= 4; onDetent(+1); }
    else if (encAcc <= -4) { encAcc += 4; onDetent(-1); }
    // encoder switch: short = next digit, long (0.7 s) = next mode
    bool sw = !(in & B_ENC_SW);
    if (sw && !swDown) { swDown = now; longDone = false; }
    if (sw && swDown && !longDone && now - swDown > 700) { longDone = true; onLongSw(); }
    if (!sw && swDown) { if (!longDone && now - swDown > 30) onShortSw(); swDown = 0; }
    // OUTPUT button
    bool ob = !(in & B_OUT);
    if (ob && !outDown) outDown = now;
    if (!ob && outDown) { if (now - outDown > 30) onOut(); outDown = 0; }
    lastIn = in;
}

// ---- drawing
static void fmtSet(char *buf, size_t n, uint8_t &digitCol) {
    // returns the text and the column (in chars) of the digit being edited
    uint8_t ns; const float *st = steps(ns); if (stepIdx >= ns) stepIdx = ns - 1;
    const char *unit = load.mode == MODE_CC ? "A" : (load.mode == MODE_CP ? "W" : "R");
    const char *mode = load.mode == MODE_CC ? "CC" : (load.mode == MODE_CP ? "CP" : "CR");
    int dec = load.mode == MODE_CC ? 3 : 1;
    snprintf(buf, n, "%s %6.*f%s", mode, dec, load.set, unit);
    int dot = 3 + 6 - dec - 1;                       // index of '.' (value right-aligned in 6 chars)
    float w = st[stepIdx];
    int col;
    if (w >= 1) { int p = (int)lroundf(log10f(w)); col = dot - 1 - p; }
    else { int p = (int)lroundf(-log10f(w)); col = dot + p; }
    digitCol = col;
}

void panelDraw() {
    setLed(load.out);
    if (!oledOk) return;
    char l0[24], lc[N_CH][24], l5[24]; uint8_t cur;
    snprintf(l0, sizeof l0, "%5.2fV %6.3fA %4.0fW", load.v, load.iTot, load.pTot);
    for (int c = 0; c < N_CH; c++) snprintf(lc[c], sizeof lc[c], "%d %6.3fA %6.1fW", c + 1, load.i[c], load.p[c]);
    fmtSet(l5, sizeof l5, cur);
    char right[12];
    if (millis() < noteUntil) snprintf(right, sizeof right, "%s", "");
    else if (load.trip != TRIP_NONE) snprintf(right, sizeof right, "%s", tripName(load.trip));
    else snprintf(right, sizeof right, "%s", load.out ? "ON" : "OFF");
    oled.firstPage();
    do {
        oled.setFont(u8g2_font_6x10_tf);
        oled.drawStr(0, 9, l0);
        oled.drawHLine(0, 11, 128);
        for (int c = 0; c < N_CH; c++) oled.drawStr(0, 21 + c * 10, lc[c]);
        oled.drawHLine(0, 53, 128);
        if (millis() < noteUntil) oled.drawStr(0, 63, note);
        else {
            oled.drawStr(0, 63, l5);
            oled.drawHLine(cur * 6, 63, 5);           // cursor under the digit being edited
            oled.setDrawColor(1);
            int w = oled.getStrWidth(right);
            if (load.trip != TRIP_NONE || load.out) { oled.drawBox(127 - w - 3, 54, w + 3, 10); oled.setDrawColor(0); }
            oled.drawStr(127 - w - 1, 63, right);
            oled.setDrawColor(1);
        }
        panelPoll();                                   // keep the encoder responsive between pages
    } while (oled.nextPage());
}
