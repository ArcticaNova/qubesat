# PyCubed v05 solar-charging test
# Copy to the CIRCUITPY drive as code.py (or main.py), then open the serial
# console (Mu, `screen /dev/ttyACM0 115200`, PuTTY, etc.) to watch the output.
#
# What it does:
#   1. Takes a baseline with the panels dark/disconnected (BASELINE_S seconds)
#   2. Logs once per second while you expose the panels to light
#   3. Prints a verdict at the end

import time
from pycubed import cubesat

BASELINE_S = 10     # seconds of "panels covered" baseline
TEST_S = 60         # seconds of "panels lit" logging
CURRENT_MIN = 0.5   # charge_current above baseline + this counts as "charging"
                    # (same units charge_current() returns)


def read(name):
    """Read a cubesat attribute that may be a property OR a method.
    Returns None if it doesn't exist or errors."""
    try:
        val = getattr(cubesat, name)
        return val() if callable(val) else val
    except Exception as e:
        print("  (could not read {}: {})".format(name, e))
        return None


def charge_current():
    # docs mention both spellings across versions
    for name in ("charge_current", "charging_current"):
        if hasattr(cubesat, name):
            return read(name)
    return None


def power_monitor():
    """Optional: the board's separate power monitor (battery/system side).
    Skipped silently if this firmware doesn't expose it under this name."""
    pm = getattr(cubesat, "power_mon", None)
    if pm is None:
        return None
    try:
        return pm.bus_voltage, pm.current
    except Exception:
        return None


def sample():
    return {
        "vbatt": read("battery_voltage"),
        "ichg": charge_current(),
        "solar": read("solar_charging"),
        "pm": power_monitor(),
    }


def fmt(x):
    return "n/a" if x is None else ("{:.3f}".format(x) if isinstance(x, float) else str(x))


def show(tag, s):
    line = "[{}] Vbatt={}  charge_current={}  solar_charging={}".format(
        tag, fmt(s["vbatt"]), fmt(s["ichg"]), fmt(s["solar"]))
    if s["pm"]:
        line += "  pwr_mon(V,I)=({},{})".format(fmt(s["pm"][0]), fmt(s["pm"][1]))
    print(line)


print("=" * 60)
print("PyCubed solar test. Make sure a battery is attached and NOT full")
print("(2S Li-ion floats at 8.4 V; ~7.4 V is a good starting point).")
print("=" * 60)

# ---- Phase 1: baseline (cover / disconnect panels) ----
print("\nPHASE 1: COVER the panels (or switch the supply off) for {}s".format(BASELINE_S))
base_i = []
for _ in range(BASELINE_S):
    s = sample()
    show("dark ", s)
    if isinstance(s["ichg"], (int, float)):
        base_i.append(s["ichg"])
    time.sleep(1)
baseline = (sum(base_i) / len(base_i)) if base_i else 0
print("Baseline charge_current: {}".format(fmt(baseline)))

# ---- Phase 2: expose to light ----
print("\nPHASE 2: EXPOSE the panels to strong light / turn the supply ON ({}s)".format(TEST_S))
time.sleep(2)
max_i = baseline
solar_true = 0
v_first = v_last = None
for _ in range(TEST_S):
    s = sample()
    show("light", s)
    if isinstance(s["ichg"], (int, float)):
        max_i = max(max_i, s["ichg"])
    if s["solar"]:
        solar_true += 1
    if isinstance(s["vbatt"], (int, float)):
        v_first = s["vbatt"] if v_first is None else v_first
        v_last = s["vbatt"]
    time.sleep(1)

# ---- Verdict ----
print("\n" + "=" * 60)
print("RESULTS")
print("  baseline charge_current : {}".format(fmt(baseline)))
print("  peak charge_current     : {}".format(fmt(max_i)))
print("  solar_charging True in  : {}/{} samples".format(solar_true, TEST_S))
print("  Vbatt start -> end      : {} -> {}".format(fmt(v_first), fmt(v_last)))

charging_by_current = (max_i - baseline) > CURRENT_MIN
if solar_true > 0 and charging_by_current:
    print("  PASS: solar input detected AND charge current flowing.")
elif solar_true > 0 or charging_by_current:
    print("  PARTIAL: only one indicator fired. Check light level / battery")
    print("           state (see troubleshooting notes).")
else:
    print("  FAIL: no solar charging detected. Check: battery attached and")
    print("        not full, RBF/inhibit jumpers, panel polarity & Voc, light")
    print("        intensity (desk lamps are usually too weak).")
print("=" * 60)
