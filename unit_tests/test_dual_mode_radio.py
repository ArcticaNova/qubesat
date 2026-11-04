import unittest
from unittest.mock import patch
from unit_tests.test_newcode_comms import Comms, FakeRadio
from DualModeRadio import DualModeRadio, LORA, FSK


class RegisterRadio(FakeRadio):
    def __init__(self):
        super().__init__()
        self.regs[1] = 0x89
        self.fsk_regs = {}
        self.fifo = bytearray()
        self.tx_done = True
        self.rx_flags = 0

    def _bank(self, address):
        if 0x0D <= address <= 0x3F and not self.regs[1] & 0x80:
            return self.fsk_regs
        return self.regs

    def _read_u8(self, address):
        if address == 0:
            value = self.fifo[0]
            del self.fifo[0]
            return value
        if address == 0x3F and not self.regs[1] & 0x80:
            return (8 if self.regs[1] & 7 == 3 and self.tx_done else self.rx_flags)
        return self._bank(address).get(address, 0)

    def _write_u8(self, address, value):
        if address == 0x3F and value == 0x10 and not self.regs[1] & 0x80:
            self.fifo.clear()
            self.rx_flags = 0
        else:
            self._bank(address)[address] = value

    def _write_from(self, address, data):
        self.fifo.extend(data)
        self.air.append(bytes(data))

    def _read_into(self, address, buf):
        buf[:] = self.fifo[:len(buf)]
        del self.fifo[:len(buf)]


class TestDualMode(unittest.TestCase):
    def setUp(self):
        self.radio = RegisterRadio()
        self.comms = Comms.CommsManager(self.radio)
        self.comms.state_code = Comms.STATE_IDLE

    def test_startup_listens_for_fsk_uplink(self):
        self.assertEqual(self.comms.modulation, FSK)
        self.assertIsNone(self.comms._lora_deadline)
        self.comms._dual_radio.receive_packet(timeout=0)
        packet = Comms.build_config_command(100, 4, 2)
        self.radio.fifo.extend(bytes([len(packet)]) + packet)
        self.radio.rx_flags = 6
        self.comms.update()
        self.assertEqual(self.comms.config.rx_ticks, 100)
        self.assertEqual(self.comms.modulation, FSK)

    def test_scheduled_beacon_switches_to_lora_then_back_to_fsk(self):
        self.comms.config.rx_ticks = 1
        self.comms.config.tx_packet_count = 1
        self.comms.on_tx_window = lambda n, cad: self.comms.push_telemetry(
            Comms.build_beacon_packet(1, 7.4, 25, 0))
        self.comms.update()
        self.assertEqual(self.comms.modulation, LORA)
        self.comms.update()
        self.assertEqual(len(self.radio.air[-1]), 16)
        self.assertEqual(self.comms.modulation, FSK)
        self.assertIsNone(self.comms._lora_deadline)

    def test_stop_remains_fsk_without_scheduled_downlinks(self):
        self.comms.state_code = Comms.STATE_STOP
        self.comms.config.rx_ticks = 1
        self.comms.update()
        self.assertEqual(self.comms.modulation, FSK)
        self.assertEqual(self.radio.air, [])

    def test_switch_restores_lora_configuration(self):
        self.comms.set_modulation(LORA)
        self.radio.regs.update({0x26: 4, 0x31: 3, 0x3B: 0x1D, 0x40: 0x80})
        original = dict(self.radio.regs)
        self.comms.set_modulation(FSK, 10)
        self.assertEqual(self.radio.regs[1], 9)
        self.assertEqual(self.radio.fsk_regs[0x30], 0x90)
        self.comms.set_modulation(LORA)
        for address, value in original.items():
            self.assertEqual(self.radio.regs[address], value)

    def test_command_roundtrip_and_config_in_fsk(self):
        self.comms._handle_command(Comms.build_modulation_command(FSK, 10)[1:])
        self.assertEqual(self.comms.modulation, FSK)
        self.comms._handle_command(Comms.build_config_command(20, 3, 2)[1:])
        self.assertEqual(self.comms.config.rx_ticks, 20)
        self.comms._handle_command(Comms.build_modulation_command(LORA)[1:])
        self.assertEqual(self.comms.modulation, LORA)

    def test_lease_expires_even_in_stop_and_repeats_do_not_extend(self):
        with patch('Comms.time.monotonic', return_value=100):
            self.comms.set_modulation(LORA, 10)
        with patch('Comms.time.monotonic', return_value=105):
            self.comms.set_modulation(LORA, 10)
        self.assertEqual(self.comms._lora_deadline, 110)
        self.comms.state_code = Comms.STATE_STOP
        with patch('Comms.time.monotonic', return_value=111), \
                patch.object(self.comms, '_rx_tick', return_value=False):
            self.comms.update()
        self.assertEqual(self.comms.modulation, FSK)
        self.assertEqual(self.radio.air, [])

    def test_queued_beacon_waits_for_lora(self):
        self.comms.push_telemetry(Comms.build_beacon_packet(1, 7.4, 25, 0))
        self.comms.set_modulation(FSK)
        with patch.object(self.comms, '_rx_tick', return_value=False):
            self.comms.update()
        self.assertEqual(len(self.comms._telem_q), 1)
        self.comms.set_modulation(LORA)
        self.comms._tx_tick()
        self.assertEqual(len(self.radio.air[-1]), 16)

    def test_fsk_fifo_send_receive_and_limits(self):
        self.comms.set_modulation(FSK)
        self.comms.send_fsk(b'hello')
        self.assertEqual(self.radio.air[-1], b'\x05hello')
        adapter = self.comms._dual_radio
        adapter.receive_packet(timeout=0)
        self.radio.fifo.extend(b'\x05hello')
        self.radio.rx_flags = 6
        self.assertEqual(adapter.receive_packet(timeout=0), b'hello')
        self.radio.fifo.extend(b'\x05hello')
        self.radio.rx_flags = 4  # bad CRC
        self.assertIsNone(adapter.receive_packet(timeout=0))
        with self.assertRaises(ValueError):
            self.comms.send_fsk(bytes(64))
        self.comms.state_code = Comms.STATE_STOP
        with self.assertRaises(RuntimeError):
            self.comms.send_fsk(b'hello')

    def test_invalid_commands_do_not_switch(self):
        for body in (bytes([3, 2, 10, 253]), bytes([3, 0, 0, 255])):
            self.comms._handle_command(Comms._encrypt(body + bytes([Comms._crc8(body)])))
        self.assertEqual(self.comms.modulation, FSK)
        with self.assertRaises(ValueError):
            Comms.build_modulation_command(LORA, 0)

    def test_aes_writes_to_real_output_buffer(self):
        # Exercise aesio's write-into API rather than desktop XOR fallback.
        import types
        class AES:
            def __init__(self, *args):
                pass
            def encrypt_into(self, source, destination):
                destination[:] = bytes(b ^ 0x55 for b in source)
            decrypt_into = encrypt_into
        with patch.dict('sys.modules', aesio=types.SimpleNamespace(AES=AES, MODE_ECB=1)):
            packet = Comms.build_modulation_command(LORA, 10)
            self.comms._handle_command(packet[1:])
            self.assertEqual(self.comms.modulation, LORA)


if __name__ == '__main__':
    unittest.main()
