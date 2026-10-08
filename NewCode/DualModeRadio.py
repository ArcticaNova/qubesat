"""SX1276/78 FSK packet mode alongside the existing PyCubed LoRa driver.

FSK uses 9.6 kbps, 25 kHz deviation, 100 kHz RX bandwidth, an eight-byte
preamble and sync bytes 2D D4. Variable-length, unwhitened, CCITT CRC packets.
The 64-byte FIFO limits application packets to 63 bytes (one length byte).
Bench-test with the actual board and matching ground receiver before flight.
"""
import time

LORA = 0
FSK = 1
MAX_FSK_PACKET = 63


class DualModeRadio:
    def __init__(self, radio):
        for name in ("_read_u8", "_write_u8", "_read_into", "_write_from"):
            if not hasattr(radio, name):
                raise TypeError("Radio lacks SX127x register access: " + name)
        self.radio = radio
        self.modulation = LORA
        self._lora_regs = None
        self._receiving = False

    def _mode(self, mode):
        r = self.radio
        r._write_u8(0x01, (r._read_u8(0x01) & 0xF8) | mode)

    def set_modulation(self, modulation):
        if modulation not in (LORA, FSK):
            raise ValueError("Expected LORA or FSK")
        if modulation == self.modulation:
            return
        r = self.radio
        # Sleep before changing LongRangeMode; preserve frequency-band bit.
        self._mode(0)
        time.sleep(0.01)
        if modulation == FSK:
            # Preserve the complete writable LoRa configuration touched by FSK.
            addresses = (0x02, 0x03, 0x04, 0x05, 0x0A, 0x0D, 0x1F,
                         0x26, 0x31, 0x3B, 0x40, 0x41)
            self._lora_regs = [(a, r._read_u8(a)) for a in addresses]
            r._write_u8(0x01, r._read_u8(0x01) & 0x08)
            try:
                settings = (
                    (0x02, 0x0D), (0x03, 0x05),  # 32 MHz / 3333 = 9601 baud
                    (0x04, 0x01), (0x05, 0x9A),  # 410 * 61.035 Hz
                    (0x0A, r._read_u8(0x0A) & 0x9F),  # no Gaussian shaping
                    (0x0D, 0x1E),  # AFC, AGC, trigger on preamble
                    (0x12, 0x0A), (0x13, 0x09),  # RX 100 kHz, AFC 125 kHz
                    (0x1F, 0xAA),  # preamble detector enabled, two bytes
                    (0x25, 0), (0x26, 8),  # FSK preamble (bytes)
                    (0x27, 0x11), (0x28, 0x2D), (0x29, 0xD4),
                    (0x30, 0x90),  # variable length, CRC, no address/whitening
                    (0x31, 0x40), (0x32, MAX_FSK_PACKET),  # packet mode
                    (0x35, 0), (0x3B, 0),  # no FIFO threshold IRQ/auto restart
                    (0x40, 0), (0x41, 0),
                )
                for address, value in settings:
                    r._write_u8(address, value)
                r._write_u8(0x3F, 0x10)  # clear FIFO
                self._mode(1)
            except Exception:
                self._restore_lora()
                raise
        else:
            self._restore_lora()
        self.modulation = modulation
        self._receiving = False

    def _restore_lora(self):
        r = self.radio
        self._mode(0)
        time.sleep(0.01)
        r._write_u8(0x01, (r._read_u8(0x01) & 0x08) | 0x80)
        for address, value in self._lora_regs:
            r._write_u8(address, value)
        r._write_u8(0x12, 0xFF)
        self._mode(1)

    def send_packet(self, packet):
        if self.modulation != FSK:
            raise RuntimeError("send_packet requires FSK mode")
        if not 1 <= len(packet) <= MAX_FSK_PACKET:
            raise ValueError("FSK packet must contain 1..63 bytes")
        r = self.radio
        self._mode(1)
        self._receiving = False
        r._write_u8(0x3F, 0x10)
        r._write_from(0x00, bytes([len(packet)]) + bytes(packet))
        try:
            self._mode(3)
            deadline = time.monotonic() + 1.0
            while not r._read_u8(0x3F) & 0x08:  # PacketSent
                if time.monotonic() >= deadline:
                    raise RuntimeError("FSK TX timeout")
                time.sleep(0.001)
            return True
        finally:
            self._mode(1)
            r._write_u8(0x3F, 0x10)

    def receive_packet(self, timeout=0.1):
        r = self.radio
        if not self._receiving:
            self._mode(1)
            r._write_u8(0x3F, 0x10)
            self._mode(5)
            self._receiving = True
        deadline = time.monotonic() + timeout
        while True:
            flags = r._read_u8(0x3F)
            if flags & 0x10:  # overrun: discard and restart
                self._restart_rx()
                return None
            if flags & 0x04:  # PayloadReady
                try:
                    self._mode(1)
                    if not flags & 0x02:  # CrcOk
                        return None
                    length = r._read_u8(0x00)
                    if not 1 <= length <= MAX_FSK_PACKET:
                        return None
                    packet = bytearray(length)
                    r._read_into(0x00, packet)
                    return bytes(packet)
                finally:
                    self._restart_rx()
            if time.monotonic() >= deadline:
                return None  # keep listening between FSM ticks
            time.sleep(0.001)

    def _restart_rx(self):
        self._mode(1)
        self.radio._write_u8(0x3F, 0x10)
        self._mode(5)
        self._receiving = True
