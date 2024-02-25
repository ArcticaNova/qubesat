from lib.pycubed import cubesat
from lib.image_utils import flags
import time


async def run(result_dict):
    if not cubesat.camera:
        result_dict["uart_test"] = ("camera unavailable", False)
    cubesat.cam_pin.value = True
    time.sleep(2)
    if not cubesat.camera.get_confirmation(True):
        result_dict["uart_test"] = ("could not confirm connection", False)
    result_dict["uart_test"] = uart_test()
    print("passed uart test")
    cubesat.cam_pin.value = False
    time.sleep(5)
    cubesat.cam_pin.value = True
    time.sleep(2)
    if not cubesat.camera.get_confirmation():
        result_dict["camera_test"] = ("could not confirm camera test", False)
    time.sleep(1)
    result_dict["camera_test"] = camera_test()
    cubesat.cam_pin.value = False

def uart_test():
    retrieving = True
    pointer = 0
    while retrieving:
        with open("/sd/images/test_image.jpeg", "rb") as fd:
            fd.seek(pointer)
            ref_packet = fd.read(499)
        pointer += 499
        packet, flag = cubesat.camera.get_packet
        for i in range(len(ref_packet)):
            if ref_packet[i] != packet[i]:
                return (f"byte {i} is different. Ref: {ref_packet[i]}, packet: {packet[i]}", False)
        if flag == flags.SUCCESS_END_PACKET:
            retrieving = False
        cubesat.camera.ack
    return ("test_image.jpeg was identical to our reference", True)

def camera_test():
    attempts = 0
    retrieving = True
    end_bytes = bytearray(2)
    end_bytes[0] = 0xFF
    end_bytes[1] = 0xD9
    while retrieving:
        packet, flag = cubesat.camera.get_packet
        if flag == flags.FAIL_CONFIRM_AGAIN or flag == flags.FAIL_NO_PACKET:
            attempts += 1
            if attempts > 3:
                return (f"failed to get packet. Code {flag}", False)
            continue
        attempts = 0
        if flag == flags.SUCCESS_FIRST_PACKET:
            if (packet[0] != 0xFF or packet[1] != 0xD8 or packet[2] != 0xFF or packet[3] != 0xE0):
                result = f"{packet[0]}{packet[1]} {packet[2]}{packet[3]}"
                return (f"did not start with JPEG header. Started with {result}", False)
        elif flag == flags.SUCCESS_END_PACKET:
            if end_bytes not in packet:
                result = f"{packet[-2]}{packet[-1]}"
                return (f"did not end with JPEF ending. Ended with {result}", False)
            cubesat.camera.ack
            break
        cubesat.camera.ack
    return ("image looks like a JPEG", True)
