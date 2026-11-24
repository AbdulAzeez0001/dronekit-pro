/*
 * DroneKit Pro flight controller (fc board) - Betaflight hardware config.
 * GPLv3, see ../../../README.md.
 *
 * Format: Betaflight 4.5's config.h (the betaflight/config repository).
 * Build it with:  make CONFIG=DRONEKITPRO   (after copying this folder into
 * the config repo's configs/), or paste the CLI in ../../cli-defaults.txt
 * onto a cloud build that has the drivers listed below.
 *
 * Source of truth: hardware/stm32f405-pinmap.md. Every pin here was checked
 * against the routed board (hardware/board/fc.kicad_pcb) on 2026-11-24.
 *
 * NOT YET COMPILED. Define names change between Betaflight releases; check
 * them against the release you build. Not done here:
 *   - the dual-boot logic (read MODE_SENSE on PC13 at boot, pick the RC
 *     source) needs custom code, see hardware/dual-boot/;
 *   - the DMA check in hardware/stm32f405-pinmap.md (run `dma show` and
 *     `timer show` in the CLI on the first board).
 */

#pragma once

#define FC_TARGET_MCU       STM32F405
#define BOARD_NAME          DRONEKITPRO
#define MANUFACTURER_ID     DKPR

/* --- Drivers ----------------------------------------------------------- */
#define USE_GYRO
#define USE_ACC
#define USE_GYRO_SPI_ICM42688P
#define USE_ACC_SPI_ICM42688P
#define USE_BARO
#define USE_BARO_DPS310             /* covers the SPA06-003 (hardware/baro/) */

/* --- Status LED, beeper ------------------------------------------------ */
#define LED0_PIN                PB9     /* D90 cathode: active low, Betaflight's default */

#define BEEPER_PIN              PB8     /* AO3400A low-side switch (Q120) */
#define BEEPER_INVERTED                 /* PB8 high = FET on = beep */

/* --- Motors: 4 brushed channels, TIM3 ----------------------------------
 * Betaflight quad-X order: M1 rear right, M2 front right, M3 rear left,
 * M4 front left. Each pin drives an AO3400A gate through 22R.
 */
#define MOTOR1_PIN              PB0     /* TIM3_CH3 */
#define MOTOR2_PIN              PB1     /* TIM3_CH4 */
#define MOTOR3_PIN              PB4     /* TIM3_CH1 */
#define MOTOR4_PIN              PB5     /* TIM3_CH2 */

/* PWM header J133 (TIM8_CH1-4): free outputs, e.g. servos. */
#define SERVO1_PIN              PC6
#define SERVO2_PIN              PC7
#define SERVO3_PIN              PC8
#define SERVO4_PIN              PC9

#define LED_STRIP_PIN           PA8     /* TIM1_CH1 -> header J132 */

/* TIMER_PIN_MAP(index, pin, occurrence, dma option). The occurrence counts
 * the timers a pin can use, from 1 in Betaflight's F4 timer table:
 * PB0/PB1 -> 2 = TIM3 (1 = TIM1/TIM8 N channel), PB4/PB5 -> 1 = TIM3,
 * PC6-PC9 -> 2 = TIM8 (1 = TIM3), PA8 -> 1 = TIM1.
 * Brushed PWM and servos need no DMA (-1); the WS2812 strip does (0).
 */
#define TIMER_PIN_MAPPING \
    TIMER_PIN_MAP( 0, PB0 , 2, -1) \
    TIMER_PIN_MAP( 1, PB1 , 2, -1) \
    TIMER_PIN_MAP( 2, PB4 , 1, -1) \
    TIMER_PIN_MAP( 3, PB5 , 1, -1) \
    TIMER_PIN_MAP( 4, PC6 , 2, -1) \
    TIMER_PIN_MAP( 5, PC7 , 2, -1) \
    TIMER_PIN_MAP( 6, PC8 , 2, -1) \
    TIMER_PIN_MAP( 7, PC9 , 2, -1) \
    TIMER_PIN_MAP( 8, PA8 , 1,  0)

#define DEFAULT_MOTOR_PROTOCOL  MOTOR_PROTOCOL_BRUSHED

/* --- Gyro + accelerometer: TDK ICM-42688-P (U80) on SPI1 ---------------
 * SCLK pin 13 -> PA5, SDO pin 1 -> PA6, SDI pin 14 -> PA7,
 * CS pin 12 -> PA4 (10k pull-up), INT1 pin 4 -> PC4 (EXTI4).
 * SPI1 carries only the gyro.
 *
 * Alignment: U80 is on the BOTTOM of the board (KiCad rotation 0), so the
 * chip's axes are x forward, y right, z down: a 180 degree roll flip.
 * Derivation and the bench check are in ../../cli-defaults.txt.
 * Bench-check before the first flight.
 */
#define USE_SPI_DEVICE_1
#define SPI1_SCK_PIN            PA5
#define SPI1_SDI_PIN            PA6
#define SPI1_SDO_PIN            PA7

#define GYRO_1_SPI_INSTANCE     SPI1
#define GYRO_1_CS_PIN           PA4
#define GYRO_1_EXTI_PIN         PC4
#define GYRO_1_ALIGN            CW180_DEG_FLIP

#define DEFAULT_GYRO_TO_USE     GYRO_CONFIG_USE_GYRO_1

/* --- Baro: Goertek SPA06-003 (U70) on I2C1, address 0x76 ---------------
 * Shared with the SENSOR header J130. 5.1k pull-ups on the baro block.
 */
#define USE_I2C_DEVICE_1
#define I2C1_SCL_PIN            PB6
#define I2C1_SDA_PIN            PB7
#define BARO_I2C_INSTANCE       I2CDEV_1
#define DEFAULT_BARO_DPS310

/* --- UARTs --------------------------------------------------------------
 * UART1: bridge to the ESP32-S3 (MSP), through the B2B connector.
 * UART2: optional ELRS receiver on J60 (CRSF), through 100R each way.
 * UART3: expansion header J131, through 100R each way.
 */
#define USE_VCP
#define UART1_TX_PIN            PA9
#define UART1_RX_PIN            PA10
#define UART2_TX_PIN            PA2
#define UART2_RX_PIN            PA3
#define UART3_TX_PIN            PB10
#define UART3_RX_PIN            PB11

#define SERIALRX_UART           SERIAL_PORT_USART2
#define SERIALRX_PROVIDER       SERIALRX_CRSF
#define MSP_UART                SERIAL_PORT_USART1

/* --- Battery ------------------------------------------------------------
 * PC1 reads VBAT through R15 10k / R16 1k, so vbat_scale 110 (also
 * Betaflight's default). No current sensor is fitted.
 */
#define USE_ADC
#define ADC_VBAT_PIN            PC1
#define DEFAULT_VOLTAGE_METER_SOURCE    VOLTAGE_METER_ADC
#define DEFAULT_CURRENT_METER_SOURCE    CURRENT_METER_NONE
#define DEFAULT_VOLTAGE_METER_SCALE     110

/* --- ESP32-S3 power (ESP_EN on PB12) ------------------------------------
 * Until the dual-boot code exists, PINIO1 lets a switch turn the ESP32-S3
 * on: USER1 (box 40) on an AUX channel. Off by default; the 10k pull-down
 * on ESP_EN keeps it off while the STM32 boots.
 */
#define PINIO1_PIN              PB12
#define PINIO1_BOX              40

/* Not connected: PC13 (MODE_SENSE, read by the future dual-boot code),
 * PB2 (BOOT1), PA11/PA12 (USB via the TS3USB221A switch), PA13/PA14 (SWD). */
