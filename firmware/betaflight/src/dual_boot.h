/*
 * DroneKit Pro dual-boot: pick Fly or Code mode from the boot switch.
 * GPLv3 (Betaflight derivative), see ../../README.md.
 * Design: hardware/dual-boot/dual-boot-design.md.
 */

#pragma once

typedef enum {
    DUAL_BOOT_FLY = 0,  // Mode A: RC from the ELRS receiver, ESP32-S3 held off
    DUAL_BOOT_CODE,     // Mode B: RC from the ESP32-S3 over MSP, ESP32-S3 on
} dualBootMode_e;

// Read the boot switch once, power the ESP32-S3 (or keep it off) and pick
// the receiver. Call after the config is loaded and before rxInit().
void dualBootInit(void);

dualBootMode_e dualBootMode(void);
