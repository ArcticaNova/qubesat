import time
import board

class BurnWire() :
    wire1 = 1 #for each of the burn wires
    wire2 = 2

    def __init__(self) :
        self.isBurning = False #turn to not isBurning once started and then not isBurning after the necessary time runs (30 min i think)
        cubesat._relayA.drive_mode=digitalio.DriveMode.PUSH_PULL
        cubesat._relayA.value = 1

    def burn(self) :
        if self.isBurning :
