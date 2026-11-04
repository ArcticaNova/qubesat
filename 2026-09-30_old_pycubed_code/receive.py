import time
from radio_util.radio_util import DataPacket
from radio_util.radio_util import read_data_file
from lib.pycubed import cubesat


time.sleep(3)
print("starting...")


rec_kwargs = {"keep_listening": True, "timeout": None, "with_header":False}
packets_received = 0
packets = []
data = {}


while True:
    packet = cubesat.radio1.receive(kwargs=rec_kwargs)
    

    packet_id = packet["packet_id"]
    packet_payload = packet["payload"]
    packet_checksum = packet["checksum"]


    packets.append(packet)


    packets_received += 1
    
    for id, values in packet_payload.items():
        if id > 30: 
            id //= 10
            if id in data: 
                data[id].extend(values)
            else:
                data[id] = values
        else:
            if id in data: 
                raise ValueError(f"Duplicate ID {id} found in packet payload.")
            data[id] = values
    if all(id in data for id in range(1, 29)): break
    time.sleep(0.01)

original_data = read_data_file()
original_data_dict = {entry['id']: entry['value'] for entry in original_data}

for id, values in data.items():
    if id not in original_data_dict:
        raise ValueError(f"ID {id} not found in original data.")
    if isinstance(values, list):
        if len(values) != len(original_data_dict[id]):
            raise ValueError(f"Length mismatch for ID {id}: {len(values)} vs {len(original_data_dict[id])}.")
        for i, value in enumerate(values):
            if value != original_data_dict[id][i]:
                raise ValueError(f"Value mismatch for ID {id} at index {i}: {value} vs {original_data_dict[id][i]}.")
    else: # flaot
        if values != original_data_dict[id][0]:
            raise ValueError(f"Value mismatch for ID {id}: {values} vs {original_data_dict[id]}.")

print(f"Data is verified and matches original data.")





