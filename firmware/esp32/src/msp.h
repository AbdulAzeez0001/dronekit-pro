// MSP v1 over a UART: just enough to talk to Betaflight (MIT).
#pragma once

#include <Arduino.h>

namespace msp {

// Betaflight MSP command ids used here.
constexpr uint8_t API_VERSION = 1;
constexpr uint8_t ATTITUDE = 108;
constexpr uint8_t ANALOG = 110;
constexpr uint8_t STATUS_EX = 150;
constexpr uint8_t SET_RAW_RC = 200;

constexpr size_t MAX_PAYLOAD = 64;

struct Frame {
    uint8_t cmd;
    bool error;        // '!' reply: Betaflight didn't accept the command
    uint8_t size;
    uint8_t payload[MAX_PAYLOAD];
};

class Port {
public:
    void begin(HardwareSerial &serial, int rxPin, int txPin, unsigned long baud);

    // Send a request: "$M<" size cmd payload checksum.
    void send(uint8_t cmd, const uint8_t *payload = nullptr, uint8_t size = 0);

    // Feed received bytes through the parser. Returns true and fills
    // `out` when a whole, valid reply has arrived.
    bool poll(Frame &out);

    uint32_t badFrames() const { return badFrames_; }

private:
    enum class State { Idle, M, Dir, Size, Cmd, Payload, Checksum };

    HardwareSerial *serial_ = nullptr;
    State state_ = State::Idle;
    Frame frame_{};
    uint8_t index_ = 0;
    uint8_t checksum_ = 0;
    uint32_t badFrames_ = 0;
};

// Little-endian helpers for payloads.
inline uint16_t u16(const uint8_t *p) { return uint16_t(p[0] | (p[1] << 8)); }
inline int16_t i16(const uint8_t *p) { return int16_t(u16(p)); }
inline uint32_t u32(const uint8_t *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}

} // namespace msp
