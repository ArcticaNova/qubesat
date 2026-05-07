"""
QubeSat TinyGS telemetry decoder.

Submit this file (along with your satellite's radio parameters) to the TinyGS
project via their Telegram bot (@tinygs_satadmin_bot) so the network can display
decoded telemetry from QubeSat on https://tinygs.com

Radio parameters to submit:
  mode : LoRa
  freq : 433.0   (MHz)
  bw   : 125.0   (kHz)
  sf   : 7
  cr   : 5       (4/5)
  sw   : 18      (0x12, LoRa public sync word)
  pl   : 8       (preamble length)
  crc  : true
  pwr  : 5       (dBm, satellite TX power)

Beacon packet layout (16 bytes on air):
  Byte 0      : header 0xD0 (HDR_TELEMETRY, stripped by ground station)
  Bytes 1-6   : callsign (6 ASCII chars, space-padded)
  Byte 7      : FSM state code (0=STOP 1=IDLE 2=DEPLOY 3=SCIENCE 4=COMMS)
  Bytes 8-9   : battery voltage in millivolts, uint16 big-endian
  Byte 10     : temperature, uint8, value = int(temp_C) + 40
  Bytes 11-14 : mission time in seconds since boot, uint32 big-endian
  Byte 15     : CRC-8/ITU over bytes 1-14 (payload only, not the header byte)
"""

_STATE_NAMES = {0: "STOP", 1: "IDLE", 2: "DEPLOY", 3: "SCIENCE", 4: "COMMS"}


def _crc8(data):
    """CRC-8/ITU (poly 0x07, init 0xFF). Must match Comms.py implementation."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def decode(raw_packet):
    """
    Decode a raw QubeSat beacon packet received by a TinyGS ground station.

    Args:
        raw_packet: bytes or bytearray — the full packet as received over the air.
                    May or may not include the 0xD0 header byte depending on how
                    the TinyGS firmware delivers it to the decoder.

    Returns:
        dict with decoded fields, or None if the packet is invalid.
    """
    # Strip the HDR_TELEMETRY byte (0xD0) if present
    if len(raw_packet) >= 1 and raw_packet[0] == 0xD0:
        raw_packet = raw_packet[1:]

    # Expect exactly 15 bytes: 6 callsign + 1 state + 2 batt + 1 temp + 4 time + 1 crc
    if len(raw_packet) != 15:
        return None

    payload  = raw_packet[:14]
    received_crc = raw_packet[14]
    if _crc8(payload) != received_crc:
        return None

    callsign     = payload[0:6].decode("ascii", errors="replace").strip()
    state_code   = payload[6]
    batt_mv      = (payload[7] << 8) | payload[8]
    temp_c       = payload[9] - 40
    mission_time = (payload[10] << 24) | (payload[11] << 16) | (payload[12] << 8) | payload[13]

    return {
        "callsign":        callsign,
        "state_code":      state_code,
        "state_name":      _STATE_NAMES.get(state_code, "UNKNOWN"),
        "battery_v":       round(batt_mv / 1000.0, 3),
        "temperature_c":   temp_c,
        "mission_time_s":  mission_time,
    }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Reconstruct the packet that Comms.build_beacon_packet() would produce for:
    #   state=1 (IDLE), batt=7.4 V, temp=25 C, mission_time=120 s
    import struct

    callsign = b"STAC  "
    state    = 1
    batt_mv  = 7400
    temp_raw = 25 + 40  # 65
    t        = 120

    payload = bytearray()
    payload.extend(callsign)
    payload.append(state)
    payload.append((batt_mv >> 8) & 0xFF)
    payload.append(batt_mv & 0xFF)
    payload.append(temp_raw)
    payload.append((t >> 24) & 0xFF)
    payload.append((t >> 16) & 0xFF)
    payload.append((t >>  8) & 0xFF)
    payload.append(t & 0xFF)
    payload.append(_crc8(payload))

    full_packet = bytes([0xD0]) + bytes(payload)
    print("Test packet (hex):", full_packet.hex())

    result = decode(full_packet)
    print("Decoded:", result)

    assert result["callsign"]       == "STAC"
    assert result["state_name"]     == "IDLE"
    assert result["battery_v"]      == 7.4
    assert result["temperature_c"]  == 25
    assert result["mission_time_s"] == 120
    print("All assertions passed.")
