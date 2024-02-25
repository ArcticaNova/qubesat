from datetime import datetime as dt, timezone
import numpy as np
import radio_utils.headers as headers
from radio_driver import _Packet as Packet
from pycubed import cubesat

def timestamp(year, month, day, hour=0, minute=0, second=0):
    return dt(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp()

def assert_vector_similar(a, b, leq, angle_tolerance=5, a_tolerance=50, units=""):
    ua = a / np.linalg.norm(a)
    ub = b / np.linalg.norm(b)
    angle = np.arccos(np.dot(ua, ub)) * 180 / np.pi
    dif = np.linalg.norm(a - b)
    leq(angle, angle_tolerance,
        f"Exceeded the {angle_tolerance}° tolerance\n ref: {b}\n ours:   {a}\n diff:   {b - a}")
    leq(
        dif, a_tolerance, f"Exceeded the {a_tolerance}{units} tolerance\n ref: {b}\n ours:   {a}\n diff:   {b - a}")
    return angle, dif

def command_data(command_code, args):
    return bytes([headers.COMMAND]) + b'p\xba\xb8C' + command_code + args

def send_cmd(cmd, args):
    query_packet = Packet(command_data(cmd, args))
    cubesat.radio.test.push_rx_queue(query_packet)
