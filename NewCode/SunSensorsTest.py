import time
import board
from adafruit_bus_device.i2c_device import I2CDevice

i2c = board.I2C()
bq = I2CDevice(i2c, 0x6B)

def read_reg(reg):
    buf = bytearray([reg])
    with bq:
        bq.write_then_readinto(buf, buf)
    return buf[0]

def write_reg(reg, val):
    with bq:
        bq.write(bytes([reg, val]))

# Disable watchdog (Reg 0x05) and enable continuous 15-bit ADC (Reg 0x15 = 0x80)
write_reg(0x05, read_reg(0x05) & 0b11001111)
write_reg(0x15, 0x80)
time.sleep(0.5)

# Read IBUS (Solar Input Current: Reg 0x19 MSB, 0x1A LSB) -> 1 LSB = 1 mA
ibus_ma = (read_reg(0x19) << 8) | read_reg(0x1A)

# Read ICHG (Battery Charge Current: Reg 0x1B MSB, 0x1C LSB) -> 1 LSB = 1 mA
ichg_ma = (read_reg(0x1B) << 8) | read_reg(0x1C)

# Read VBUS (Input Voltage: Reg 0x1D MSB, 0x1E LSB) -> 1 LSB = 1 mV
vbus_mv = (read_reg(0x1D) << 8) | read_reg(0x1E)

print(f"Solar Input Voltage (VBUS): {vbus_mv} mV")
print(f"Solar Input Current (IBUS): {ibus_ma} mA")
print(f"Battery Charge Current (ICHG): {ichg_ma} mA")