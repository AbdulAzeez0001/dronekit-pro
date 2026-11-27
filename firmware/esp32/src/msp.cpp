// MSP v1 over a UART (MIT).
#include "msp.h"

namespace msp {

void Port::begin(HardwareSerial &serial, int rxPin, int txPin, unsigned long baud)
{
    serial_ = &serial;
    serial_->begin(baud, SERIAL_8N1, rxPin, txPin);
}

void Port::send(uint8_t cmd, const uint8_t *payload, uint8_t size)
{
    uint8_t header[5] = {'$', 'M', '<', size, cmd};
    uint8_t checksum = size ^ cmd;
    for (uint8_t i = 0; i < size; i++) {
        checksum ^= payload[i];
    }
    serial_->write(header, sizeof(header));
    if (size) {
        serial_->write(payload, size);
    }
    serial_->write(checksum);
}

bool Port::poll(Frame &out)
{
    while (serial_->available()) {
        const uint8_t c = uint8_t(serial_->read());
        switch (state_) {
        case State::Idle:
            if (c == '$') state_ = State::M;
            break;
        case State::M:
            state_ = (c == 'M') ? State::Dir : State::Idle;
            break;
        case State::Dir:
            if (c == '>' || c == '!') {
                frame_.error = (c == '!');
                state_ = State::Size;
            } else {
                state_ = State::Idle;
            }
            break;
        case State::Size:
            if (c > MAX_PAYLOAD) {
                badFrames_++;
                state_ = State::Idle;
                break;
            }
            frame_.size = c;
            checksum_ = c;
            state_ = State::Cmd;
            break;
        case State::Cmd:
            frame_.cmd = c;
            checksum_ ^= c;
            index_ = 0;
            state_ = frame_.size ? State::Payload : State::Checksum;
            break;
        case State::Payload:
            frame_.payload[index_++] = c;
            checksum_ ^= c;
            if (index_ >= frame_.size) state_ = State::Checksum;
            break;
        case State::Checksum:
            state_ = State::Idle;
            if (c == checksum_) {
                out = frame_;
                return true;
            }
            badFrames_++;
            break;
        }
    }
    return false;
}

} // namespace msp
