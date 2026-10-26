#include "settings.h"
#include <LittleFS.h>
#include "control.h"

Settings settings;

static void setKV(const String &k, const String &v) {
    if (k == "ssid") v.toCharArray(settings.ssid, sizeof settings.ssid);
    else if (k == "pass") v.toCharArray(settings.pass, sizeof settings.pass);
    else if (k == "host") v.toCharArray(settings.hostname, sizeof settings.hostname);
    else if (k == "trim") settings.autoTrim = v.toInt() != 0;
    else if (k == "mask") settings.mask = v.toInt() & 0x0F;
    else if (k == "vcut") settings.vCutoff = v.toFloat();
    else if (k == "logint") settings.logInterval = max(1L, v.toInt());
    else if (k == "pfreq") settings.pulseFreq = pulseClampFreq(v.toFloat());
    else if (k == "pduty") settings.pulseDuty = v.toFloat();
    else if (k.startsWith("gain") && k.length() == 5) settings.gain[(k[4] - '0') & 3] = v.toFloat();
    else if (k.startsWith("off") && k.length() == 4) settings.offset[(k[3] - '0') & 3] = v.toFloat();
}

bool settingsLoad() {
    File f = LittleFS.open("/settings.txt", "r");
    if (!f) return false;
    while (f.available()) {
        String line = f.readStringUntil('\n'); line.trim();
        int eq = line.indexOf('=');
        if (eq > 0) setKV(line.substring(0, eq), line.substring(eq + 1));
    }
    f.close();
    settings.pulseDuty = pulseClampDuty(settings.pulseFreq, settings.pulseDuty);
    return true;
}

bool settingsSave() {
    File f = LittleFS.open("/settings.txt", "w");
    if (!f) return false;
    f.printf("ssid=%s\npass=%s\nhost=%s\ntrim=%d\nmask=%u\nvcut=%.3f\nlogint=%u\n", settings.ssid, settings.pass,
             settings.hostname, settings.autoTrim, settings.mask, settings.vCutoff, settings.logInterval);
    f.printf("pfreq=%.3f\npduty=%.1f\n", settings.pulseFreq, settings.pulseDuty);
    for (int c = 0; c < N_CH; c++) f.printf("gain%d=%.6f\noff%d=%.6f\n", c, settings.gain[c], c, settings.offset[c]);
    f.close();
    return true;
}
