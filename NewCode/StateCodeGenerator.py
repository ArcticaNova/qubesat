# Each state has an assigned code — minimum number of bits needed to represent it.
# 0 is reserved for STOP (halt all transmission).

class StateID:
    IDLE    = 1   # 001
    DEPLOY  = 2   # 010
    SCIENCE = 3   # 011
    COMMS   = 4   # 100  (downlink / ground contact window)


class StateCodec:
    STOP = 0  # reserved: halt all transmission

    _codes = {
        StateID.IDLE:    0b001,
        StateID.DEPLOY:  0b010,
        StateID.SCIENCE: 0b011,
        StateID.COMMS:   0b100,
    }
    _decode = {v: k for k, v in _codes.items()}

    @classmethod
    def encode(cls, state):
        return cls._codes[state]

    @classmethod
    def decode(cls, code):
        if code == cls.STOP:
            return None  # caller should halt transmission
        if code not in cls._decode:
            raise ValueError("Unknown code: " + str(code))
        return cls._decode[code]

    @classmethod
    def is_valid(cls, code):
        return code == cls.STOP or code in cls._decode
