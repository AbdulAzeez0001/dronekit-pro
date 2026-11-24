// DroneKit Pro vision board: ESP32-S3-WROOM-1 pins (MIT).
// Checked against hardware/board/vision.kicad_pcb on 2026-11-24.
#pragma once

// UART bridge to the STM32 (Betaflight MSP on its UART1, 115200).
constexpr int PIN_BRIDGE_RX = 1;    // module pad 39, net BRIDGE_TX (STM32 PA9 -> here)
constexpr int PIN_BRIDGE_TX = 2;    // module pad 38, net BRIDGE_RX (here -> STM32 PA10)
constexpr unsigned long BRIDGE_BAUD = 115200;

// STM32 flash control. Left alone in normal running:
//   BOOT0 driven low (it also has a 10k pull-down on fc),
//   NRST released (high impedance; the STM32 has its own pull-up).
constexpr int PIN_STM_BOOT0 = 41;   // module pad 34
constexpr int PIN_STM_NRST = 42;    // module pad 35

// Expansion headers (all through 100R).
constexpr int PIN_CODE_I2C_SDA = 47; // J134, 4.7k pull-ups on the board
constexpr int PIN_CODE_I2C_SCL = 48;
constexpr int PIN_CODE_IO21 = 21;    // J135
constexpr int PIN_CODE_IO38 = 38;
constexpr int PIN_CODE_IO39 = 39;
constexpr int PIN_CODE_IO40 = 40;

// Camera (OV2640 on J30) - not used yet. The Y2..Y9 order depends on the
// J30 connector's contact side, which isn't confirmed. See
// hardware/camera/camera-design.md before using these.
constexpr int PIN_CAM_SIOD = 4;
constexpr int PIN_CAM_SIOC = 5;
constexpr int PIN_CAM_VSYNC = 6;
constexpr int PIN_CAM_HREF = 7;
constexpr int PIN_CAM_XCLK = 15;
constexpr int PIN_CAM_PCLK = 13;
constexpr int PIN_CAM_PWDN = 14;
constexpr int PIN_CAM_Y2 = 11;
constexpr int PIN_CAM_Y3 = 9;
constexpr int PIN_CAM_Y4 = 8;
constexpr int PIN_CAM_Y5 = 10;
constexpr int PIN_CAM_Y6 = 12;
constexpr int PIN_CAM_Y7 = 18;
constexpr int PIN_CAM_Y8 = 17;
constexpr int PIN_CAM_Y9 = 16;

// Never drive the strapping pins GPIO0/3/45/46 (hardware/dual-boot/).
