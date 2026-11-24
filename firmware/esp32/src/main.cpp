// DroneKit Pro - ESP32-S3 firmware, Code mode (MIT).
//
// Wi-Fi access point at 192.168.4.1, a bench-test page, the WebSocket JSON
// API (api.h), and the MSP link that flies the STM32 (flight_link.h).
// The STM32 only powers this chip up in Code mode (firmware/betaflight/).
#include <Arduino.h>
#include <ArduinoJson.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <WiFi.h>

#include "api.h"
#include "flight_link.h"
#include "index_html.h"

namespace {

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");
FlightLink flight;
QueueHandle_t commands;

// Pilot state: only touched in loop().
uint32_t pilot = 0;           // client id, 0 = nobody
uint32_t lastControlMs = 0;

String ssid, password;

// ---- Wi-Fi password ---------------------------------------------------------
// Made once per board at first boot and kept in flash, so two kits in one
// classroom don't share a password. It's printed on the USB console.

String makePassword()
{
    static const char alphabet[] = "abcdefghjkmnpqrstuvwxyz23456789";  // no 0/o/1/l/i
    String p;
    for (int i = 0; i < 10; i++) {
        p += alphabet[esp_random() % (sizeof(alphabet) - 1)];
    }
    return p;
}

void startWifi()
{
    Preferences prefs;
    prefs.begin("dronekit", false);
    password = prefs.getString("wifi_pass", "");
    if (password.length() < 8) {
        password = makePassword();
        prefs.putString("wifi_pass", password);
    }
    prefs.end();

    WiFi.mode(WIFI_AP);

    uint8_t mac[6];
    WiFi.softAPmacAddress(mac);
    char name[20];
    snprintf(name, sizeof(name), "DroneKit-%02X%02X", mac[4], mac[5]);
    ssid = name;

    WiFi.softAP(ssid.c_str(), password.c_str(), 1, 0, 2);  // channel 1, max 2 clients
}

void printWifi()
{
    Serial.printf("Wi-Fi: %s  password: %s  page: http://%s/\n",
                  ssid.c_str(), password.c_str(), WiFi.softAPIP().toString().c_str());
}

// ---- WebSocket (runs on the network task: only queue commands here) --------

void queue(const Command &c)
{
    xQueueSend(commands, &c, 0);  // full queue: drop; the next control frame follows
}

void onText(AsyncWebSocketClient *client, const char *text, size_t len)
{
    JsonDocument doc;
    if (deserializeJson(doc, text, len)) {
        client->text("{\"type\":\"error\",\"msg\":\"bad JSON\"}");
        return;
    }
    const char *type = doc["type"] | "";
    Command c{};
    c.client = client->id();

    if (strcmp(type, "control") == 0) {
        c.kind = Command::Control;
        c.roll = constrain(doc["roll"] | 0.0f, -1.0f, 1.0f);
        c.pitch = constrain(doc["pitch"] | 0.0f, -1.0f, 1.0f);
        c.yaw = constrain(doc["yaw"] | 0.0f, -1.0f, 1.0f);
        c.throttle = constrain(doc["throttle"] | 0.0f, 0.0f, 1.0f);
    } else if (strcmp(type, "arm") == 0) {
        c.kind = Command::Arm;
    } else if (strcmp(type, "disarm") == 0) {
        c.kind = Command::Disarm;
    } else if (strcmp(type, "kill") == 0) {
        c.kind = Command::Kill;
    } else {
        client->text("{\"type\":\"error\",\"msg\":\"unknown type\"}");
        return;
    }
    queue(c);
}

void onWsEvent(AsyncWebSocket *, AsyncWebSocketClient *client, AwsEventType type,
               void *arg, uint8_t *data, size_t len)
{
    switch (type) {
    case WS_EVT_CONNECT: {
        char hello[128];
        snprintf(hello, sizeof(hello),
                 "{\"type\":\"hello\",\"api\":%d,\"fw\":\"%s\",\"mode\":\"code\",\"client_id\":%lu}",
                 API_VERSION, FW_VERSION, (unsigned long)client->id());
        client->text(hello);
        break;
    }
    case WS_EVT_DISCONNECT: {
        Command c{};
        c.kind = Command::Disconnect;
        c.client = client->id();
        queue(c);
        break;
    }
    case WS_EVT_DATA: {
        auto *info = static_cast<AwsFrameInfo *>(arg);
        // Whole, unfragmented text frames only; the API never needs more.
        if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
            onText(client, reinterpret_cast<const char *>(data), len);
        }
        break;
    }
    default:
        break;
    }
}

