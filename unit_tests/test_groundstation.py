"""Ground station uplink tests: commands built on a laptop are accepted by the satellite code."""

import os
import sys
import types
import unittest

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "groundstation"))


class _FakeAES:
    """Stands in for CircuitPython's aesio so Comms.py uses real AES on the desktop."""

    def __init__(self, key, mode):
        self._cipher = Cipher(algorithms.AES(bytes(key)), modes.ECB())

    def encrypt_into(self, src, dest):
        enc = self._cipher.encryptor()
        dest[:] = enc.update(bytes(src)) + enc.finalize()

    def decrypt_into(self, src, dest):
        dec = self._cipher.decryptor()
        dest[:] = dec.update(bytes(src)) + dec.finalize()


sys.modules["aesio"] = types.SimpleNamespace(AES=_FakeAES, MODE_ECB=1)

from unit_tests.test_newcode_comms import Comms  # noqa: E402  (sets up the fake board)
import commands  # noqa: E402
import fsk  # noqa: E402
import pluto_uplink  # noqa: E402


class TestCommands(unittest.TestCase):
    def test_matches_satellite_builders(self):
        self.assertEqual(commands.build_state_command("IDLE"),
                         Comms.build_state_command(Comms.STATE_IDLE))
        self.assertEqual(commands.build_config_command(50, 10, 3),
                         Comms.build_config_command(50, 10, 3))
        self.assertEqual(commands.build_modulation_command(commands.LORA, 60),
                         Comms.build_modulation_command(Comms.LORA, 60))

    def test_satellite_accepts_ground_command(self):
        comms = Comms.CommsManager(Comms.cubesat.radio1, default_modulation=Comms.LORA)
        comms.state_code = Comms.STATE_IDLE
        comms._handle_command(commands.build_state_command("SCIENCE")[1:])
        self.assertEqual(comms.state_code, Comms.STATE_SCIENCE)

    def test_wrong_key_is_rejected(self):
        comms = Comms.CommsManager(Comms.cubesat.radio1, default_modulation=Comms.LORA)
        comms.state_code = Comms.STATE_IDLE
        comms._handle_command(commands.build_state_command("SCIENCE", key=b"x" * 16)[1:])
        self.assertEqual(comms.state_code, Comms.STATE_IDLE)

    def test_fits_in_one_fsk_packet(self):
        self.assertLessEqual(len(commands.build_config_command(50, 10, 3)), fsk.MAX_PAYLOAD)


class TestFsk(unittest.TestCase):
    def test_crc_matches_semtech_reference(self):
        # Semtech AN1200.18 algorithm: poly 0x1021, seed 0x1D0F, inverted.
        self.assertEqual(fsk.crc16_sx127x(b""), (~0x1D0F) & 0xFFFF)
        self.assertNotEqual(fsk.crc16_sx127x(b"\x01"), fsk.crc16_sx127x(b"\x02"))

    def test_frame_layout(self):
        frame = fsk.build_frame(b"\xc0\x01")
        self.assertEqual(frame[:8], bytes([0xAA] * 8))
        self.assertEqual(frame[8:10], b"\x2d\xd4")
        self.assertEqual(frame[10], 2)
        self.assertEqual(len(frame), 8 + 2 + 1 + 2 + 2)

    def test_modulated_burst_round_trips(self):
        packet = commands.build_state_command("IDLE")
        iq = pluto_uplink.burst(packet)
        self.assertEqual(fsk.demodulate(iq, pluto_uplink.SAMPLE_RATE), packet)

    def test_tones_are_plus_minus_25_khz(self):
        iq = fsk.modulate(b"\xff\x00", pluto_uplink.SAMPLE_RATE)
        freq = (np_angle_diff(iq) * pluto_uplink.SAMPLE_RATE / (2 * 3.141592653589793))
        self.assertAlmostEqual(freq[:700].mean(), 25_000, delta=50)
        self.assertAlmostEqual(freq[900:1500].mean(), -25_000, delta=50)

    def test_rejects_oversized_payload(self):
        with self.assertRaises(ValueError):
            fsk.build_frame(bytes(64))


def np_angle_diff(iq):
    import numpy as np
    return np.angle(iq[1:] * np.conj(iq[:-1]))


if __name__ == "__main__":
    unittest.main()
