// Front panel: 128x64 I2C OLED (SSD1309 2.42" or SH1106 1.3"), EC11 encoder and OUTPUT button on a PCF8574.
#pragma once
#include <Arduino.h>

void panelBegin();
void panelSplash(const char *line2);   // logo + text, shown at boot
void panelPoll();                      // call as often as possible (encoder)
void panelDraw();                      // every DISPLAY_PERIOD_MS
bool panelPresent();
