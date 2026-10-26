#include "logger.h"
#include <LittleFS.h>
#include <time.h>
#include "load.h"
#include "settings.h"

static HistSample hist[HISTORY_LEN];
static uint16_t hHead = 0, hCount = 0;
static uint32_t tick = 0;
static File logFile;
static bool active = false;
static uint32_t lines = 0, sinceFlush = 0, logT0 = 0;
static const char *PATH = "/log.csv";

const char *logPath() { return PATH; }
bool timeValid() { return time(nullptr) > 1700000000; }
void timeString(char *buf, size_t n) {
    if (timeValid()) { time_t t = time(nullptr); struct tm tm; localtime_r(&t, &tm); strftime(buf, n, "%Y-%m-%d %H:%M:%S", &tm); }
    else snprintf(buf, n, "uptime %lus", (unsigned long)(millis() / 1000));
}

void logBegin() { lines = 0; }

static void histPush() {
    HistSample s;
    s.v_cV = (uint16_t)constrain(lroundf(load.v * 100), 0, 65535);
    s.i_mA = (uint16_t)constrain(lroundf(load.iTot * 1000), 0, 65535);
    s.p_dW = (uint16_t)constrain(lroundf(load.pTot * 10), 0, 65535);
    s.t = (int8_t)constrain(lroundf(load.tSpreader), -100, 127);
    hist[hHead] = s; hHead = (hHead + 1) % HISTORY_LEN;
    if (hCount < HISTORY_LEN) hCount++;
}
uint16_t histCount() { return hCount; }
const HistSample &histAt(uint16_t i) { return hist[(hHead + HISTORY_LEN - hCount + i) % HISTORY_LEN]; }
uint32_t histT0() { return tick - hCount; }   // uptime second of the oldest sample

bool logStart(uint16_t intervalS) {
    logStop();
    settings.logInterval = max<uint16_t>(1, intervalS);
    logFile = LittleFS.open(PATH, "w");
    if (!logFile) return false;
    char ts[32]; timeString(ts, sizeof ts);
    logFile.printf("# %s %s, started %s, interval %u s\n", FW_NAME, FW_VERSION, ts, settings.logInterval);
    logFile.print("time,elapsed_s,output,mode,setpoint,V,I_total_A,P_total_W,I1_A,I2_A,I3_A,I4_A,Wh,Ah,T_spreader_C,trip\n");
    lines = 0; sinceFlush = 0; logT0 = millis(); active = true;
    loadResetCounters();
    return true;
}

void logStop() { if (active) { logFile.close(); active = false; } }
void logFlush() { if (active) { logFile.flush(); sinceFlush = 0; } }
void logClear() { logStop(); LittleFS.remove(PATH); lines = 0; }
bool logActive() { return active; }
uint32_t logLines() { return lines; }
uint32_t logBytes() { if (active) return logFile.size(); File f = LittleFS.open(PATH, "r"); uint32_t s = f ? f.size() : 0; if (f) f.close(); return s; }
uint32_t fsFree() { FSInfo i; LittleFS.info(i); return i.totalBytes - i.usedBytes; }

void logTick() {
    histPush();
    tick++;
    if (!active || (tick % settings.logInterval)) return;
    if (fsFree() < 64 * 1024) { logStop(); return; }                 // keep some room for settings
    char ts[32]; timeString(ts, sizeof ts);
    static const char *M[] = {"CC", "CP", "CR"};
    logFile.printf("%s,%lu,%d,%s,%.4f,%.4f,%.4f,%.3f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.1f,%s\n", ts,
                   (unsigned long)((millis() - logT0) / 1000), load.out, M[load.mode], load.set, load.v, load.iTot,
                   load.pTot, load.i[0], load.i[1], load.i[2], load.i[3], load.wh, load.ah, load.tSpreader,
                   tripName(load.trip));
    lines++;
    if (++sinceFlush >= 10) { logFile.flush(); sinceFlush = 0; }
}
