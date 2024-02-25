import sys

sys.path.insert(0, './drivers/emulation/lib')
sys.path.insert(0, './drivers/emulation/')
sys.path.insert(0, './applications/flight')
sys.path.insert(0, './applications/flight/lib')

import Tasks.radio as radio
import settings
from pycubed import cubesat

def init_radio_task_for_testing():
    settings.TX_ALLOWED = True
    settings.RX_ALLOWED = True
    cubesat.radio.test.reset()
    rt = radio.task()

    return rt
