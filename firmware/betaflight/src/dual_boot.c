/*
 * DroneKit Pro dual-boot: pick Fly or Code mode from the boot switch.
 * GPLv3 (Betaflight derivative), see ../../README.md.
 * Design: hardware/dual-boot/dual-boot-design.md.
 *
 * Hardware (checked against fc.kicad_pcb and vision.kicad_pcb, 2026-11-24):
 *   MODE_SENSE (PC13 on fc): 10k pull-up to +3V3_SYS and 100 nF on the
 *     vision board; SW1 pulls it to GND.
 *       SW1 closed -> LOW  -> Mode A, Fly
 *       SW1 open   -> HIGH -> Mode B, Code
 *     The same net steers the USB switch (U92) in hardware, so USB follows
 *     the switch whatever this code does.
 *   ESP_EN (PB12 on fc): 10k pull-down and 100 nF on the vision board.
 *     LOW = ESP32-S3 held off, HIGH = it boots.
 *
 * Failure modes, all ending in Fly with the ESP32-S3 off:
 *   - before this runs, PB12 floats and the 10k pull-down holds EN low;
 *   - with the vision board unplugged, PC13's internal pull-down reads LOW.
 *     With the board fitted, the 10k pull-up against the ~40k internal
 *     pull-down still reads about 2.6 V, a clear HIGH.
 *
 * The mode is read once at boot. Flipping the switch later changes nothing
 * until the next power cycle (USB still follows it, since that's hardware).
 */

#include <stdbool.h>
#include <stdint.h>

#include "platform.h"

#ifdef USE_DRONEKIT_DUAL_BOOT

#include "config/feature.h"
#include "drivers/io.h"
#include "drivers/time.h"

#include "dual_boot.h"

#ifndef DUAL_BOOT_SENSE_PIN
#error "DUAL_BOOT_SENSE_PIN must be defined (PC13 on DroneKit Pro)"
#endif
#ifndef DUAL_BOOT_ESP_EN_PIN
#error "DUAL_BOOT_ESP_EN_PIN must be defined (PB12 on DroneKit Pro)"
#endif

// MODE_SENSE has a 10k x 100 nF filter (1 ms). Wait several time constants
// after enabling the pin before reading it.
#define DUAL_BOOT_SETTLE_MS 5

// Every receiver feature except MSP. In Code mode the ESP32-S3 is the
// only RC source, so the ELRS receiver is ignored even if it's fitted.
#define DUAL_BOOT_OTHER_RX_FEATURES \
    (FEATURE_RX_SERIAL | FEATURE_RX_PPM | FEATURE_RX_PARALLEL_PWM | FEATURE_RX_SPI)

static dualBootMode_e bootMode = DUAL_BOOT_FLY;

void dualBootInit(void)
{
    // ESP_EN first, driven low, so the ESP32-S3 can't start while we decide.
    IO_t espEn = IOGetByTag(IO_TAG(DUAL_BOOT_ESP_EN_PIN));
    IOInit(espEn, OWNER_PINIO, 1);
    IOConfigGPIO(espEn, IOCFG_OUT_PP);
    IOLo(espEn);

    IO_t sense = IOGetByTag(IO_TAG(DUAL_BOOT_SENSE_PIN));
    IOInit(sense, OWNER_PINIO, 2);
    IOConfigGPIO(sense, IOCFG_IPD);
    delay(DUAL_BOOT_SETTLE_MS);

    bootMode = IORead(sense) ? DUAL_BOOT_CODE : DUAL_BOOT_FLY;

    if (bootMode == DUAL_BOOT_CODE) {
        // Runtime only: the saved config keeps the receiver the user chose,
        // so Fly mode gets it back on the next boot.
        featureDisableImmediate(DUAL_BOOT_OTHER_RX_FEATURES);
        featureEnableImmediate(FEATURE_RX_MSP);
        IOHi(espEn);
    }
    // Fly: leave the configured receiver alone and keep ESP_EN low.
}

dualBootMode_e dualBootMode(void)
{
    return bootMode;
}

#endif // USE_DRONEKIT_DUAL_BOOT
