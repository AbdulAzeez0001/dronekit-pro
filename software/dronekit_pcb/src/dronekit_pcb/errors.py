"""Errors raised by dronekit_pcb."""

# Betaflight's arming-disable flags, bit by bit (Betaflight 4.4 / 4.5,
# src/main/fc/runtime_config.h). Other releases may add or move some.
ARMING_DISABLE_FLAGS = [
    "NO_GYRO", "FAILSAFE", "RXLOSS", "BADRX", "BOXFAILSAFE", "RUNAWAY_TAKEOFF",
    "CRASH_DETECTED", "THROTTLE", "ANGLE", "BOOT_GRACE_TIME", "NOPREARM", "LOAD",
    "CALIBRATING", "CLI", "CMS_MENU", "BST", "MSP", "PARALYZE", "GPS",
    "RESC", "RPMFILTER", "REBOOT_REQUIRED", "DSHOT_BITBANG", "ACC_CALIBRATION",
    "MOTOR_PROTOCOL", "ARMSWITCH",
]


def arming_disable_names(flags: int) -> list:
    """Turn Betaflight's arming-disable bit mask into flag names."""
    names = []
    for bit in range(32):
        if flags & (1 << bit):
            names.append(ARMING_DISABLE_FLAGS[bit] if bit < len(ARMING_DISABLE_FLAGS) else f"BIT{bit}")
    return names


class DroneError(Exception):
    """Base class for everything this package raises."""


class LinkLost(DroneError):
    """The link to the drone dropped, or it stopped sending telemetry."""


class NotPilot(DroneError):
    """Another client is flying the drone."""


class ArmError(DroneError):
    """The drone refused to arm."""


class Disarmed(DroneError):
    """The drone disarmed while a flight command was running (kill, link loss,
    another client, or Betaflight's own failsafe)."""
