// eload-60v firmware - 4-channel 60 V / 20 A / 300 W electronic load
// Board: Wemos LOLIN D1 mini Pro (ESP8266). See firmware/README.md.
#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <LittleFS.h>
#include "config.h"
#include "settings.h"
#include "load.h"
#include "panel.h"
#include "logger.h"
#include "web.h"

void setup() {
    // Safety first: keep the load disarmed whatever happens next.
    pinMode(PIN_ARM_DRV, OUTPUT); digitalWrite(PIN_ARM_DRV, LOW);
    Serial.begin(115200, SERIAL_8N1, SERIAL_TX_ONLY);        // RX (GPIO3) is the fan tach input
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setClock(400000);
    loadBegin();
    LittleFS.begin();
    settingsLoad();
    panelBegin();
    panelSplash("WiFi...");
    Serial.printf("\n%s %s\n", FW_NAME, FW_VERSION);
    for (int c = 0; c < N_CH; c++) Serial.printf("INA228 #%d %s\n", c + 1, load.inaOk[c] ? "ok" : "MISSING");
    wifiBegin();
    webBegin();
    logBegin();
    String ip = wifiInfo();
    Serial.printf("WiFi: %s\n", ip.c_str());
    panelSplash(ip.c_str());
    delay(1500);
}

void loop() {
    static uint32_t tCtl = 0, tDisp = 0, tLog = 0;
    uint32_t now = millis();
    panelPoll();
    if (now - tCtl >= CONTROL_PERIOD_MS) { tCtl = now; loadUpdate(); }
    if (now - tDisp >= DISPLAY_PERIOD_MS) { tDisp = now; panelDraw(); }
    if (now - tLog >= 1000) { tLog += 1000; logTick(); }
    webLoop();
}
