"""
Utility functions for the radio and data applications
"""
import struct

class DataPacket:
    """Util class to build and decode packets for telemetry data."""
    def __init__(self, packet_id, data_dict):
        self.packet_id = packet_id      
        self.data = data_dict          

        self.payload = self.build_payload()
        self.checksum = self.calculate_checksum()
        self.raw = self.build_raw_packet()

    """Build formatted payload bytearray from data dictionary."""
    def build_payload(self):
        # initalize raw payload bytearray
        raw = bytearray()
        # Iterator through data dictionary
        for data_id, value in self.data.items():

            # Format of each entry in our payload is: 
            # 1 byte for ID + 1/0 Byte of length + n * 4 bytes for float values
            # 
            raw.append(data_id) 
            if isinstance(value, list):
                raw.append(len(value))
                for v in value:
                    raw.extend(struct.pack('<f', v))  
            else: 
                raw.append(1)  
                raw.extend(struct.pack('<f', value))  
        return raw

    def calculate_checksum(self):
        checksum = 0
        for byte in self.payload:
            checksum ^= byte
        return checksum

    def build_raw_packet(self):
        raw = bytearray()
        raw.append(self.packet_id) # 1 byte for packet number
        raw.extend(self.payload)
        raw.append(self.checksum) # 1 byte for checksum
        return raw

    @staticmethod
    def decode_payload(payload: bytearray) -> dict:
        decoded_data = {}
        i = 0
        # iterate through the payload
        while i < len(payload):
            data_id = payload[i]  # 1 byte for ID
            i += 1
            length = payload[i]  # 1 byte for the length of items
            i += 1
            values = []
            for _ in range(length):
                value = struct.unpack('<f', payload[i:i+4])[0]  # 4 bytes for each float
                value = round(value, 2)
                i += 4
                values.append(value)
            decoded_data[data_id] = values if length > 1 else values[0]  # Single value if length is 1
        return decoded_data


    @staticmethod
    def decode_raw_packet(raw_packet: str) -> dict:
        raw_packet = bytearray(raw_packet, 'latin1')
        if len(raw_packet) < 3:  # Ensure packet is at least 3 bytes
            raise ValueError("Invalid packet size")

        packet_id = raw_packet[0]  # 1 byte for packet number
        checksum = raw_packet[-1]  # 1 byte for checksum
        payload = raw_packet[1:-1]  # everything in between

        # Verify checksum
        calculated_checksum = 0
        for byte in payload:
            calculated_checksum ^= byte
        if calculated_checksum != checksum:
            raise ValueError("Checksum mismatch")

        # Decode payload
        decoded_data = DataPacket.decode_payload(payload)

        return {
            "packet_id": packet_id,
            "checksum": checksum,
            "payload": decoded_data
        }

class TelemetryFrame:
    def __init__(self, telemetry_data):
        self.raw_data = telemetry_data  
        self.packets = self.build_packets()

    def build_packets(self) -> list[DataPacket]:
        packets = []
        packet_id = 0
        max_packet_size = 176

        float_size = 4

        # Preprocess - split large data into smaller chunks
        processed_items = []
        for data_id, value in self.raw_data.items():
            max_list_bytes = max_packet_size - 2  # 1 byte ID, 1 byte len
            max_floats = max_list_bytes // float_size # max floats we can have
            # If list
            if isinstance(value, list):
                # if list is not too long
                if len(value) * float_size <= max_list_bytes:
                    processed_items.append((data_id, value))
                else:
                    # Split into sub chunks with special ID chunk_id * 10 + sub_chunk_id 
                    chunk_id_base = data_id * 10
                    num_chunks = (len(value) + max_floats - 1) // max_floats

                    for j in range(num_chunks):
                        chunk_vals = value[j * max_floats : (j + 1) * max_floats]
                        processed_items.append((chunk_id_base + j, chunk_vals))
            else:
                processed_items.append((data_id, value))

        
        current_payload = {}
        current_size = 0  # in bytes

        for data_id, value in processed_items:
            if isinstance(value, list):
                length = len(value)
            else:
                length = 1
                value = [value]

            entry_size = 1 + 1 + length * float_size  # ID + length byte + data

            if current_size + entry_size > max_packet_size:
                # flush current packet
                packets.append(DataPacket(packet_id, current_payload))
                packet_id += 1
                current_payload = {}
                current_size = 0

            current_payload[data_id] = value if length > 1 else value[0]
            current_size += entry_size

        # flush last packet
        if current_payload:
            packets.append(DataPacket(packet_id, current_payload))

        return packets


    def packet_generator(self):
        for pkt in self.packets:
            yield pkt

    def reset(self):
        self.index = 0




dummy_data_path = "/radio_util/telemetry_dummy_data.csv"
    
def read_data_file() -> list[DataPacket]: 
    data_to_send = []
    file_path = dummy_data_path
    with open(file_path, "r") as f:
        lines = f.readlines()

    for line in lines[1:]:
        parts = line.strip().split(',')
        name = parts[0]
        data_id = int(parts[1])
        values = parts[2:]
    
        try:
            values = [v.replace("\"", "") for v in values]
            parsed_values = [
                float(v) if '.' in v else int(v)
                for v in values if v
            ]

        except ValueError as e:
            print(e)
            print(f"Warning: could not parse values for {name}: {values}")
            continue

        data_to_send.append({
            'name': name,
            'id': data_id,
            'value': parsed_values
        })
        
    return data_to_send


def verify_data():
    return    

def dummy_send(packet):
    return None

def dummy_receive(packet): 
    return None
