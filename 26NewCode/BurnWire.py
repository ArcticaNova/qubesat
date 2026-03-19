import time
import board
import pycubed
import digitalio

class BurnWire() :
    wire1 = 1 #for each of the burn wires
    wire2 = 2

    def __init__(self) :
        self.isBurning = False #turn to not isBurning once started and then not isBurning after the necessary time runs (30 min i think)
        pycubed.cubesat._relayA.drive_mode=digitalio.DriveMode.PUSH_PULL
        pycubed.cubesat._relayA.value = True

    def burn(self) :
        if self.isBurning :
            return