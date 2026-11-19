# QubeSat FSK uplink bench test, satellite side.
#
# Copy to the PyCubed as code.py, next to Comms.py and DualModeRadio.py.
# Does not import QubeSatFSM or BurnWire, and does not change the saved state.
#
# Listens on FSK and prints every packet. For command packets (0xC0) it
# decrypts and runs the same checks as CommsManager._handle_command, then
# prints what the command would do, without acting on it.

import time

from Comms import HDR_COMMAND, _crc8, _decrypt, configure_radio, print_status
from DualModeRadio import DualModeRadio, FSK

NAMES = {1: "SET_STATE", 2: "SET_CONFIG", 3: "SET_MODULATION"}


def to_hex(data):
    return "".join("{:02x}".format(byte) for byte in data)


radio = configure_radio()
print_status(radio)
dual = DualModeRadio(radio)
dual.set_modulation(FSK)
print("Listening on FSK. Send commands from the ground station now.")

count = 0
while True:
    raw = dual.receive_packet(timeout=0.5)
    if raw is None:
        continue
    count += 1
    print("RX", count, len(raw), "bytes:", to_hex(raw))
    if raw[0] != HDR_COMMAND:
        continue
    plain = _decrypt(bytes(raw[1:]))
    if not plain or len(plain) < 4:
        print("   decrypt FAILED (wrong AES key?)")
    elif plain[1] ^ plain[-2] != 0xFF:
        print("   complement check FAILED")
    elif _crc8(bytes(plain[:-1])) != plain[-1]:
        print("   CRC-8 check FAILED")
    else:
        print("   VALID", NAMES.get(plain[0], "UNKNOWN"), "args:", list(plain[1:-2]))
