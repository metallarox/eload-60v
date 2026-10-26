#pragma once
extern "C" {
#include "u8g2.h"
}
#define U8X8_PIN_NONE 255
#define U8G2_R0 (&u8g2_cb_r0)
struct U8G2_SSD1309_128X64_NONAME0_1_HW_I2C {
    u8g2_t u;
    U8G2_SSD1309_128X64_NONAME0_1_HW_I2C(const u8g2_cb_t *r, uint8_t) { u8g2_Setup_ssd1309_128x64_noname0_f(&u, r, u8x8_byte_empty, u8x8_dummy_cb); u8x8_InitDisplay(u8g2_GetU8x8(&u)); }
    void setI2CAddress(uint8_t) {} bool begin() { return true; } void setBusClock(uint32_t) {} void setContrast(uint8_t) {}
    void firstPage() { u8g2_FirstPage(&u); } uint8_t nextPage() { return u8g2_NextPage(&u); }
    void setFont(const uint8_t *f) { u8g2_SetFont(&u, f); }
    void drawStr(int x, int y, const char *s) { u8g2_DrawStr(&u, x, y, s); }
    int getStrWidth(const char *s) { return u8g2_GetStrWidth(&u, s); }
    void drawBox(int x, int y, int w, int h) { u8g2_DrawBox(&u, x, y, w, h); }
    void drawHLine(int x, int y, int w) { u8g2_DrawHLine(&u, x, y, w); }
    void setDrawColor(int c) { u8g2_SetDrawColor(&u, c); }
    void drawXBMP(int x, int y, int w, int h, const uint8_t *b) { u8g2_DrawXBMP(&u, x, y, w, h, b); }
};
