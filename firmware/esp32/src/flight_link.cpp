// The link to the STM32 flight controller (MIT).
#include "flight_link.h"

#include "board_pins.h"

namespace {

// RC channel order sent to Betaflight. It matches Betaflight's default
// channel map (AETR1234): roll, pitch, throttle, yaw, then AUX1...
// AUX1 is the arm switch: map ARM to AUX1 high in the Modes tab
// (firmware/betaflight/cli-defaults.txt does this).
enum Channel { CH_ROLL, CH_PITCH, CH_THROTTLE, CH_YAW, CH_AUX1, CH_AUX2, CH_AUX3, CH_AUX4, CH_COUNT };

constexpr uint16_t RC_MIN = 1000, RC_MID = 1500, RC_MAX = 2000;
constexpr uint32_t RC_PERIOD_MS = 20;        // 50 Hz
constexpr uint32_t TLM_PERIOD_MS = 33;       // one request every 33 ms, ~10 Hz per item
constexpr uint32_t FC_LINK_TIMEOUT_MS = 1000;

// Arming only with the throttle at the bottom.
constexpr float ARM_MAX_THROTTLE = 0.05f;

uint16_t stick(float v)  // -1..1 -> 1000..2000
{
    v = constrain(v, -1.0f, 1.0f);
    return uint16_t(RC_MID + v * (RC_MAX - RC_MID));
}

uint16_t throttle(float v)  // 0..1 -> 1000..2000
{
    v = constrain(v, 0.0f, 1.0f);
    return uint16_t(RC_MIN + v * (RC_MAX - RC_MIN));
}

} // namespace

void FlightLink::begin()
{
    // Leave the STM32 running its flash firmware: BOOT0 low, NRST released.
    pinMode(PIN_STM_BOOT0, OUTPUT);
    digitalWrite(PIN_STM_BOOT0, LOW);
    pinMode(PIN_STM_NRST, INPUT);

    port_.begin(Serial1, PIN_BRIDGE_RX, PIN_BRIDGE_TX, BRIDGE_BAUD);
    port_.send(msp::API_VERSION);
}

void FlightLink::setSticks(const Sticks &s)
{
    sticks_ = s;
}

bool FlightLink::requestArm(const char *&why)
{
    if (sticks_.throttle > ARM_MAX_THROTTLE) {
        why = "throttle must be at the bottom to arm";
        return false;
    }
    if (!tlm_.fcLink) {
        why = "no link to the flight controller";
        return false;
    }
    armed_ = true;
    why = "";
    return true;
}

void FlightLink::disarm()
{
    armed_ = false;
}

void FlightLink::controlLost()
{
    // No pilot: cut throttle and disarm. A 1S whoop simply drops, which is
    // the safest outcome indoors.
    sticks_ = Sticks{};
    armed_ = false;
}

void FlightLink::loop()
{
    const uint32_t now = millis();

    msp::Frame f;
    while (port_.poll(f)) {
        lastReplyMs_ = now;
        handle(f);
    }
    tlm_.fcLink = lastReplyMs_ != 0 && (now - lastReplyMs_) < FC_LINK_TIMEOUT_MS;

    if (now - lastRcMs_ >= RC_PERIOD_MS) {
        lastRcMs_ = now;
        sendRc();
    }
    if (now - lastTlmMs_ >= TLM_PERIOD_MS) {
        lastTlmMs_ = now;
        requestTelemetry();
    }
}

void FlightLink::sendRc()
{
    uint16_t ch[CH_COUNT];
    ch[CH_ROLL] = stick(sticks_.roll);
    ch[CH_PITCH] = stick(sticks_.pitch);
    ch[CH_YAW] = stick(sticks_.yaw);
    // Disarmed: hold the throttle at the bottom whatever the client sends.
    ch[CH_THROTTLE] = armed_ ? throttle(sticks_.throttle) : RC_MIN;
    ch[CH_AUX1] = armed_ ? RC_MAX : RC_MIN;
    ch[CH_AUX2] = RC_MIN;
    ch[CH_AUX3] = RC_MIN;
    ch[CH_AUX4] = RC_MIN;

    uint8_t payload[CH_COUNT * 2];
    for (int i = 0; i < CH_COUNT; i++) {
        payload[2 * i] = uint8_t(ch[i] & 0xff);
        payload[2 * i + 1] = uint8_t(ch[i] >> 8);
    }
    port_.send(msp::SET_RAW_RC, payload, sizeof(payload));
}

void FlightLink::requestTelemetry()
{
    static const uint8_t cycle[] = {msp::ATTITUDE, msp::ANALOG, msp::STATUS_EX};
    port_.send(cycle[tlmStep_]);
    tlmStep_ = uint8_t((tlmStep_ + 1) % sizeof(cycle));
    if (tlm_.apiMajor == 0 && tlmStep_ == 0) {
        port_.send(msp::API_VERSION);
    }
}

void FlightLink::handle(const msp::Frame &f)
{
    if (f.error) {
        return;
    }
    const uint8_t *p = f.payload;
    switch (f.cmd) {
    case msp::API_VERSION:
        // protocol version, API major, API minor
        if (f.size >= 3) {
            tlm_.apiMajor = p[1];
            tlm_.apiMinor = p[2];
        }
        break;
    case msp::ATTITUDE:
        // roll, pitch (0.1 deg), heading (deg)
        if (f.size >= 6) {
            tlm_.roll = msp::i16(p) / 10.0f;
            tlm_.pitch = msp::i16(p + 2) / 10.0f;
            tlm_.heading = msp::i16(p + 4);
        }
        break;
    case msp::ANALOG:
        // vbat (0.1 V), mAh drawn, RSSI, amperage, then vbat (0.01 V) from
        // API 1.41 on. Use the finer one when it's there.
        if (f.size >= 9) {
            tlm_.vbat = msp::u16(p + 7) / 100.0f;
        } else if (f.size >= 1) {
            tlm_.vbat = p[0] / 10.0f;
        }
        break;
    case msp::STATUS_EX: {
        // cycleTime u16, i2cErrors u16, sensors u16, flight modes u32,
        // PID profile u8, system load u16, PID profile count u8,
        // rate profile u8, extra mode byte count n u8, n bytes,
        // arming-disable flag count u8, arming-disable flags u32.
        // ARM is always the first box, so bit 0 of the modes is "armed".
        if (f.size >= 10) {
            tlm_.fcArmed = (msp::u32(p + 6) & 1u) != 0;
        }
        if (f.size >= 16) {
            const uint8_t n = p[15];
            const size_t flagsAt = 16 + n + 1;
            if (f.size >= flagsAt + 4) {
                tlm_.armingDisabled = msp::u32(p + flagsAt);
            }
        }
        break;
    }
    default:
        break;
    }
}
