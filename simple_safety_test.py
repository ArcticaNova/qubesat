import time
import random

print('Battery Temperature Safety Test Starting...')

# Battery temperature safety limits
TEMP_MIN = 0
TEMP_MAX = 5

# Current system state
radio_on = True
camera_on = True
state = "Normal"

print('Safe temperature range: 0C to 5C')
print('Starting main control loop...')
print('')

# ------- MAIN LOOP -------
while True:
    # Simulate random battery temperature
    battery_temp = random.uniform(-10, 15)
    
    print('Time:', time.monotonic())
    print('Battery Temperature:', round(battery_temp, 1), 'C')
    
    # Control logic
    if battery_temp < TEMP_MIN or battery_temp > TEMP_MAX:
        print('UNSAFE TEMPERATURE!')
        if radio_on:
            print('ACTION: Turn OFF radio')
            radio_on = False
        if camera_on:
            print('ACTION: Turn OFF camera')
            camera_on = False
        if state != "Safe":
            print('ACTION: Switch to SAFE mode')
            state = "Safe"
    else:
        print('Temperature OK')
        if not radio_on:
            print('ACTION: Turn ON radio')
            radio_on = True
        if not camera_on:
            print('ACTION: Turn ON camera')
            camera_on = True
        if state != "Normal":
            print('ACTION: Switch to NORMAL mode')
            state = "Normal"
    
    print('Status - Radio:', 'ON' if radio_on else 'OFF', 
          '| Camera:', 'ON' if camera_on else 'OFF',
          '| State:', state)
    print('---')
    
    time.sleep(2)