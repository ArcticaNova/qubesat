"""QubeSat uplink command builders for the ground station (runs on a laptop).

These produce exactly the same bytes as the build_*_command() functions in
NewCode/Comms.py, but use desktop AES (the `cryptography` package) instead of
CircuitPython's `aesio`. Comms.py falls back to a plain XOR when `aesio` is
missing, so it must not be used to build commands on a laptop: the satellite
would reject them.

Wire format of every command:
    [0xC0] + AES-128-ECB( PKCS7_pad( body + [crc8(body)] ) )

The AES key must match _AES_KEY in NewCode/Comms.py on the satellite.
"""

import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

HDR_COMMAND = 0xC0

CMD_SET_STATE = 0x01
CMD_SET_CONFIG = 0x02
CMD_SET_MODULATION = 0x03

STATES = {"STOP": 0, "IDLE": 1, "DEPLOY": 2, "SCIENCE": 3, "COMMS": 4}
LORA = 0
FSK = 1

# Matches the placeholder in NewCode/Comms.py. Replace both before flight.
DEFAULT_KEY = bytes(16)


def load_key():
    """Read the key from QUBESAT_AES_KEY (32 hex characters), else the placeholder."""
    text = os.environ.get("QUBESAT_AES_KEY")
    if not text:
        return DEFAULT_KEY
    key = bytes.fromhex(text)
    if len(key) != 16:
        raise ValueError("QUBESAT_AES_KEY must be 32 hex characters (16 bytes)")
    return key


def crc8(data):
    """CRC-8/ITU (poly 0x07, init 0xFF). Same as _crc8 in Comms.py."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _pkcs7_pad(data):
    pad = 16 - (len(data) % 16)
    return bytes(data) + bytes([pad] * pad)


def encrypt(plaintext, key=None):
    """AES-128-ECB with PKCS7 padding, as the satellite expects."""
    key = load_key() if key is None else key
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return enc.update(_pkcs7_pad(plaintext)) + enc.finalize()


def _command(body, key=None):
    return bytes([HDR_COMMAND]) + encrypt(body + bytes([crc8(body)]), key)


def build_state_command(state, key=None):
    """Move the satellite FSM to STOP, IDLE, DEPLOY, SCIENCE or COMMS."""
    code = STATES[state.upper()] if isinstance(state, str) else int(state)
    if code not in STATES.values():
        raise ValueError("Invalid state: %r" % (state,))
    return _command(bytes([CMD_SET_STATE, code, (~code) & 0xFF]), key)


def build_config_command(rx_ticks, tx_packet_count, telem_cadence, key=None):
    """Change the satellite's listen time, packets per window and beacon cadence."""
    for value in (rx_ticks, tx_packet_count, telem_cadence):
        if not 1 <= value <= 255:
            raise ValueError("Config values must be 1..255")
    body = bytes([CMD_SET_CONFIG, rx_ticks, tx_packet_count, telem_cadence,
                  (~rx_ticks) & 0xFF])
    return _command(body, key)


def build_modulation_command(modulation, duration_s=60, key=None):
    """Open a LoRa window for 1..255 s (LORA), or return to FSK (FSK)."""
    if modulation not in (LORA, FSK):
        raise ValueError("Expected LORA (0) or FSK (1)")
    if modulation == LORA and not 1 <= duration_s <= 255:
        raise ValueError("LoRa duration must be 1..255 seconds")
    duration_s = duration_s if modulation == LORA else 0
    body = bytes([CMD_SET_MODULATION, modulation, duration_s, (~modulation) & 0xFF])
    return _command(body, key)
