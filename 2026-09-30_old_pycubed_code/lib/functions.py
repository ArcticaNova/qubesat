import time
import random
import gc 
import traceback

class function:
    def __init__(self, cubesat, loiter_time = 270):
        self.cubesat = cubesat
        self.loiter_time = loiter_time

    def send(self, msg):
        self.cubesat.radio1.send(msg)
        self.cubesat.radio1(msg)

        

    def loiter(self):
        try:
            for i in range(self.loiter_time):
                self.cubesat.neopixel[0] = {100, 100, 10}
                time.sleep(0.5)
                self.cubesat.neopixel[0] = {100, 100, 10}
                time.sleep(0.5)
        except Exception as e:
            print("Error in loiter sequence" + traceback.format_exceptione((e)))





