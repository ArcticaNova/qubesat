# QubeSat FSK bench test (TC-A4-03 in NewCode/ANNEX-A4-COMMS.md).
#
# Copy to the PyCubed as code.py, next to Comms.py and DualModeRadio.py.
# Does not import QubeSatFSM or BurnWire.
#
# Sends 20 beacons over FSK, about 3 seconds apart, then stops.
# FSK settings come from DualModeRadio.py:
#   433.0 MHz, 9.6 kbps, 25 kHz deviation, 100 kHz RX bandwidth,
#   8-byte preamble, sync word 2D D4, variable length, CCITT CRC, no whitening.
# Each packet on air is: length byte, then the 16-byte beacon.

import time

from Comms import (
    HDR_TELEMETRY,
    STATE_IDLE,
    build_beacon_packet,
    configure_radio,
    print_status,
)
from DualModeRadio import DualModeRadio, FSK

PACKETS = 20
SPACING_S = 3


def to_hex(data):
    return "".join("{:02x}".format(byte) for byte in data)


radio = configure_radio()
print_status(radio)
dual = DualModeRadio(radio)
dual.set_modulation(FSK)
print("Switched to FSK. Antenna must be attached. Transmitting in 10 seconds.")
time.sleep(10)

for counter in range(PACKETS):
    packet = bytes([HDR_TELEMETRY]) + build_beacon_packet(STATE_IDLE, 7.4, 25, counter)
    try:
        dual.send_packet(packet)
        print("FSK TX", counter, "ok", to_hex(packet))
    except Exception as e:
        print("FSK TX", counter, "FAILED:", e)
    time.sleep(SPACING_S)

radio.idle()
print("Done. Compare the hex above with what the LILYGO prints.")
