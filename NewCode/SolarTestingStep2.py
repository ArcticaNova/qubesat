import microcontroller

print(microcontroller.cpu.voltage)

R_PROG = 3010.0   # ohms, from schematic/BOM
H_PROG = 988.0    # BAT:PROG current ratio, from datasheet
VREF = 3.3        # volts, measured at the MCU

def expected_raw(i_mA):
    v = (i_mA / 1000.0) * R_PROG / H_PROG
    return round(v / VREF * 65536)

for i in (40, 100, 200, 300, 400):
    print(i, "mA ->", expected_raw(i), "counts")