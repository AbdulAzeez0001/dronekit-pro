/*
 * DroneKit Pro flight controller (fc board) - Betaflight hardware config.
 * GPLv3, see ../../../README.md.
 *
 * Format: Betaflight 4.5's config.h (the betaflight/config repository).
 * Build it with:  make CONFIG=DRONEKITPRO   (after copying this folder into
 * the config repo's configs/), or paste the CLI in ../../cli-defaults.txt
 * onto a cloud build that has the ICM-42688-P driver.
 *
 * STATUS: only the gyro block is written. Motors, UARTs, baro, ADC, LED and
 * beeper follow hardware/stm32f405-pinmap.md and are still to do.
 * Check the define names against the Betaflight release you build; they
 * change between versions.
 */

#pragma once

#define FC_TARGET_MCU       STM32F405
#define BOARD_NAME          DRONEKITPRO
#define MANUFACTURER_ID     DKPR

/* --- Gyro + accelerometer: TDK ICM-42688-P (U80) on SPI1 ---------------
 *
 * Wiring checked against hardware/board/fc.kicad_pcb (2026-11-24):
 *   SCLK pin 13 -> PA5, SDO pin 1 -> PA6, SDI pin 14 -> PA7,
 *   CS pin 12 -> PA4 (10k pull-up), INT1 pin 4 -> PC4 (EXTI4).
 * SPI1 carries only the gyro.
 *
 * Alignment: U80 is on the BOTTOM of the board (KiCad rotation 0), so the
 * chip's axes are x forward, y right, z down: a 180 degree roll flip.
 * Derivation and the bench check are in ../../cli-defaults.txt.
 * Bench-check before the first flight.
 */
#define USE_GYRO
#define USE_ACC
#define USE_GYRO_SPI_ICM42688P
#define USE_ACC_SPI_ICM42688P

#define USE_SPI_DEVICE_1
#define SPI1_SCK_PIN            PA5
#define SPI1_SDI_PIN            PA6
#define SPI1_SDO_PIN            PA7

#define GYRO_1_SPI_INSTANCE     SPI1
#define GYRO_1_CS_PIN           PA4
#define GYRO_1_EXTI_PIN         PC4
#define GYRO_1_ALIGN            CW180_DEG_FLIP

/* One gyro only. */
#define DEFAULT_GYRO_TO_USE     GYRO_CONFIG_USE_GYRO_1
