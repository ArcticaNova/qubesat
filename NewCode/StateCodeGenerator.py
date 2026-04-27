# each state should have an assigned code to it, which should be the minimum number of bits
# comms has no number since it's running in parallel
# 0 is reserved for stopping all transmission


class StateID:
    IDLE    = 1   # 001
    DEPLOY  = 2   # 010
    SCIENCE = 3   # 011
    DATA    = 4   # 100


class StateCodec:
    STOP = 0  # reserved: halt all transmission

    _codes = {
        StateID.IDLE:    0b001,
        StateID.DEPLOY:  0b010,
        StateID.SCIENCE: 0b011,
        StateID.DATA:    0b100,
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
