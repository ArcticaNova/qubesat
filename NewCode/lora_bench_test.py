# QubeSat LoRa bench test (TC-A4-02 in NewCode/ANNEX-A4-COMMS.md).
#
# Copy to the PyCubed as code.py, next to Comms.py and DualModeRadio.py.
# CircuitPython runs code.py before main.py, so main.py and the FSM do not run.
# This file does not import QubeSatFSM or BurnWire.
#
# Sends 20 beacons over LoRa, about 3 seconds apart, then stops.
# LoRa settings come from Comms.py: 433.0 MHz, 125 kHz, SF7, CR 4/5,
# sync word 0x12, preamble 8, CRC on, 5 dBm.
# Expected first packet: d0535441432020011ce84100000000ee

import time

from Comms import (
    HDR_TELEMETRY,
    STATE_IDLE,
    build_beacon_packet,
    configure_radio,
    print_status,
    send_raw,
)

PACKETS = 20
SPACING_S = 3


def to_hex(data):
    return "".join("{:02x}".format(byte) for byte in data)


radio = configure_radio()
print_status(radio)
print("Antenna must be attached. Transmitting in 10 seconds.")
time.sleep(10)

for counter in range(PACKETS):
    # Fixed test values make the bytes easy to compare on TinyGS.
    # The counter uses the mission-time field, so dropped packets are obvious.
    payload = build_beacon_packet(STATE_IDLE, 7.4, 25, counter)
    packet = bytes([HDR_TELEMETRY]) + payload
    sent = send_raw(radio, packet)
    print("TX", counter, "ok" if sent else "TIMEOUT", to_hex(packet))
    time.sleep(SPACING_S)

radio.idle()
print("Done. Compare the hex above with the frames on your TinyGS station.")
