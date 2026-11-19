"""FSK framing and modulation that match the satellite's SX127x receiver.

Satellite FSK settings (NewCode/DualModeRadio.py):
    433.0 MHz, 9600 bps, +/-25 kHz deviation, no Gaussian shaping,
    8-byte preamble (0xAA), sync word 2D D4, variable-length packets,
    CRC-16 CCITT on, no whitening, no address byte, payload 1..63 bytes.

Frame on air (all bytes sent most significant bit first):
    AA x8 | 2D D4 | length | payload | CRC16 (high byte, low byte)

The SX127x CCITT CRC uses polynomial 0x1021, seed 0x1D0F and an inverted
result, computed over the length byte and payload (Semtech AN1200.18).
"""

import numpy as np

BITRATE = 9600
DEVIATION_HZ = 25_000
PREAMBLE = bytes([0xAA] * 8)
SYNC_WORD = bytes([0x2D, 0xD4])
MAX_PAYLOAD = 63


def crc16_sx127x(data):
    crc = 0x1D0F
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return (~crc) & 0xFFFF


def build_frame(payload):
    """Wrap a payload in preamble, sync word, length byte and CRC."""
    payload = bytes(payload)
    if not 1 <= len(payload) <= MAX_PAYLOAD:
        raise ValueError("FSK payload must be 1..63 bytes")
    body = bytes([len(payload)]) + payload
    crc = crc16_sx127x(body)
    return PREAMBLE + SYNC_WORD + body + bytes([crc >> 8, crc & 0xFF])


def bytes_to_bits(data):
    return np.unpackbits(np.frombuffer(bytes(data), dtype=np.uint8))


def modulate(frame, sample_rate, amplitude=1.0):
    """Continuous-phase 2-FSK baseband IQ: bit 1 = +deviation, bit 0 = -deviation."""
    samples_per_bit = sample_rate / BITRATE
    if abs(samples_per_bit - round(samples_per_bit)) > 1e-9:
        raise ValueError("sample_rate must be a whole multiple of 9600")
    bits = bytes_to_bits(frame)
    freq = np.repeat(np.where(bits == 1, DEVIATION_HZ, -DEVIATION_HZ), int(round(samples_per_bit)))
    phase = 2 * np.pi * np.cumsum(freq) / sample_rate
    return (amplitude * np.exp(1j * phase)).astype(np.complex64)


def demodulate(iq, sample_rate):
    """Simple reference receiver used by the self-test: returns the payload or None.

    Finds the sync word, reads the length byte, and checks the CRC, like the
    satellite does. Not used on air.
    """
    spb = int(round(sample_rate / BITRATE))
    inst_freq = np.angle(iq[1:] * np.conj(iq[:-1]))
    for offset in range(spb):
        bits = (inst_freq[offset + spb // 2::spb] > 0).astype(np.uint8)
        for shift in range(8):
            shifted = np.packbits(bits[shift:]).tobytes()
            index = shifted.find(SYNC_WORD)
            if index < 0:
                continue
            start = index + len(SYNC_WORD)
            if start >= len(shifted):
                continue
            length = shifted[start]
            body = shifted[start:start + 1 + length]
            crc_bytes = shifted[start + 1 + length:start + 3 + length]
            if len(body) == 1 + length and len(crc_bytes) == 2:
                if crc16_sx127x(body) == (crc_bytes[0] << 8 | crc_bytes[1]):
                    return body[1:]
    return None
