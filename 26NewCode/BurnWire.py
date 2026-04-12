import time
import board
import pycubed
import digitalio

class BurnWire() :
    wire1 = "1" #for each of the burn wires
    wire2 = "2"
    freq = 0
    burn_num = ""
    duty_cycle = 0

    def __init__(self) :
        self.isBurning = False #turn to not isBurning once started and then not isBurning after the necessary time runs (30 min i think)
        pycubed.cubesat._relayA.drive_mode = digitalio.DriveMode.PUSH_PULL
        pycubed.cubesat._relayA.value = True
        
        if self.burn_num == "1" :
            burnwire = pycubed.cubesat.pwmio.PWMOut(self.wire1, self.freq, self.duty_cycle)
        elif self.burn_num == "2" :
            burnwire = pycubed.cubesat.pwmio.PWMOut(self.wire2, self.freq, self.duty_cycle)


    def cubesatBurn(self, burn_num, dutycycle, freq) :
        