// ---- Commands (runs in loop()) ---------------------------------------------

void say(uint32_t client, const char *type, const char *msg)
{
    char buf[128];
    snprintf(buf, sizeof(buf), "{\"type\":\"%s\",\"msg\":\"%s\"}", type, msg);
    if (client) {
        ws.text(client, buf);
    } else {
        ws.textAll(buf);
    }
}

void dropPilot(const char *why)
{
    flight.controlLost();
    pilot = 0;
    say(0, "event", why);
}

void handle(const Command &c)
{
    switch (c.kind) {
    case Command::Control:
        if (pilot != 0 && pilot != c.client) {
            say(c.client, "error", "another client is the pilot");
            return;
        }
        pilot = c.client;
        lastControlMs = millis();
        flight.setSticks({c.roll, c.pitch, c.yaw, c.throttle});
        break;
    case Command::Arm: {
        if (pilot != c.client) {
            say(c.client, "error", "only the pilot can arm; send control first");
            return;
        }
        const char *why = "";
        if (!flight.requestArm(why)) {
            say(c.client, "error", why);
        }
        break;
    }
    case Command::Disarm:
        flight.disarm();
        say(0, "event", "disarmed");
        break;
    case Command::Kill:
        dropPilot("kill: disarmed, pilot dropped");
        break;
    case Command::Disconnect:
        if (c.client == pilot) {
            dropPilot("pilot disconnected: disarmed");
        }
        break;
    }
}

void sendTelemetry()
{
    // One broadcast; each client compares pilot_id with its own client_id.
    // (Walking ws.getClients() here would race the network task.)
    const Telemetry &t = flight.telemetry();
    char buf[256];
    snprintf(buf, sizeof(buf),
             "{\"type\":\"telemetry\",\"pilot_id\":%lu,\"armed_cmd\":%s,\"armed\":%s,"
             "\"arming_disabled\":%lu,\"fc_link\":%s,\"vbat\":%.2f,"
             "\"roll\":%.1f,\"pitch\":%.1f,\"heading\":%.0f}",
             (unsigned long)pilot,
             flight.armCommanded() ? "true" : "false",
             t.fcArmed ? "true" : "false",
             (unsigned long)t.armingDisabled,
             t.fcLink ? "true" : "false",
             t.vbat, t.roll, t.pitch, t.heading);
    ws.textAll(buf);
}

} // namespace

void setup()
{
    Serial.begin(115200);
    commands = xQueueCreate(32, sizeof(Command));

    flight.begin();
    startWifi();

    ws.onEvent(onWsEvent);
    server.addHandler(&ws);

    // The bench page is built into the firmware and always at /bench.
    // The full control panel (software/control-panel) lives in LittleFS,
    // uploaded with `pio run -t uploadfs`. Until it's uploaded, / shows the
    // bench page.
    server.on("/bench", HTTP_GET, [](AsyncWebServerRequest *req) {
        req->send(200, "text/html", INDEX_HTML);
    });
    const bool panel = LittleFS.begin(false) && LittleFS.exists("/index.html");
    if (panel) {
        server.serveStatic("/", LittleFS, "/").setDefaultFile("index.html");
    } else {
        server.on("/", HTTP_GET, [](AsyncWebServerRequest *req) {
            req->send(200, "text/html", INDEX_HTML);
        });
    }
    server.begin();
    Serial.println(panel ? "Control panel: from LittleFS" : "Control panel: not uploaded, serving the bench page");

    printWifi();
}

void loop()
{
    const uint32_t now = millis();

    Command c;
    while (xQueueReceive(commands, &c, 0) == pdTRUE) {
        handle(c);
    }

    if (pilot != 0 && now - lastControlMs > CONTROL_TIMEOUT_MS) {
        dropPilot("pilot went quiet: disarmed");
    }

    flight.loop();

    static uint32_t lastTlm = 0;
    if (now - lastTlm >= 100) {
        lastTlm = now;
        sendTelemetry();
        ws.cleanupClients();
    }

    // Repeat the Wi-Fi details on the console until someone joins.
    static uint32_t lastPrint = 0;
    if (WiFi.softAPgetStationNum() == 0 && now - lastPrint >= 10000) {
        lastPrint = now;
        printWifi();
    }

    delay(1);
}
