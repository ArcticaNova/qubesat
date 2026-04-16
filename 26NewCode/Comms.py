import time
from pycubed import cubesat

# -----------------------------
# CONFIG
# -----------------------------
MODE = "probe"   # "probe", "listen", or "beacon"
FREQ_MHZ = 433.0

# Conservative LoRa settings
SIGNAL_BW = 125000                                                                                                                                                                                                                                                                      
SPREADING_FACTOR = 7
CODING_RATE = 8
PREAMBLE_LEN = 8
ENABLE_CRC = True

# Keep power low for first transmit tests on an unknown antenna
TX_POWER_DBM = 5

# -----------------------------
# HELPERS
# -----------------------------
def configure_radio():
    if not cubesat.hardware["Radio1"]:
        raise RuntimeError("Radio1 did not initialize")

    r = cubesat.radio1
    r.frequency_mhz = FREQ_MHZ
    r.signal_bandwidth = SIGNAL_BW
    r.spreading_factor = SPREADING_FACTOR
    r.coding_rate = CODING_RATE
    r.preamble_length = PREAMBLE_LEN
    r.enable_crc = ENABLE_CRC
    r.tx_power = TX_POWER_DBM
    return r

def print_status(r):
    print("Radio initialized.")
    print("Frequency (MHz):", r.frequency_mhz)
    print("TX power (dBm):", r.tx_power)
    print("BW:", r.signal_bandwidth)
    print("SF:", r.spreading_factor)
    print("CR:", r.coding_rate)
    print("CRC:", r.enable_crc)


def handle_received_code(self, code: int):
    if not StateCodec.is_valid(code):
        return  # malformed, ignore
    new_state = StateCodec.decode(code)
    if new_state is None:
        self.halt_transmission()
    elif new_state != self.current_state:  # only transition if it's different
        self.transition(new_state)
    # if same state, do nothing — handles the spam case

# -----------------------------
# MAIN
# -----------------------------
try:
    radio = configure_radio()
    print_status(radio)
except Exception as e:
    print("RADIO SETUP FAILED:", e)
    while True:
        time.sleep(1)

if MODE == "probe":
    print("Probe complete.")
    print("If you got here, Radio1 is alive and configurable.")
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

                # Some PyCubed/adafruit_rfm9x variants expose these
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
            payload = msg.encode("utf-8")
            print("TX:", msg)
            radio.send(payload)
            counter += 1
            time.sleep(2)
        except Exception as e:
            print("TX error:", e)
            time.sleep(1)

else:
    print("Unknown MODE:", MODE)
    while True:
        time.sleep(1)
