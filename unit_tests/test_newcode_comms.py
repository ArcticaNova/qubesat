import sys
import types
import unittest

sys.path.insert(0, './NewCode')


class FakeRadio:
    """Mimics pycubed_rfm9x's RadioHead header handling: send() prepends a 4-byte
    header (destination, node, identifier, flags); receive() drops packets under
    5 bytes, filters on destination vs node, and strips the header unless
    with_header=True."""

    def __init__(self):
        self.node = 0xFF
        self.destination = 0xFF
        self.identifier = 0
        self.flags = 0
        self.air = []     # every packet sent, exactly as it would appear on air
        self.inbox = []   # on-air packets waiting to be received
        self.regs = {}

    def _write_u8(self, address, val):
        self.regs[address] = val

    def send(self, data, *, keep_listening=False, destination=None, node=None,
             identifier=None, flags=None):
        assert 0 < len(data) <= 252
        header = bytes([
            self.destination if destination is None else destination,
            self.node if node is None else node,
            self.identifier if identifier is None else identifier,
            self.flags if flags is None else flags,
        ])
        self.air.append(header + bytes(data))
        return True

    def receive(self, *, keep_listening=True, with_header=False, with_ack=False,
                timeout=None, debug=False, view=False):
        if not self.inbox:
            return None
        packet = self.inbox.pop(0)
        if len(packet) < 5:
            return None
        if self.node != 0xFF and packet[0] != 0xFF and packet[0] != self.node:
            return None
        return bytes(packet if with_header else packet[4:])


# Comms.py does `from pycubed import cubesat`; give it a fake board.
_fake_pycubed = types.ModuleType('pycubed')
_fake_pycubed.cubesat = types.SimpleNamespace(hardware={"Radio1": True}, radio1=FakeRadio())
sys.modules['pycubed'] = _fake_pycubed

import Comms
import tinygs_decoder


class TestNewCodeComms(unittest.TestCase):

    def setUp(self):
        _fake_pycubed.cubesat.radio1 = FakeRadio()
        self.radio = Comms.configure_radio()
        self.comms = Comms.CommsManager(self.radio)
        self.comms.state_code = Comms.STATE_IDLE

    def test_configure_radio_sets_sync_word_and_broadcast_node(self):
        self.assertEqual(self.radio.regs[0x39], 0x12)
        self.assertEqual(self.radio.node, 0xFF)

    def test_beacon_on_air_is_16_bytes_and_decodes(self):
        self.comms.push_telemetry(Comms.build_beacon_packet(Comms.STATE_SCIENCE, 7.4, 25.3, 99))
        self.comms._tx_tick()
        on_air = self.radio.air[-1]
        self.assertEqual(len(on_air), 16)
        self.assertEqual(on_air[0], Comms.HDR_TELEMETRY)
        decoded = tinygs_decoder.decode(on_air)
        self.assertEqual(decoded["state_name"], "SCIENCE")
        self.assertEqual(decoded["battery_v"], 7.4)
        self.assertEqual(decoded["temperature_c"], 25)
        self.assertEqual(decoded["mission_time_s"], 99)

    def test_beacon_with_missing_sensors_encodes_unknown(self):
        packet = Comms.build_beacon_packet(Comms.STATE_IDLE, None, None, 120)
        decoded = tinygs_decoder.decode(bytes([Comms.HDR_TELEMETRY]) + packet)
        self.assertIsNone(decoded["battery_v"])
        self.assertIsNone(decoded["temperature_c"])
        self.assertEqual(decoded["state_name"], "IDLE")

    def test_ground_state_command_round_trip(self):
        ground = FakeRadio()
        received = []
        self.comms.on_state_command = received.append
        Comms.send_raw(ground, Comms.build_state_command(Comms.STATE_COMMS))
        self.radio.inbox.append(ground.air[-1])
        self.assertTrue(self.comms._rx_tick())
        self.assertEqual(received, [Comms.STATE_COMMS])
        self.assertEqual(self.comms.state_code, Comms.STATE_COMMS)

    def test_send_raw_pads_short_packets(self):
        Comms.send_raw(self.radio, bytes([Comms.HDR_AMATEUR, 0x01]))
        self.assertEqual(self.radio.air[-1], bytes([Comms.HDR_AMATEUR, 0x01, 0, 0, 0]))

    def test_fresh_nvm_uses_default_schedule(self):
        for blank in (0x00, 0xFF):
            Comms._nvm[Comms._NVM_CFG_RX] = blank
            Comms._nvm[Comms._NVM_CFG_TX] = blank
            Comms._nvm[Comms._NVM_CFG_CAD] = blank
            config = Comms.CommsConfig()
            self.assertEqual(
                (config.rx_ticks, config.tx_packet_count, config.telem_cadence),
                (Comms.CommsConfig.DEFAULT_RX_TICKS,
                 Comms.CommsConfig.DEFAULT_TX_PACKET_COUNT,
                 Comms.CommsConfig.DEFAULT_TELEM_CADENCE))

    def test_nvm_does_not_overlap_pycubed(self):
        pycubed_bytes = {0, 6, 7, 9, 10, 11, 16}
        ours = {Comms._NVM_S1, Comms._NVM_S2, Comms._NVM_S3, Comms._NVM_CS,
                Comms._NVM_CFG_RX, Comms._NVM_CFG_TX, Comms._NVM_CFG_CAD}
        self.assertFalse(ours & pycubed_bytes)


if __name__ == '__main__':
    unittest.main()
