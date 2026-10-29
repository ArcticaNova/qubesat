from pycubed import cubesat

print("hardware flags:", cubesat.hardware)

# I2C scan on the driver's existing bus
i2c = cubesat.i2c1
while not i2c.try_lock() :
    pass
try :
    print("I2C devices:", [hex(a) for a in i2c.scan()])
finally :
    i2c.unlock()

# Raw analog pins, before any scaling
print("L1PROG raw :", cubesat._ichrg.value, "of 65535")
print("BATTERY raw:", cubesat._vbatt.value, "of 65535")
print("ADC ref (V):", cubesat._ichrg.reference_voltage)

# Derived values
print("solar_charging :", cubesat.solar_charging)
print("charge_current :", cubesat.charge_current(), "mA")
print("battery_voltage:", cubesat.battery_voltage, "V")
print("system_voltage :", cubesat.system_voltage, "V")