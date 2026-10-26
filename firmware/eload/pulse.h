// Pulsed load: a timer1 callback alternates the DAC between two sets of codes.
// The callback runs in the core's waveform NMI (shared with analogWrite), so it talks to the
// HSPI registers directly and only while the main code keeps its hands off the DAC.
#pragma once
#include <Arduino.h>
#include "config.h"

// Start or update the waveform. hi/lo = DAC codes per channel, times in microseconds.
// The new values take effect at the next edge; the first call starts with the high phase.
void pulseSet(const uint16_t hi[N_CH], const uint16_t lo[N_CH], uint32_t hiUs, uint32_t loUs);
void pulseStop();        // after this the caller owns the DAC again
bool pulseRunning();
uint32_t pulseEdges();   // edge counter (diagnostics)
