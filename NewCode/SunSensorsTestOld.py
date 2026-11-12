import analogio
import board
import time

print("Attempting direct analog pin read...")
print("-----------------------------------")

# Trying standard PyCubed solar voltage ADC pin mappings
pin_options = ['V_SOLAR', 'A5', 'A6', 'AIN5']
solar_pin = None

for pin_name in pin_options:
    if hasattr(board, pin_name):
        try:
            solar_pin = analogio.AnalogIn(getattr(board, pin_name))
            print(f"Successfully bound to pin: board.{pin_name}")
            break
        except Exception as e:
            print(f"Could not bind to board.{pin_name}: {e}")

if solar_pin:
    while True:
        # Read the 16-bit analog value (0 to 65535) and convert to voltage
        voltage = (solar_pin.value * 3.3) / 65536
        # A 10k/10k voltage divider scales voltage by half; multiply by 2 to get actual value
        actual_voltage = voltage * 2 
        
        print(f"Raw Pin: {solar_pin.value} | Scaled: {voltage:.2f}V | Estimated Solar Input: {actual_voltage:.2f}V")
        time.sleep(0.5)
else:
    print("Could not find a valid solar pin mapping on this board definition.")