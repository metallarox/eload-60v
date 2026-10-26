#include "web.h"
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPUpdateServer.h>
#include <ESP8266mDNS.h>
#include <ArduinoOTA.h>
#include <LittleFS.h>
#include <time.h>
#include <Updater.h>
#include "config.h"
#include "load.h"
#include "logger.h"
#include "settings.h"
#include "webpage.h"

static ESP8266WebServer server(80);
static ESP8266HTTPUpdateServer updater;
static bool apMode = false;
static char apName[20];

String wifiInfo() {
    if (apMode) return String("AP ") + apName;
    return WiFi.localIP().toString();
}

void wifiBegin() {
    WiFi.persistent(false);
    WiFi.hostname(settings.hostname);
    snprintf(apName, sizeof apName, "ELOAD-%06X", ESP.getChipId() & 0xFFFFFF);
    if (settings.ssid[0]) {
        WiFi.mode(WIFI_STA);
        WiFi.begin(settings.ssid, settings.pass);
        uint32_t t0 = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) delay(100);
    }
    if (WiFi.status() == WL_CONNECTED) {
        apMode = false;
        configTime("CET-1CEST,M3.5.0,M10.5.0/3", "pool.ntp.org", "time.google.com");
    } else {
        apMode = true;                                        // setup network: connect and open http://192.168.4.1
        WiFi.mode(WIFI_AP);
        WiFi.softAP(apName, "eload1234");
    }
    MDNS.begin(settings.hostname);
    ArduinoOTA.setHostname(settings.hostname);
    ArduinoOTA.onStart([]() { loadSetOutput(false); logStop(); });   // never update with the load on
    ArduinoOTA.begin();
}

// ---------------------------------------------------------------- helpers
static void sendJson(const String &s, int code = 200) {
    server.sendHeader("Cache-Control", "no-store");
    server.send(code, "application/json", s);
}
static void ok(const char *msg = "ok") { sendJson(String("{\"ok\":true,\"msg\":\"") + msg + "\"}"); }
static void err(const char *msg) { sendJson(String("{\"ok\":false,\"msg\":\"") + msg + "\"}", 400); }

static void handleStatus() {
    static const char *M[] = {"CC", "CP", "CR"};
    char b[1400]; char ts[32]; timeString(ts, sizeof ts);
    int n = snprintf(b, sizeof b,
        "{\"fw\":\"%s\",\"up\":%lu,\"time\":\"%s\",\"v\":%.4f,\"i\":%.4f,\"p\":%.3f,"
        "\"ich\":[%.4f,%.4f,%.4f,%.4f],\"pch\":[%.3f,%.3f,%.3f,%.3f],\"icmd\":[%.4f,%.4f,%.4f,%.4f],"
        "\"tdie\":[%.1f,%.1f,%.1f,%.1f],\"ina\":[%d,%d,%d,%d],\"t\":%.1f,\"fan\":%.2f,\"rpm\":%u,"
        "\"wh\":%.4f,\"ah\":%.4f,\"out\":%d,\"mode\":\"%s\",\"set\":%.4f,\"setmax\":%.1f,\"mask\":%u,"
        "\"vcut\":%.3f,\"trim\":%d,\"gain\":[%.4f,%.4f,%.4f,%.4f],\"trip\":\"%s\",\"tripch\":%d,"
        "\"log\":{\"on\":%d,\"lines\":%lu,\"bytes\":%lu,\"int\":%u,\"free\":%lu},"
        "\"wifi\":{\"ap\":%d,\"ssid\":\"%s\",\"rssi\":%d,\"ip\":\"%s\",\"host\":\"%s\"}}",
        FW_VERSION, (unsigned long)(millis() / 1000), ts, load.v, load.iTot, load.pTot,
        load.i[0], load.i[1], load.i[2], load.i[3], load.p[0], load.p[1], load.p[2], load.p[3],
        load.iCmd[0], load.iCmd[1], load.iCmd[2], load.iCmd[3],
        load.tDie[0], load.tDie[1], load.tDie[2], load.tDie[3],
        load.inaOk[0], load.inaOk[1], load.inaOk[2], load.inaOk[3], load.tSpreader, load.fan, load.rpm,
        load.wh, load.ah, load.out, M[load.mode], load.set, setMax(load.mode), settings.mask,
        settings.vCutoff, settings.autoTrim, settings.gain[0], settings.gain[1], settings.gain[2], settings.gain[3],
        tripName(load.trip), load.tripCh,
        logActive(), (unsigned long)logLines(), (unsigned long)logBytes(), settings.logInterval, (unsigned long)fsFree(),
        apMode, apMode ? apName : settings.ssid, apMode ? 0 : WiFi.RSSI(), wifiInfo().c_str(), settings.hostname);
    if (n >= (int)sizeof b) { err("status too long"); return; }
    sendJson(b);
}

