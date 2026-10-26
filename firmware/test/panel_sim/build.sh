#!/bin/bash
# Renders the real panel.cpp on the PC (U8g2 C library, fake PCF8574 encoder) and writes PBM screenshots.
# usage: U8G2=<path to U8g2_Arduino/src/clib> ./build.sh
set -e
cd "$(dirname "$0")"; C=${U8G2:?set U8G2 to U8g2_Arduino/src/clib}; E=../../eload; O=$(mktemp -d)
for f in $C/u8g2_*.c $C/u8x8_*.c; do case $f in *u8x8_d_*) continue;; esac
  gcc -w -ffunction-sections -fdata-sections -I$C -c $f -o $O/$(basename $f .c).o; done
gcc -w -I$C -c $C/u8x8_d_ssd1309.c -o $O/ssd1309.o
g++ -std=c++17 -DPANEL_HOST_SIM -w -Istub -I$C -I$E -c $E/panel.cpp -o $O/panel.o
g++ -std=c++17 -w -Istub -I$C -I$E -c sim.cpp -o $O/sim.o
g++ -Wl,--gc-sections $O/*.o -o panel_sim && ./panel_sim
