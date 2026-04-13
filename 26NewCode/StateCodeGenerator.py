# each state should have an assigned code to it, which should be the minimum number of bits
from enum import Enum

class StateID(Enum):
    IDLE   = 1  # 001
    DEPLOY = 2  # 010
    SCIENCE= 3  # 011
    COMMS  = 4  # 100
    # 0 is reserved for stopping all transmission

class StateCodec:
    STOP = 0  # reserved: halt all transmission

    # maps each state to its minimal bit code
    _codes = {
        StateID.IDLE:    0b001,
        StateID.DEPLOY:  0b010,
        StateID.SCIENCE: 0b011,
        StateID.COMMS:   0b100,
    }
    _decode = {v: k for k, v in _codes.items()}

    # encoding a state to a code 
    def encode(cls, state: StateID) -> int:
        return cls._codes[state]

    # decoding state from codes 
    def decode(cls, code: int):
        if code == cls.STOP:
            return None  # caller should halt transmission
        if code not in cls._decode:
            raise ValueError(f"Unknown code: {code}")
        return cls._decode[code]


    def is_valid(cls, code: int):
        return code == cls.STOP or code in cls._decode