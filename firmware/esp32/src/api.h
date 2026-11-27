// WebSocket JSON API, version 1 (MIT). Keep it stable, or bump API_VERSION.
//
// Endpoint: ws://192.168.4.1/ws, text frames, one JSON object each.
//
// Client -> drone
//   {"type":"control","roll":0,"pitch":0,"yaw":0,"throttle":0}
//        roll/pitch/yaw -1..1, throttle 0..1. Send at least every 200 ms.
//        The first client to send control becomes the pilot; others get
//        an error until it lets go (disconnects or goes quiet for 500 ms).
//   {"type":"arm"}      pilot only; throttle must be at the bottom
//   {"type":"disarm"}   any client
//   {"type":"kill"}     any client: disarm now and drop the pilot
//
// Drone -> client
//   {"type":"hello","api":1,"fw":"0.1.0","mode":"code","client_id":3}
//        on connect. client_id identifies this connection.
//   {"type":"telemetry","pilot_id":3,"armed_cmd":false,"armed":false,
//    "arming_disabled":0,"fc_link":true,"vbat":3.95,
//    "roll":0.0,"pitch":0.0,"heading":0}                         10 Hz
//        pilot_id: the pilot's client_id (0 = nobody). armed_cmd: what the
//        ESP32 asks for. armed: what Betaflight reports.
//        arming_disabled: Betaflight's arming-disable flags (0 = may arm).
//   {"type":"event","msg":"..."}    e.g. pilot lost, disarmed
//   {"type":"error","msg":"..."}    a command was refused
#pragma once

#include <stdint.h>

constexpr int API_VERSION = 1;
constexpr const char *FW_VERSION = "0.1.0";

constexpr uint32_t CONTROL_TIMEOUT_MS = 500;

struct Command {
    enum Kind : uint8_t { Control, Arm, Disarm, Kill, Disconnect } kind;
    uint32_t client;
    float roll, pitch, yaw, throttle;
};
