#!/bin/bash
# Builds the firmware with makeEspArduino (no Arduino IDE needed).
#   ESP_ROOT  = ESP8266 Arduino core 3.1.2 checkout (with tools/get.py run)
#   MAKE_ESP  = makeEspArduino.mk
#   LIBS_DIR  = folder with U8g2_Arduino
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ESP_ROOT=${ESP_ROOT:-$HOME/esp/esp8266}
MAKE_ESP=${MAKE_ESP:-$HOME/esp/makeEspArduino/makeEspArduino.mk}
LIBS_DIR=${LIBS_DIR:-$HOME/esp/libs}
L=$ESP_ROOT/libraries
python3 "$HERE/tools/embed_web.py"
make -s -f "$MAKE_ESP" ESP_ROOT="$ESP_ROOT" SKETCH="$HERE/eload/eload.ino" BOARD=d1_mini_pro FLASH_DEF=16M14M \
  BUILD_DIR="${BUILD_DIR:-/tmp/eload_build}" \
  LIBS="$L/Wire $L/SPI $L/ESP8266WiFi $L/ESP8266WebServer $L/ESP8266HTTPUpdateServer $L/ESP8266mDNS $L/ArduinoOTA $L/LittleFS $LIBS_DIR/U8g2_Arduino" "$@"
