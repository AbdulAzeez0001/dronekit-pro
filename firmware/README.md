# Firmware

## esp32/  (MIT)
WiFi access point, bench-test page (192.168.4.1), WebSocket JSON API v1,
MSP bridge to the STM32. See `esp32/README.md`. Not yet: camera, STM32
flashing from the ESP32, OTA. Develop and test most of this on a spare
ESP32-S3 dev board before the real PCB exists.

## betaflight/  (GPLv3)
Custom Betaflight target for the STM32F405 pinmap, plus the CLI dump from
the kit documentation. This is a Betaflight derivative and is GPLv3.
Test the target logic with Betaflight SITL before flashing hardware.
