// eload-60v firmware - hardware configuration (rev 0.3 board, Wemos LOLIN D1 mini Pro)
#pragma once
#include <stdint.h>

#define FW_VERSION "0.2.0"
#define FW_NAME    "eload-60v"

// ---------------------------------------------------------------- pins (ESP8266 GPIO numbers)
#define PIN_I2C_SDA   4     // D2
#define PIN_I2C_SCL   5     // D1
// SPI uses the ESP8266 HSPI pins: SCK = GPIO14 (D5), MOSI = GPIO13 (D7)
#define PIN_DAC_SYNC  15    // D8, DAC8565 SYNC (low at boot thanks to the module pull-down)
#define PIN_ARM_DRV   12    // D6, drives ARM through 1k. HIGH = load armed. Re-assign after SPI.begin()!
#define PIN_ARM_FB    16    // D0, reads ARM through 100k (hardware trip detection)
#define PIN_FAN_PWM   2     // D4, gate of the open-drain fan PWM FET (inverted)
#define PIN_FAN_TACH  3     // RX, fan tach (Serial runs TX-only)
#define PIN_EXP_INT   0     // D3, PCF8574 INT (front panel)
#define PIN_NTC       A0    // NTC1 through the D1 mini 220k/100k divider

// ---------------------------------------------------------------- I2C addresses
static const uint8_t INA_ADDR[4] = {0x40, 0x41, 0x42, 0x43};
#define PCF8574_ADDR  0x20
#define OLED_ADDR     0x3C

// ---------------------------------------------------------------- analog front end
#define R_SHUNT       0.020f      // ohm, per channel
#define DIVIDER       25.0f       // DAC -> setpoint divider (24k / 1k)
#define DAC_VREF      2.5f        // DAC8565 internal reference
#define DAC_FS        65535.0f
// I = Vdac / (DIVIDER * R_SHUNT) -> 2 A/V, 5 A at 2.5 V

// ---------------------------------------------------------------- ratings and limits
#define N_CH          4
#define I_CH_MAX      5.0f        // A per channel
#define P_CH_MAX      75.0f       // W per channel (MOSFET SOA / thermal budget)
#define V_MAX         60.0f       // V, rated input
#define I_KEEPALIVE   0.010f      // A per channel while the output is on (fast response from idle)
#define T_SPREADER_MAX 85.0f      // C, firmware over-temperature (hardware OTP trips at ~100 C)

// INA228 hardware limits -> ALERT -> ARM (latched)
#define INA_OVP_V     63.0f       // bus over-voltage
#define INA_OCP_A     5.25f       // per channel over-current
#define INA_OPP_W     80.0f       // per channel over-power

// ---------------------------------------------------------------- fan / NTC
#define NTC_R25       10000.0f
#define NTC_BETA      3950.0f
#define NTC_PULLUP    10000.0f
#define NTC_VCC       3.3f
#define A0_DIVIDER    3.2f        // D1 mini: 220k / 100k in front of the 1 V ADC
#define A0_LOAD       320000.0f   // the same divider loads the NTC node
#define FAN_T_LOW     35.0f       // C -> minimum fan speed
#define FAN_T_HIGH    65.0f       // C -> full speed
#define FAN_MIN_DUTY  0.25f

// ---------------------------------------------------------------- pulsed (modulated) load
// The sink alternates between the setpoint (high phase) and the keep-alive current (low phase).
// The CC loop needs ~30-50 us per edge (10-90 %), so each phase lasts at least PULSE_T_MIN_US.
#define PULSE_F_MIN     0.1f      // Hz
#define PULSE_F_MAX     1000.0f   // Hz
#define PULSE_D_MIN     1.0f      // % duty (time at the setpoint)
#define PULSE_D_MAX     99.0f     // %
#define PULSE_T_MIN_US  100.0f    // us, shortest high or low phase

// ---------------------------------------------------------------- timing
#define CONTROL_PERIOD_MS  50
#define DISPLAY_PERIOD_MS  200
#define HISTORY_LEN        600     // RAM history samples (1 s each -> 10 min)
