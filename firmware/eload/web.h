// WiFi (station or setup access point), HTTP API, web page, OTA.
#pragma once
#include <Arduino.h>
void wifiBegin();
void webBegin();
void webLoop();
String wifiInfo();     // one line for the display
