// Host unit tests for the control math: g++ -std=c++17 -I../eload test_control.cpp && ./a.out
#include <cstdio>
#include <cmath>
#include "control.h"

static int fails = 0, checks = 0;
#define NEAR(a, b, tol) do { checks++; double _a = (a), _b = (b); if (std::fabs(_a - _b) > (tol)) { \
    std::printf("FAIL %s:%d  %s = %.6f, expected %.6f\n", __FILE__, __LINE__, #a, _a, _b); fails++; } } while (0)

int main() {
    // per-channel limit: 5 A up to 15 V, then 75 W / V
    NEAR(channelLimit(5), 5.0, 1e-6);
    NEAR(channelLimit(15), 5.0, 1e-6);
    NEAR(channelLimit(30), 2.5, 1e-6);
    NEAR(channelLimit(60), 1.25, 1e-6);
    // modes
    NEAR(modeTarget(MODE_CC, 3.0f, 12), 3.0, 1e-6);
    NEAR(modeTarget(MODE_CP, 60.0f, 12), 5.0, 1e-6);
    NEAR(modeTarget(MODE_CR, 4.0f, 12), 3.0, 1e-6);
    NEAR(modeTarget(MODE_CP, 60.0f, 0.1f), 0.0, 1e-6);       // no division by ~0
    // distribution over 4 channels and the power limit
    float o[N_CH];
    NEAR(distribute(8, 0x0F, 12, o), 8.0, 1e-5); NEAR(o[0], 2.0, 1e-6); NEAR(o[3], 2.0, 1e-6);
    NEAR(distribute(20, 0x0F, 60, o), 5.0, 1e-5);            // 300 W at 60 V
    NEAR(o[1], 1.25, 1e-6);
    NEAR(distribute(6, 0x05, 12, o), 6.0, 1e-5); NEAR(o[1], 0.0, 1e-6); NEAR(o[2], 3.0, 1e-6);
    NEAR(distribute(30, 0x0F, 5, o), 20.0, 1e-5);            // clipped at 4 x 5 A
    NEAR(distribute(5, 0x00, 12, o), 0.0, 1e-6);
    // DAC: 2 A/V -> 5 A = 2.5 V = full scale
    NEAR(dacCode(5.0f, 1, 0), 65535, 0.5);
    NEAR(dacCode(1.0f, 1, 0), 13107, 0.5);
    NEAR(dacCode(0.010f, 1, 0), 131, 0.5);
    NEAR(dacCode(6.0f, 1, 0), 65535, 0.5);                   // saturates
    NEAR(dacCode(1.0f, 1.02f, 0), 13369, 1);
    NEAR(dacCode(-1.0f, 1, 0), 0, 0.1);
    // NTC: 25 C gives 10k in parallel with the 320k A0 divider
    {
        double r = 10000.0 * 320000.0 / (10000.0 + 320000.0);
        double vn = 3.3 * r / (10000.0 + r);
        int raw = (int)std::lround(vn / 3.2 * 1023);
        NEAR(ntcTemperature(raw), 25.0, 0.4);
        double r100 = 10000.0 * std::exp(3950.0 * (1 / 373.15 - 1 / 298.15));   // ~0.95k at 100 C
        double rp = r100 * 320000.0 / (r100 + 320000.0); vn = 3.3 * rp / (10000.0 + rp);
        NEAR(ntcTemperature((int)std::lround(vn / 3.2 * 1023)), 100.0, 2.5);
    }
    NEAR(ntcTemperature(0), 200.0, 0.1);                     // shorted sensor reads hot -> safe
    // fan
    NEAR(fanDuty(20, 0), FAN_MIN_DUTY, 1e-6);
    NEAR(fanDuty(65, 0), 1.0, 1e-6);
    NEAR(fanDuty(20, 300), 1.0, 1e-6);
    // trim converges and stays bounded
    float g = 1.0f;
    for (int k = 0; k < 400; k++) g = trimGain(g, 2.0f, 2.0f / 1.02f * g);   // channel reads 2 % low
    NEAR(g, 1.02, 0.002);
    NEAR(trimGain(1.0f, 2.0f, 1.0f), 1.0, 1e-6);           // 50 % error = transient, ignored
    for (int k = 0; k < 2000; k++) g = trimGain(g, 2.0f, 1.99f);
    NEAR(g <= 1.05f, 1, 0);
    std::printf("%d checks, %d failures\n", checks, fails);
    return fails ? 1 : 0;
}
