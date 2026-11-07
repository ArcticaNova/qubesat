import board
import digitalio
import busio
import time

print("Attempting to force power to external face ports...")

# PyCubed v05 often gates peripheral/face power behind specific pins
power_pins = ['EN_PERIPH', 'NEO_PWR', 'PERIPH_PWR', 'PB06']
enabled_pins = []

for pin_name in power_pins:
    if hasattr(board, pin_name):
        try:
            pin = digitalio.DigitalInOut(getattr(board, pin_name))
            pin.direction = digitalio.Direction.OUTPUT
            pin.value = True # Force the power switch open
            enabled_pins.append(pin_name)
            print(f"Enabled power channel: {pin_name}")
        except Exception as e:
            print(f"Could not toggle {pin_name}: {e}")

time.sleep(0.5) # Give the chips a moment to boot up

# Now re-try scanning the default I2C line to see if the panel wakes up
i2c = board.I2C()
if i2c.try_lock():
    print("\nScanning bus with peripheral power active...")
    print("Found devices:", [hex(addr) for addr in i2c.scan()])
    i2c.unlock()
else:
    print("Could not lock I2C bus.")