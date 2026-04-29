"""
Comms.py  —  CubeSat communications system (CircuitPython / PyCubed).

Handles:
  - Physical LoRa radio configuration via PyCubed (cubesat.radio1)
  - FSM state code persistence in NVM (3 copies, majority vote, checksum)
  - AES-128-ECB encrypted command packets with CRC-8 + complement verification
  - Alternating RX/TX schedule (RX = tick count, TX = packet count)
  - Telemetry and amateur radio queues with priority ordering
  - Ground station command builders (build_state_command, build_config_command)

State codes mirror StateCodeGenerator.py (plain integer class constants, no enum)
and must be kept in sync manually.
"""

import time
from pycubed import cubesat

# ── State codes ────────────────────────────────────────────────────────────────
# Must stay in sync with StateID in StateCodeGenerator.py.
STATE_STOP    = 0   # halt all transmission; RX stays active so a non-zero command can wake it
STATE_IDLE    = 1   # 0b001
STATE_DEPLOY  = 2   # 0b010
STATE_SCIENCE = 3   # 0b011
STATE_DATA    = 4   # 0b100

_VALID_CODES = (STATE_STOP, STATE_IDLE, STATE_DEPLOY, STATE_SCIENCE, STATE_DATA)

# ── Radio hardware config ──────────────────────────────────────────────────────
FREQ_MHZ         = 433.0
SIGNAL_BW        = 125000
SPREADING_FACTOR = 7
CODING_RATE      = 8
PREAMBLE_LEN     = 8
ENABLE_CRC       = True
TX_POWER_DBM     = 5

# ── NVM layout (bytes 12–18) ───────────────────────────────────────────────────
#  12–14: three copies of the state code (majority vote on read)
#  15   : state checksum (state ^ 0xAA)  (tiebreaker if all three differ)
#  16   : config rx_ticks
#  17   : config tx_packet_count
#  18   : config telem_cadence
_NVM_S1      = 12
_NVM_S2      = 13
_NVM_S3      = 14
_NVM_CS      = 15
_NVM_CFG_RX  = 16
_NVM_CFG_TX  = 17
_NVM_CFG_CAD = 18

try:
    import microcontroller
    _nvm = microcontroller.nvm
except ImportError:
    _nvm = bytearray(256)   # desktop emulation fallback


def _nvm_write_state(code):
    b = code & 0x7F
    _nvm[_NVM_S1] = b
    _nvm[_NVM_S2] = b
    _nvm[_NVM_S3] = b
    _nvm[_NVM_CS] = b ^ 0xAA


def _nvm_read_state():
    """
    Majority vote across 3 NVM copies. Uses checksum as tiebreaker if all differ.
    Self-heals the outlier copy. Returns 0 (halt) if all three are corrupt.
    Fresh NVM (all zeros): expected = 0xAA, copies = 0 != 0xAA -> returns 0.
    """
    s1, s2, s3 = _nvm[_NVM_S1], _nvm[_NVM_S2], _nvm[_NVM_S3]
    expected = _nvm[_NVM_CS] ^ 0xAA

    if s1 == s2:
        if s3 != s1:
            _nvm[_NVM_S3] = s1
        return s1
    if s1 == s3:
        _nvm[_NVM_S2] = s1
        return s1
    if s2 == s3:
        _nvm[_NVM_S1] = s2
        return s2
    for candidate in (s1, s2, s3):
        if candidate == expected:
            _nvm_write_state(candidate)   # restore all three from the valid copy
            return candidate
    return 0   # all three corrupt — halt


def _nvm_write_config(rx, tx, cad):
    _nvm[_NVM_CFG_RX]  = rx  & 0xFF
    _nvm[_NVM_CFG_TX]  = tx  & 0xFF
    _nvm[_NVM_CFG_CAD] = cad & 0xFF


def _nvm_read_config():
    return _nvm[_NVM_CFG_RX], _nvm[_NVM_CFG_TX], _nvm[_NVM_CFG_CAD]


