import time
import board
import pycubed
import digitalio
import pwmio
import microcontroller

print("Reset reason:", microcontroller.cpu.reset_reason) #tells us the reason for previous failure if necessary

class BurnWire() :
    freq = 1000
    duration = 0
    isBurning = False #turn to not isBurning once started and then not isBurning after the necessary time runs (30 min i think

    def __init__(self) :
        pycubed.cubesat._relayA.drive_mode = digitalio.DriveMode.PUSH_PULL
        pycubed.cubesat._relayA.value = True

    def burningCheck(self) :
        if self.isBurning == False :
            return "The burn wires are currently not burning."
        return "The burn wires are currently burning."

    def cubesatBurn(self, burn_num, dutycycle, duration) :
        self.isBurning = True
        if burn_num == "1" :
            burnwire = pwmio.PWMOut(board.BURN1, frequency = self.freq, duty_cycle = 0)
        elif burn_num == "2" :
            burnwire = pwmio.PWMOut(board.BURN2, frequency = self.freq, duty_cycle = 0)

        burnwire.duty_cycle = int((dutycycle/100)*(0xFFFF))
        print(f"Wire {burn_num} has started burning")
        targetDutyCycle = int((dutycycle/100)*(0xFFFF))
        steps = 100
        for i in range(1, steps + 1) :
            burnwire.duty_cycle = int(targetDutyCycle * i / steps)
            print(f"Duty cycle at {burnwire.duty_cycle} and {burnwire.duty_cycle / 0xFFFF * 100}% of the max duty cycle.")
            time.sleep(0.5)

        print(microcontroller.cpu.reset_reason)

        time.sleep(300) #I don't remember the exact reason why we chose to leave the burnwire system on for another five minutes after reaching max designated dutycycle tbh
        print(f"Wire {burn_num} has finished burning")

        self.isBurning = False
        burnwire.duty_cycle = 0
        burnwire.deinit()
        pycubed.cubesat._relayA.drive_mode = digitalio.DriveMode.OPEN_DRAIN

    def turnOff(self, burn_num) :
        self.cubesatBurn(burn_num, 0, 0)

def BurnWireObject() :
    e = BurnWire()
    e.cubesatBurn("2", 2, 30)

BurnWireObject()