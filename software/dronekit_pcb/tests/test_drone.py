"""Tests against the simulated drone. Run from software/dronekit_pcb:

    python -m unittest discover -s tests -v
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dronekit_pcb import (  # noqa: E402
    ArmError, Disarmed, Drone, LinkLost, NotPilot, Sticks, arming_disable_names,
)
from dronekit_pcb.sim import SimDrone  # noqa: E402


class SimTest(unittest.TestCase):
    def setUp(self):
        self.sim = SimDrone()

    def tearDown(self):
        self.sim.stop()

    def drone(self, **kw):
        return Drone(None, transport=self.sim.connect(), **kw)


class TestFlying(SimTest):
    def test_arm_takeoff_land(self):
        with self.drone() as d:
            d.arm()
            self.assertTrue(d.armed)
            d.takeoff(throttle=0.6, ramp=0.3)
            d.hover(0.5)
            self.assertGreater(self.sim.max_altitude, 0)
            d.land(seconds=0.3)
            self.assertTrue(d.wait_for(lambda t: not t.armed, 1))

    def test_move_centres_the_sticks_afterwards(self):
        with self.drone() as d:
            d.arm()
            d.takeoff(0.5, ramp=0.1)
            d.move(pitch=0.4, seconds=0.3)
            self.assertEqual(d.sticks.pitch, 0)
            self.assertAlmostEqual(d.sticks.throttle, 0.5)

    def test_max_throttle_is_enforced(self):
        with self.drone(max_throttle=0.3) as d:
            d.arm()
            d.takeoff(0.9, ramp=0.1)
            self.assertLessEqual(d.sticks.throttle, 0.3)
            time.sleep(0.2)
            self.assertLessEqual(self.sim.sticks["throttle"], 0.3)

    def test_leaving_the_with_block_disarms(self):
        with self.drone() as d:
            d.arm()
            d.takeoff(0.5, ramp=0.1)
        time.sleep(0.2)
        self.assertFalse(self.sim.armed_cmd)
        self.assertFalse(self.sim.fc_armed)

    def test_an_exception_inside_the_with_block_disarms(self):
        with self.assertRaises(RuntimeError):
            with self.drone() as d:
                d.arm()
                raise RuntimeError("student bug")
        time.sleep(0.2)
        self.assertFalse(self.sim.fc_armed)

    def test_telemetry_arrives(self):
        with self.drone() as d:
            self.assertTrue(d.wait_for(lambda t: t.vbat > 3, 1))
            self.assertTrue(d.telemetry.fc_link)


class TestSafety(SimTest):
    def test_firmware_refuses_arm_with_throttle_up(self):
        # Bypass the client's own zeroing to check the firmware rule.
        t = self.sim.connect()
        t.send('{"type":"control","roll":0,"pitch":0,"yaw":0,"throttle":0.5}')
        t.send('{"type":"arm"}')
        time.sleep(0.05)
        self.assertFalse(self.sim.armed_cmd)
        t.close()

    def test_betaflight_block_is_reported_by_name(self):
        self.sim.arming_disabled = (1 << 7) | (1 << 25)   # THROTTLE, ARMSWITCH
        with self.drone() as d:
            with self.assertRaises(ArmError) as cm:
                d.arm(timeout=0.5)
            self.assertIn("THROTTLE", str(cm.exception))
            self.assertIn("ARMSWITCH", str(cm.exception))

    def test_no_fc_link_refuses_arm(self):
        self.sim.fc_link = False
        with self.drone() as d:
            with self.assertRaises(ArmError):
                d.arm(timeout=0.5)

    def test_second_client_cannot_fly_but_can_kill(self):
        with self.drone() as pilot, self.drone() as other:
            pilot.arm()
            with self.assertRaises(NotPilot):
                other.arm()
            pilot.takeoff(0.5, ramp=0.1)
            other.kill()
            with self.assertRaises(Disarmed):
                pilot.hover(1.0)
            self.assertFalse(self.sim.fc_armed)

    def test_pilot_going_quiet_disarms(self):
        t = self.sim.connect()
        t.send('{"type":"control","roll":0,"pitch":0,"yaw":0,"throttle":0}')
        t.send('{"type":"arm"}')
        time.sleep(0.15)
        self.assertTrue(self.sim.fc_armed)
        time.sleep(0.6)            # no control for > 0.5 s
        self.assertFalse(self.sim.armed_cmd)
        self.assertFalse(self.sim.fc_armed)
        t.close()

    def test_pilot_disconnect_disarms(self):
        d = self.drone()
        d.arm()
        d._t.close()               # link drops without a kill
        time.sleep(0.1)
        self.assertFalse(self.sim.fc_armed)
        d._closed.set()

    def test_flight_commands_need_arming(self):
        with self.drone() as d:
            with self.assertRaises(Disarmed):
                d.takeoff(0.5)
            with self.assertRaises(Disarmed):
                d.move(pitch=0.2, seconds=0.1)

    def test_link_loss_is_reported(self):
        d = self.drone()
        d.arm()
        self.sim.stop()
        with self.assertRaises((LinkLost, Disarmed)):
            d.hover(2.0)
        d._closed.set()

    def test_disarmed_sticks_are_clamped(self):
        with self.drone() as d:
            d.set_sticks(Sticks(roll=5, pitch=-5, yaw=2, throttle=3))
            s = d.sticks
            self.assertEqual((s.roll, s.pitch, s.yaw), (1, -1, 1))
            self.assertEqual(s.throttle, d.max_throttle)


class TestFlags(unittest.TestCase):
    def test_names(self):
        self.assertEqual(arming_disable_names(0), [])
        self.assertEqual(arming_disable_names(1 << 2), ["RXLOSS"])
        self.assertEqual(arming_disable_names(1 << 31), ["BIT31"])


if __name__ == "__main__":
    unittest.main()
