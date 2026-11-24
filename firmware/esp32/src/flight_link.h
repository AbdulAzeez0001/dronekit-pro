// The link to the STM32 flight controller: RC out, telemetry in (MIT).
//
// The ESP32-S3 only runs in Code mode, where Betaflight takes its RC from
// MSP. This sends MSP_SET_RAW_RC at 50 Hz all the time, so Betaflight sees
// a live receiver. If this firmware stops, Betaflight's own RC failsafe
// takes over.
#pragma once

#include <Arduino.h>

#include "msp.h"

struct Telemetry {
    bool fcLink = false;          // replies from the STM32 in the last second
    uint16_t apiMajor = 0, apiMinor = 0;
    bool fcArmed = false;         // Betaflight's own armed state
    uint32_t armingDisabled = 0;  // Betaflight arming-disable flags (0 = may arm)
    float vbat = 0;               // V
    float roll = 0, pitch = 0;    // deg
    float heading = 0;            // deg
};

class FlightLink {
public:
    // Control inputs, already range-checked by the caller.
    //   roll, pitch, yaw: -1..1   throttle: 0..1
    struct Sticks {
        float roll = 0, pitch = 0, yaw = 0, throttle = 0;
    };

    void begin();
    void loop();                 // call often

    void setSticks(const Sticks &s);

    // Arming. requestArm() refuses unless throttle is low; the reason goes
    // in `why`. disarm() always works. Betaflight applies its own checks too.
    bool requestArm(const char *&why);
    void disarm();

    // Called when the controlling client goes quiet or disconnects.
    void controlLost();

    bool armCommanded() const { return armed_; }
    const Telemetry &telemetry() const { return tlm_; }

private:
    void sendRc();
    void requestTelemetry();
    void handle(const msp::Frame &f);

    msp::Port port_;
    Sticks sticks_;
    bool armed_ = false;
    uint32_t lastRcMs_ = 0;
    uint32_t lastTlmMs_ = 0;
    uint32_t lastReplyMs_ = 0;
    uint8_t tlmStep_ = 0;
    Telemetry tlm_;
};
