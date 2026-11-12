import time
import board
import analogio
import digitalio

print("Initializing LTC4121 pins...")
prog_adc = analogio.AnalogIn(board.L1PROG)

chrg = digitalio.DigitalInOut(board.CHRG)
chrg.direction = digitalio.Direction.INPUT
chrg.pull = digitalio.Pull.UP

print("Started! Reading solar current every 1s:")

while True:
    raw = prog_adc.value
    v_prog = (raw * 3.3) / 65536
    solar_ma = (v_prog / 3010.0) * 1000.0 * 1000.0
    
    print(f"CHRG Active: {not chrg.value} | L1PROG Raw: {raw} ({v_prog:.3f} V) | Current: {solar_ma:.2f} mA")
    time.sleep(1.0)