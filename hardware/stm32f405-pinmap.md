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
| BRIDGE_TX | PA9 | USART1_TX | RC is on UART3, so USART1 is free. |
| BRIDGE_RX | PA10 | USART1_RX | Pair of USART1. |
| STM_BOOT0 | BOOT0 | input (dedicated) | Dedicated pin, driven by ESP32 IO25 for OTA. |
| STM_NRST | NRST | input (dedicated) | Dedicated pin, driven by ESP32 IO26 for OTA. |

## Full pin allocation

### Fixed / dedicated
| Pin | Function |
|---|---|
| PA11 / PA12 | USB DM / DP |
| PA13 / PA14 | SWDIO / SWCLK (programming, keep) |
| PH0 / PH1 | 8MHz HSE crystal (OSC_IN / OSC_OUT) |
| NRST | reset (STM_NRST) |
| BOOT0 | boot select (STM_BOOT0) |
| VCAP1 / VCAP2 | internal reg caps — 2.2uF each, easy to forget |
| VDD/VSS/VDDA/VSSA/VBAT | power |

### Gyro — MPU-6000 on SPI1
| Pin | Function |
|---|---|
| PA5 | SPI1_SCK |
| PA6 | SPI1_MISO |
| PA7 | SPI1_MOSI |
| PA4 | SPI1_CS (gyro) |
| PC4 | gyro INT (EXTI) |

### Blackbox flash — W25Q128 on SPI3
| Pin | Function |
|---|---|
| PC10 | SPI3_SCK |
| PC11 | SPI3_MISO |
| PC12 | SPI3_MOSI |
| PA15 | FLASH_CS (W25Q128 /CS) |

### RC — external CRSF receiver on UART3
| Pin | Function |
|---|---|
| PB10 | RX_UART TX (USART3_TX) |
| PB11 | RX_UART RX (USART3_RX) |

Onboard SPI-ELRS (SX1280) dropped. RC now comes from an external CRSF/ELRS
receiver wired to UART3 on an expansion header. PB10/PB11 were unassigned.
PB13/PB14/PB15 (ex RX RESET/BUSY/DIO1) are now spare.

### Baro — DPS368 on I2C1
| Pin | Function |
|---|---|
| PB6 | I2C1_SCL |
| PB7 | I2C1_SDA |

### Motors — 4-in-1 ESC, DSHOT300, all on TIM3
| Pin | Function |
|---|---|
| PB0 | M1 (TIM3_CH3) |
| PB1 | M2 (TIM3_CH4) |
| PB4 | M3 (TIM3_CH1) |
| PB5 | M4 (TIM3_CH2) |

One timer bank for all four keeps DSHOT DMA clean.

### Sensing + misc
| Pin | Function |
|---|---|
| PC1 | VBAT sense (ADC) |
| PC2 | current sense (ADC) |
| PB8 | buzzer (via FET) |
| PA8 | LED strip (WS2811, TIM1_CH1) — optional |

### Bridge + dual-boot control
| Pin | Function |
|---|---|
| PA9 | BRIDGE_TX (USART1_TX) -> ESP32 IO16 |
| PA10 | BRIDGE_RX (USART1_RX) <- ESP32 IO17 |
| PC13 | MODE_SENSE (input) |
| PB12 | ESP_EN (output) |

### Free for expansion headers
PA0, PA1, PA2, PA3 (a spare UART2 or ADC), PB9, PB13, PB14, PB15, PC0, PC3,
PC5, PC6, PC7, PC8, PC9, PC14, PC15, PD2. Plenty for the six expansion headers.
PB13/PB14/PB15 are spare (freed when onboard SPI-ELRS was dropped).
Avoid PB2 (BOOT1). PC13/14/15 are low-drive — inputs only.

## Bus summary (no conflicts)
- SPI1: gyro
- SPI3: blackbox flash (W25Q128)
- I2C1: baro
- USART1: ESP32 bridge
- USART3: external CRSF receiver
- TIM3: four motors
- USB, SWD, crystal: dedicated

## Open verification item — DMA

Pin assignment is conflict-free. DMA is the remaining check. On the F405,
DSHOT (TIM3), the SPI buses, and USART1 all request DMA streams, and DMA1/DMA2
streams are shared. When building the Betaflight target, confirm the target's
DMA allocation allows TIM3 DSHOT + SPI3 (flash) + SPI1 (gyro) + USART1
(bridge) + USART3 (CRSF RX) simultaneously. If a stream collides, options
are: move motors to TIM8 (PC6-9), or move the flash to SPI2. Validate
against the F405 DMA table and test, do not assume.

## To do when building the target
- [ ] Encode this map in the Betaflight custom target (resource assignments).
- [ ] Run the DMA check above.
- [ ] Add the MODE_SENSE read + ESP_EN drive to target init (custom code).

## Changelog
- 2026-09-07 — Dropped onboard SPI-ELRS (SX1280). SPI3 + PA15 repurposed for the
  W25Q128 blackbox flash (FLASH_CS = PA15). RC moved to an external CRSF receiver
  on UART3 (RX_UART: PB10 TX / PB11 RX). PB13/PB14/PB15 freed to spare.