static void handleHistory() {
    server.setContentLength(CONTENT_LENGTH_UNKNOWN);
    server.sendHeader("Cache-Control", "no-store");
    server.send(200, "application/json", "");
    char b[64];
    snprintf(b, sizeof b, "{\"t0\":%lu,\"dt\":1,\"s\":[", (unsigned long)histT0());
    server.sendContent(b);
    String chunk; chunk.reserve(1100);
    uint16_t n = histCount();
    for (uint16_t k = 0; k < n; k++) {
        const HistSample &s = histAt(k);
        snprintf(b, sizeof b, "%s[%u,%u,%u,%d]", k ? "," : "", s.v_cV, s.i_mA, s.p_dW, s.t);
        chunk += b;
        if (chunk.length() > 1000) { server.sendContent(chunk); chunk = ""; }
    }
    chunk += "]}";
    server.sendContent(chunk);
    server.sendContent("");
}

static void handleSet() {
    if (server.hasArg("clear")) loadClearTrip();
    if (server.hasArg("reset")) loadResetCounters();
    if (server.hasArg("mask")) settings.mask = server.arg("mask").toInt() & 0x0F;
    if (server.hasArg("vcut")) settings.vCutoff = max(0.0f, server.arg("vcut").toFloat());
    if (server.hasArg("trim")) settings.autoTrim = server.arg("trim").toInt() != 0;
    if (server.hasArg("mode")) {
        String m = server.arg("mode"); Mode nm = m == "CP" ? MODE_CP : (m == "CR" ? MODE_CR : MODE_CC);
        if (nm != load.mode) {
            if (load.out) { err("turn the output off before changing mode"); return; }
            loadSetMode(nm, 0);
        }
    }
    if (server.hasArg("set")) loadSetpoint(server.arg("set").toFloat());
    if (server.hasArg("out")) {
        if (!loadSetOutput(server.arg("out").toInt() != 0)) { err(tripName(load.trip)); return; }
    }
    if (server.hasArg("save")) settingsSave();
    ok();
}

static void handleLog() {
    String a = server.arg("action");
    if (a == "start") { if (!logStart(server.arg("interval").toInt())) { err("cannot open file"); return; } }
    else if (a == "stop") logStop();
    else if (a == "clear") logClear();
    else { err("action?"); return; }
    ok();
}

static void handleCsv() {
    logFlush();                                            // logging continues; the download is a snapshot
    File f = LittleFS.open(logPath(), "r");
    if (!f) { server.send(404, "text/plain", "no log"); return; }
    server.sendHeader("Content-Disposition", "attachment; filename=\"eload_log.csv\"");
    server.streamFile(f, "text/csv");
    f.close();
}

static void handleWifi() {
    if (!server.hasArg("ssid")) { err("ssid?"); return; }
    server.arg("ssid").toCharArray(settings.ssid, sizeof settings.ssid);
    server.arg("pass").toCharArray(settings.pass, sizeof settings.pass);
    if (server.hasArg("host") && server.arg("host").length()) server.arg("host").toCharArray(settings.hostname, sizeof settings.hostname);
    settingsSave();
    ok("saved, restarting");
    delay(300);
    loadSetOutput(false);
    ESP.restart();
}

static void handleCal() {
    String a = server.arg("action");
    if (a == "save") settingsSave();
    else if (a == "reset") { for (int c = 0; c < N_CH; c++) { settings.gain[c] = 1; settings.offset[c] = 0; } settingsSave(); }
    else { err("action?"); return; }
    ok();
}

void webBegin() {
    server.on("/", HTTP_GET, []() {
        server.sendHeader("Content-Encoding", "gzip");
        server.send_P(200, "text/html", (const char *)INDEX_HTML_GZ, INDEX_HTML_GZ_LEN);
    });
    server.on("/api/status", HTTP_GET, handleStatus);
    server.on("/api/history", HTTP_GET, handleHistory);
    server.on("/api/set", HTTP_POST, handleSet);
    server.on("/api/log", HTTP_POST, handleLog);
    server.on("/api/wifi", HTTP_POST, handleWifi);
    server.on("/api/cal", HTTP_POST, handleCal);
    server.on("/log.csv", HTTP_GET, handleCsv);
    server.onNotFound([]() { server.send(404, "text/plain", "not found"); });
    updater.setup(&server, "/update");                       // firmware upload page (load is forced off in webLoop)
    server.begin();
    MDNS.addService("http", "tcp", 80);
}

void webLoop() {
    server.handleClient();
    if (Update.isRunning() && load.out) { loadSetOutput(false); logStop(); }   // never flash with the load on
    MDNS.update();
    ArduinoOTA.handle();
}
