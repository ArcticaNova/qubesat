#from lib import pycubed
#from lib import pycubed_rfm9x

import radio_util.radio_util as radio_util
from radio_util.radio_util import DataPacket
import struct
import time
from lib.pycubed import cubesat

# 
print("starting...")
 
"""
cubesat.radio1.coding_rate = 5
cubesat.radio1.long_range_mode = True   
cubesat.radio1.signal_bandwidth = 125000
cubesat.radio1.spreading_factor = 10
cubesat.radio1.high_power = True

"""
data = []
data_bytes = []

cubesat.radio1.high_power = True


data_to_send = radio_util.read_data_file()
data_to_packetize = {}

for entry in data_to_send:
    data_id = entry['id']
    values = entry['value']
    data_to_packetize[data_id] = values
start = time.time()

tf = radio_util.TelemetryFrame(data_to_packetize)
for _ in range(3):
    for pkt in tf.packets:
        """"
        print(f"Packet ID: {pkt.packet_id}, Checksum: {pkt.checksum}")
        print("Payload:")
        
        decoded_payload = DataPacket.decode_payload(pkt.payload)
        for data_id, value in decoded_payload.items():
            print(f"  - ID {data_id}: {value}")
        print("-" * 40)  # Separator for better readability


        print("Raw Packet size: " + str(len(pkt.raw)) + " bytes")
        util.dummy_send(pkt.raw)
        """
        cubesat.RGB = (0, 0, 255)    
        cubesat.radio1.send(pkt.raw)
        curr_time = time.time() - start
        print("Sent packet with ID:", pkt.packet_id, " at time: ", curr_time)

        cubesat.RGB = (0, 0, 0) 
        time.sleep(0.2)