# ── CRC-8 ──────────────────────────────────────────────────────────────────────
def _crc8(data):
    """CRC-8/ITU (poly 0x07, init 0xFF). Detects all single-bit and many burst errors."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


# ── Encryption ─────────────────────────────────────────────────────────────────
# AES-128-ECB + PKCS7 padding. ECB is appropriate because every command is a
# single packet, so there is no multi-block context to leak via identical IVs.
_AES_KEY = b'\x00' * 16   # REPLACE with actual 16-byte pre-shared key before flight


def _pkcs7_pad(data):
    pad = 16 - (len(data) % 16)
    return bytearray(data) + bytearray([pad] * pad)


def _pkcs7_unpad(data):
    pad = data[-1]
    if pad < 1 or pad > 16:
        return b''
    return bytes(data[:-pad])


def _encrypt(plaintext):
    """AES-128-ECB encrypt. Called by the ground station to build command packets."""
    try:
        import aesio
        padded = _pkcs7_pad(plaintext)
        out = bytearray(len(padded))
        c = aesio.AES(_AES_KEY, aesio.MODE_ECB)
        for i in range(0, len(padded), 16):
            c.encrypt_into(padded[i:i + 16], out[i:i + 16])
        return bytes(out)
    except ImportError:
        return bytes(b ^ _AES_KEY[i % 16] for i, b in enumerate(plaintext))


def _decrypt(ciphertext):
    """AES-128-ECB decrypt. Called by the satellite to parse incoming commands."""
    try:
        import aesio
        if len(ciphertext) % 16 != 0:
            return b''
        out = bytearray(len(ciphertext))
        c = aesio.AES(_AES_KEY, aesio.MODE_ECB)
        for i in range(0, len(ciphertext), 16):
            c.decrypt_into(ciphertext[i:i + 16], out[i:i + 16])
        return _pkcs7_unpad(out)
    except ImportError:
        return bytes(b ^ _AES_KEY[i % 16] for i, b in enumerate(ciphertext))


# ── Packet headers and command types ──────────────────────────────────────────
HDR_COMMAND   = 0xC0   # uplink: encrypted command, one packet max
HDR_TELEMETRY = 0xD0   # downlink: telemetry
HDR_AMATEUR   = 0xA0   # bi-directional: amateur / ham radio

CMD_SET_STATE  = 0x01
CMD_SET_CONFIG = 0x02


# ── Ground station command builders ───────────────────────────────────────────
def build_state_command(state_code):
    """
    Build an encrypted uplink packet to command the satellite to a new FSM state.
    Transmit multiple times from the ground for reliability (satellite deduplicates).

    Wire format: [HDR_COMMAND] | AES( [0x01][state][~state][crc8_of_first_3] )
    """
    if state_code not in _VALID_CODES:
        raise ValueError("Invalid state code: " + str(state_code))
    arg  = state_code & 0x7F
    body = bytes([CMD_SET_STATE, arg, (~arg) & 0xFF])
    return bytes([HDR_COMMAND]) + _encrypt(body + bytes([_crc8(body)]))


def build_config_command(rx_ticks, tx_packet_count, telem_cadence):
    """
    Build an encrypted uplink packet to update the satellite's comms schedule.

    Wire format: [HDR_COMMAND] | AES( [0x02][rx][tx][cad][~rx][crc8_of_first_5] )
    """
    body = bytes([CMD_SET_CONFIG,
                  rx_ticks & 0xFF, tx_packet_count & 0xFF, telem_cadence & 0xFF,
                  (~rx_ticks) & 0xFF])
    return bytes([HDR_COMMAND]) + _encrypt(body + bytes([_crc8(body)]))


# ── Ring queue ─────────────────────────────────────────────────────────────────
class _RingQueue:
    """Fixed-size FIFO ring buffer. Avoids collections.deque (unreliable in CircuitPython)."""

    def __init__(self, maxsize):
        self._buf   = [None] * maxsize
        self._head  = 0
        self._tail  = 0
        self._count = 0
        self._max   = maxsize

    def push(self, item):
        if self._count >= self._max:
            return False
        self._buf[self._tail] = item
        self._tail = (self._tail + 1) % self._max
        self._count += 1
        return True

    def pop(self):
        if self._count == 0:
            return None
        item = self._buf[self._head]
        self._head = (self._head + 1) % self._max
        self._count -= 1
        return item

    def empty(self):
        return self._count == 0

    def __len__(self):
        return self._count


# ── Comms config ───────────────────────────────────────────────────────────────
class CommsConfig:
    """
    Schedule parameters. Loaded from NVM on startup; updateable via ground command.

    rx_ticks:        number of update() calls to stay in RX per window
    tx_packet_count: number of packets to send before switching back to RX
    telem_cadence:   FSM should push telemetry every N TX windows
                     (signaled via on_tx_window callback; not enforced internally)
    """
    DEFAULT_RX_TICKS        = 50
    DEFAULT_TX_PACKET_COUNT = 10
    DEFAULT_TELEM_CADENCE   = 3

    def __init__(self):
        rx, tx, cad = _nvm_read_config()
        self.rx_ticks        = rx  or self.DEFAULT_RX_TICKS
        self.tx_packet_count = tx  or self.DEFAULT_TX_PACKET_COUNT
        self.telem_cadence   = cad or self.DEFAULT_TELEM_CADENCE

    def apply(self, rx_ticks, tx_packet_count, telem_cadence):
        self.rx_ticks        = max(1, rx_ticks        & 0xFF)
        self.tx_packet_count = max(1, tx_packet_count & 0xFF)
        self.telem_cadence   = max(1, telem_cadence   & 0xFF)
        _nvm_write_config(self.rx_ticks, self.tx_packet_count, self.telem_cadence)


# ── CommsManager ───────────────────────────────────────────────────────────────
class CommsManager:
    """
    Manages all RF communications for the CubeSat.

    Typical FSM integration:

        comms = CommsManager(cubesat.radio1)
        comms.state_code = fsm.current_state        # sync NVM on startup

        comms.on_state_command = fsm.transition      # fn(new_state_code: int)
        comms.on_amateur_rx    = store_amateur        # fn(payload: bytes)
        comms.on_tx_window     = push_telem_if_due   # fn(window_num: int, cadence: int)
        # example on_tx_window:
        #   def push_telem_if_due(n, cad):
        #       if n % cad == 0:
        #           comms.push_telemetry(collect_telemetry())

        # every FSM tick:
        comms.update()
    """

    _RX = 0
    _TX = 1

    def __init__(self, radio):
        self._radio      = radio
        self._state_code = _nvm_read_state()
        self.config      = CommsConfig()
        self._mode       = self._RX

        self._rx_elapsed = 0
        self._tx_sent    = 0
        self._tx_windows = 0   # increments each time a TX window ends

        self._telem_q   = _RingQueue(maxsize=16)
        self._amateur_q = _RingQueue(maxsize=32)

        self.on_state_command = None   # fn(new_state_code: int)
        self.on_tx_window     = None   # fn(window_num: int, cadence: int)
        self.on_amateur_rx    = None   # fn(payload: bytes)

    # ── Public API ──────────────────────────────────────────────────────────────

    @property
    def state_code(self):
        return self._state_code

    @state_code.setter
    def state_code(self, code):
        code = code & 0x7F
        self._state_code = code
        _nvm_write_state(code)

    def push_telemetry(self, packet):
        """Enqueue a telemetry packet for downlink (high priority). Returns False if full."""
        return self._telem_q.push(bytes(packet))

    def push_amateur(self, packet):
        """Enqueue an amateur packet for downlink (FIFO). Returns False if full."""
        return self._amateur_q.push(bytes(packet))

    def update(self):
        """
        Run one comms tick. Call this every FSM loop iteration.
        No-op when state_code is 0 (halt).

        RX: advances tick counter each call, except when a command was received
            (command processing pauses the window — that tick is not counted).
        TX: advances packet counter each time a packet is sent. Switches back to
            RX immediately if both queues drain before hitting tx_packet_count.

        When state_code is 0 (STOP): RX-only — listens for a wake-up command
        but never transmits and never advances the RX/TX schedule.
        """
        if self._state_code == 0:
            self._rx_tick()   # stay alive so ground can send a non-zero state command
            return

        if self._mode == self._RX:
            cmd_received = self._rx_tick()
            if not cmd_received:
                self._rx_elapsed += 1
                if self._rx_elapsed >= self.config.rx_ticks:
                    self._enter_tx()
        else:
            sent = self._tx_tick()
            if sent:
                self._tx_sent += 1
                if self._tx_sent >= self.config.tx_packet_count:
                    self._enter_rx()
            else:
                self._enter_rx()   # queues drained early — return to RX

    # ── Internal ────────────────────────────────────────────────────────────────

    def _enter_rx(self):
        self._mode = self._RX
        self._rx_elapsed = 0
        self._tx_windows += 1

    def _enter_tx(self):
        self._mode = self._TX
        self._tx_sent = 0
        if self.on_tx_window is not None:
            self.on_tx_window(self._tx_windows, self.config.telem_cadence)

    def _rx_tick(self):
        """
        Poll radio for one packet. Dispatches by header byte.
        Returns True if a command was received — caller skips advancing rx_elapsed.
        """
        raw = self._receive()
        if raw is None or len(raw) < 2:
            return False

        header  = raw[0]
        payload = bytes(raw[1:])

        if header == HDR_COMMAND:
            self._handle_command(payload)
            return True   # schedule paused this tick

        if header == HDR_AMATEUR:
            self._amateur_q.push(payload)   # O(1) push, no processing
            if self.on_amateur_rx is not None:
                self.on_amateur_rx(payload)

        return False

    def _tx_tick(self):
        """Send one packet. Telemetry queue first (priority), amateur FIFO second."""
        if not self._telem_q.empty():
            self._send(HDR_TELEMETRY, self._telem_q.pop())
            return True
        if not self._amateur_q.empty():
            self._send(HDR_AMATEUR, self._amateur_q.pop())
            return True
        return False

    def _handle_command(self, encrypted_payload):
        """
        Decrypt and verify a command packet, then dispatch.

        Two independent integrity checks:
          Complement: plaintext[1] ^ plaintext[-2] == 0xFF
          CRC-8:      crc8(plaintext[:-1])          == plaintext[-1]

        CMD_SET_STATE  layout: [0x01][state][~state][crc8]        (4 bytes)
        CMD_SET_CONFIG layout: [0x02][rx][tx][cad][~rx][crc8]     (6 bytes)
        """
        plaintext = _decrypt(encrypted_payload)
        if not plaintext or len(plaintext) < 4:
            print("[COMMS] Command too short or decrypt failed")
            return

        if (plaintext[1] ^ plaintext[-2]) != 0xFF:
            print("[COMMS] Complement check failed — dropping")
            return

        if _crc8(bytes(plaintext[:-1])) != plaintext[-1]:
            print("[COMMS] CRC check failed — dropping")
            return

        cmd = plaintext[0]

        if cmd == CMD_SET_STATE:
            new_code = plaintext[1] & 0x7F
            if new_code not in _VALID_CODES:
                print("[COMMS] Unrecognized state code:", new_code)
                return
            if new_code == self._state_code:
                return   # deduplicate: already in this state, ground was spamming
            self.state_code = new_code   # writes to all 3 NVM copies + checksum
            print("[COMMS] State ->", new_code)
            if self.on_state_command is not None:
                self.on_state_command(new_code)

        elif cmd == CMD_SET_CONFIG:
            if len(plaintext) < 6:
                print("[COMMS] Config command too short")
                return
            self.config.apply(plaintext[1], plaintext[2], plaintext[3])
            print("[COMMS] Config: rx=%d tx=%d cad=%d" % (
                self.config.rx_ticks, self.config.tx_packet_count, self.config.telem_cadence))

        else:
            print("[COMMS] Unknown command type:", cmd)

    def _receive(self):
        try:
            return self._radio.receive(timeout=0.1)
        except Exception as e:
            print("[COMMS] RX error:", e)
            return None

    def _send(self, header, payload):
        try:
            self._radio.send(bytes([header]) + payload)
        except Exception as e:
            print("[COMMS] TX error:", e)


# ── Radio hardware helpers ─────────────────────────────────────────────────────
def configure_radio():
    if not cubesat.hardware["Radio1"]:
        raise RuntimeError("Radio1 did not initialize")
    r = cubesat.radio1
    r.frequency_mhz   = FREQ_MHZ
    r.signal_bandwidth = SIGNAL_BW
    r.spreading_factor = SPREADING_FACTOR
    r.coding_rate      = CODING_RATE
    r.preamble_length  = PREAMBLE_LEN
    r.enable_crc       = ENABLE_CRC
    r.tx_power         = TX_POWER_DBM
    return r


def print_status(r):
    print("Radio initialized.")
    print("Frequency (MHz):", r.frequency_mhz)
    print("TX power (dBm):", r.tx_power)
    print("BW:", r.signal_bandwidth)
    print("SF:", r.spreading_factor)
    print("CR:", r.coding_rate)
    print("CRC:", r.enable_crc)


# ── Diagnostic entry point ────────────────────────────────────────────────────
# Change MODE to run hardware tests directly from this file.
# When imported by the FSM, this block does not execute.
if __name__ == "__main__":
    MODE = "probe"   # "probe", "listen", or "beacon"

    try:
        radio = configure_radio()
        print_status(radio)
    except Exception as e:
        print("RADIO SETUP FAILED:", e)
        while True:
            time.sleep(1)

    if MODE == "probe":
        print("Probe complete. Radio1 is alive and configurable.")
        while True:
            time.sleep(2)

    elif MODE == "listen":
        print("Listening at", radio.frequency_mhz, "MHz")
        while True:
            try:
                packet = radio.receive(timeout=2.0)
                if packet is None:
                    print("No packet")
                else:
                    print("RX raw:", packet)
                    try:
                        print("RX text:", packet.decode("utf-8"))
                    except Exception:
                        pass
                    try:
                        print("RSSI:", radio.rssi, "dBm")
                    except Exception:
                        pass
                    try:
                        print("SNR:", radio.snr, "dB")
                    except Exception:
                        pass
                time.sleep(0.2)
            except Exception as e:
                print("RX error:", e)
                time.sleep(1)

    elif MODE == "beacon":
        counter = 0
        print("Starting LOW-POWER beacon test")
        print("Only do this if the antenna is firmly attached.")
        while True:
            try:
                msg = "PYCUBED TEST {}".format(counter)
                radio.send(msg.encode("utf-8"))
                print("TX:", msg)
                counter += 1
                time.sleep(2)
            except Exception as e:
                print("TX error:", e)
                time.sleep(1)

    else:
        print("Unknown MODE:", MODE)
        while True:
            time.sleep(1)
