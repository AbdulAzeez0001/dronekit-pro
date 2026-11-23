# STM32F405RGT6 pin map — DroneKit Pro

Proposed complete resource allocation for the custom Betaflight target, with the
dual-boot signals slotted into pins nothing else uses. No pin is double-booked.

The one item still to verify is DMA stream allocation (see bottom) — pin
assignment is conflict-free, but F405 DMA sharing must be checked when the
Betaflight target is built.

## Dual-boot signals (the reconciliation)

| Signal | Pin | Direction | Why this pin |
|---|---|---|---|
| MODE_SENSE | PC13 | input | Low-drive pin, fine for a passive input. Unused by Betaflight. |
| ESP_EN | PB12 | output (push-pull) | Full-drive output needed to drive ESP32 EN. Free (SPI2_NSS, unused). |
| BRIDGE_TX | PA9 | USART1_TX | RC receiver uses USART2, so USART1 is free. |
| BRIDGE_RX | PA10 | USART1_RX | Pair of USART1. |
| STM_BOOT0 | BOOT0 | input (dedicated) | Dedicated pin, driven by ESP32-S3 GPIO41 for OTA. |
| STM_NRST | NRST | input (dedicated) | Dedicated pin, driven by ESP32-S3 GPIO42 for OTA. |

## Full pin allocation

### Fixed / dedicated (see `hardware/stm32/`, which holds the real LQFP64 pin numbers)
| Pin | Function |
|---|---|
| PA11 / PA12 | USB DM / DP via the TS3USB221A switch (USB-C goes to the STM32 in Mode A, to the ESP32-S3 in Mode B); VBUS powers the logic via the power block |
| PA13 / PA14 | SWDIO / SWCLK (SWD pads J91) |
| PH0 / PH1 | 8MHz HSE crystal (OSC_IN / OSC_OUT), 20pF load caps |
| NRST | reset (STM_NRST) |
| BOOT0 | boot select (STM_BOOT0), BOOT button to 3V3 via 1k |
| PB2 | BOOT1, 10k pull-down |
| PB9 | LED0 status LED (active low) |
| VCAP1 / VCAP2 | internal reg caps — 2.2uF each, ESR < 2 ohm |
| VDD/VSS/VDDA/VSSA/VBAT | power (VDDA, VBAT tied to VDD) |

### Gyro — ICM-42688-P on SPI1 (see `hardware/gyro/`)
| Pin | Function |
|---|---|
| PA5 | SPI1_SCK |
| PA6 | SPI1_MISO |
| PA7 | SPI1_MOSI |
| PA4 | SPI1_CS (gyro, 10k pull-up) |
| PC4 | gyro INT (EXTI4) |

### RC — optional serial ELRS receiver on USART2 (see `hardware/elrs/`)
| Pin | Function |
|---|---|
| PA2 | USART2_TX -> receiver RX (J60, via 100R) |
| PA3 | USART2_RX <- receiver TX (J60, via 100R) |

The receiver is an add-on the user buys and solders to J60. Betaflight:
UART2 = Serial Rx, provider CRSF.

### Baro — SPA06-003 on I2C1, address 0x76 (see `hardware/baro/`)
| Pin | Function |
|---|---|
| PB6 | I2C1_SCL (5.1k pull-up, on the baro block) |
| PB7 | I2C1_SDA (5.1k pull-up, on the baro block) |

### Motors — 4 brushed MOSFET channels, plain PWM, all on TIM3
| Pin | Function |
|---|---|
| PB0 | M1 rear right (TIM3_CH3) |
| PB1 | M2 front right (TIM3_CH4) |
| PB4 | M3 rear left (TIM3_CH1) |
| PB5 | M4 front left (TIM3_CH2) |

One timer for all four gives one shared brushed PWM frequency. Each pin
drives an AO3400A gate through 22R, with a 10k pull-down (see
`hardware/motors/`).

### Sensing + misc
| Pin | Function |
|---|---|
| PC1 | VBAT sense (ADC), 10k/1k divider = vbat_scale 110; also detects 1S vs 2S |
| PC2 | current sense (ADC) — not fitted (no shunt on the board yet); free |
| PB8 | buzzer / Betaflight BEEPER (AO3400A low-side, see `hardware/buzzer/`) |
| PA8 | LED strip (WS2812, TIM1_CH1) -> header J132 |

### Expansion headers (see `hardware/expansion/`)
| Pin | Function |
|---|---|
| PB6 / PB7 | I2C1 SCL / SDA -> SENSOR header J130 (shared with the baro) |
| PB10 / PB11 | USART3 TX / RX -> UART3 header J131 |
| PA8 | LED strip -> LED header J132 |
| PC6 / PC7 / PC8 / PC9 | TIM8_CH1-4 -> PWM header J133 |

All header signals go through 100R series resistors. The ESP32-S3 has two
more headers (CODE-I2C on GPIO47/48, CODE-IO on GPIO21/38/39/40).

### Bridge + dual-boot control
| Pin | Function |
|---|---|
| PA9 | BRIDGE_TX (USART1_TX) -> ESP32-S3 GPIO1 |
| PA10 | BRIDGE_RX (USART1_RX) <- ESP32-S3 GPIO2 |
| PC13 | MODE_SENSE (input); the same net steers the USB switch |
| PB12 | ESP_EN (output) |

### Still free
PA0, PA1, PC0, PC2, PC3 (ADC-capable), PC5, PD2, PB3, PC14, PC15.
SPI3 is also free now (PC10 SCK, PC11 MISO, PC12 MOSI, plus PA15, PB13,
PB14, PB15 for chip-selects / interrupts), e.g. for an SPI expansion header.
Avoid PB2 (BOOT1). PC13/14/15 are low-drive — inputs only.

## Bus summary (no conflicts)
- SPI1: gyro
- SPI3: free (expansion)
- I2C1: baro (0x76), shared with the SENSOR header (J130)
- USART1: ESP32 bridge
- USART2: optional ELRS receiver (serial CRSF)
- USART3: UART3 expansion header (J131)
- TIM1: LED strip (PA8); TIM8: PWM header (PC6-PC9)
- TIM3: four brushed motors (PWM)
- USB, SWD, crystal: dedicated

## Open verification item — DMA

Pin assignment is conflict-free. DMA is the remaining check. With brushed
motors, TIM3 runs plain PWM and needs no DMA (the old DSHOT design did), so
the load is lighter. The SPI buses and USART1 still request DMA streams, and
DMA1/DMA2 streams are shared. When building the Betaflight target, confirm
the allocation for SPI1 (gyro) + USART1 (bridge) + USART2 (receiver) (+ the LED strip on
TIM1 if used). Validate against the F405 DMA table and test, do not assume.

## To do when building the target
- [ ] Encode this map in the Betaflight custom target (resource assignments).
- [ ] Run the DMA check above.
- [ ] Add the MODE_SENSE read + ESP_EN drive to target init (custom code).
