from Tasks.log import LogTask as Task
from pycubed import cubesat
from state_machine import state_machine
from lib.alerts import alerts


class task(Task):
    name = 'safety'
    color = 'orange'

    timeout = 60 * 60  # 60 min

    # Battery temperature safe operating range (Celsius)
    BATTERY_TEMP_MIN = 0    # Minimum safe battery temperature
    BATTERY_TEMP_MAX = 5   # Maximum safe battery temperature
    
    # Hysteresis margins to prevent state jittering
    TEMP_MARGIN = 2  # Temperature margin for returning to normal operations

    def __init__(self):
        super().__init__()
        # Add battery temperature property to cubesat if it doesn't exist
        if not hasattr(cubesat, 'battery_temperature'):
            # Simulate battery temperature for testing (would be actual sensor reading in real system)
            cubesat._battery_temperature = 25.0  # Start at room temperature
            
            def get_battery_temp():
                """Simulated battery temperature - in real system this would read from battery management IC"""
                import random
                # Simulate temperature variations based on battery voltage and usage
                base_temp = 25.0
                voltage_factor = (cubesat.battery_voltage - 3.0) * 5  # Higher voltage = higher temp
                random_variation = random.uniform(-2, 2)
                cubesat._battery_temperature = max(0, min(60, base_temp + voltage_factor + random_variation))
                return cubesat._battery_temperature
            
            cubesat.battery_temperature = property(lambda self: get_battery_temp())

    def debug_status(self, vbatt, temp, batt_temp):
        self.debug(f'Voltage: {vbatt:.2f}V | CPU Temp: {temp:.2f}°C | Battery Temp: {batt_temp:.2f}°C', log=True)

    def is_battery_temp_safe(self, batt_temp):
        """Check if battery temperature is within safe operating range"""
        return self.BATTERY_TEMP_MIN <= batt_temp <= self.BATTERY_TEMP_MAX

    def is_battery_temp_safe_with_margin(self, batt_temp):
        """Check if battery temperature is within safe range with hysteresis margin"""
        return (self.BATTERY_TEMP_MIN + self.TEMP_MARGIN) <= batt_temp <= (self.BATTERY_TEMP_MAX - self.TEMP_MARGIN)

    def disable_non_critical_systems(self):
        """Disable non-critical systems when battery temperature is unsafe"""
        self.debug('Battery temperature unsafe - disabling non-critical systems', log=True)
        
        # Disable radio communications
        if hasattr(cubesat, 'radio') and cubesat.radio:
            try:
                cubesat.radio.listen = False
                self.debug('Radio communications disabled due to unsafe battery temperature', log=True)
            except Exception as e:
                self.debug(f'Failed to disable radio: {e}', log=True)
        
        # Could also disable other non-critical systems here:
        # - Camera operations
        # - Non-essential payload operations
        # - High-power transmissions

    def enable_non_critical_systems(self):
        """Re-enable non-critical systems when battery temperature is safe"""
        self.debug('Battery temperature safe - re-enabling non-critical systems', log=True)
        
        # Re-enable radio communications
        if hasattr(cubesat, 'radio') and cubesat.radio:
            try:
                cubesat.radio.listen = True
                self.debug('Radio communications re-enabled - battery temperature safe', log=True)
            except Exception as e:
                self.debug(f'Failed to re-enable radio: {e}', log=True)

    def safe_mode(self, vbatt, temp, batt_temp):
        # Needs to be done here, and not in transition function due to #306
        cubesat.enable_low_power()
        
        # Check all safety conditions with margins to prevent jittering
        voltage_safe = vbatt >= cubesat.LOW_VOLTAGE + 0.1
        cpu_temp_safe = temp < cubesat.HIGH_TEMP - 1
        battery_temp_safe = self.is_battery_temp_safe_with_margin(batt_temp)
        
        # Log any unsafe conditions
        if not voltage_safe:
            self.debug(f'Voltage too low ({vbatt:.2f}V < {cubesat.LOW_VOLTAGE + 0.1:.2f}V)', log=True)
            alerts.set(self.debug, 'voltage_low')
        
        if not cpu_temp_safe:
            self.debug(f'CPU temp too high ({temp:.2f}°C >= {cubesat.HIGH_TEMP - 1:.2f}°C)', log=True)
            alerts.set(self.debug, 'temp_high')
            
        if not battery_temp_safe:
            self.debug(f'Battery temp unsafe ({batt_temp:.2f}°C not in safe range {self.BATTERY_TEMP_MIN + self.TEMP_MARGIN:.1f}-{self.BATTERY_TEMP_MAX - self.TEMP_MARGIN:.1f}°C)', log=True)
            alerts.set(self.debug, 'battery_temp_unsafe')
            self.disable_non_critical_systems()
        
        # Only exit safe mode if ALL conditions are safe
        if voltage_safe and cpu_temp_safe and battery_temp_safe:
            self.debug_status(vbatt, temp, batt_temp)
            self.debug(f'All safety conditions met, switching back to {state_machine.previous_state} mode', log=True)
            self.enable_non_critical_systems()
            alerts.clear(self.debug, 'battery_temp_unsafe')
            state_machine.switch_to(state_machine.previous_state)
        else:
            self.debug_status(vbatt, temp, batt_temp)

    def other_modes(self, vbatt, temp, batt_temp):
        # Check all safety conditions
        voltage_unsafe = vbatt < cubesat.LOW_VOLTAGE
        cpu_temp_unsafe = temp > cubesat.HIGH_TEMP
        battery_temp_unsafe = not self.is_battery_temp_safe(batt_temp)
        
        # Handle voltage safety
        if voltage_unsafe:
            self.debug(f'Voltage too low ({vbatt:.2f}V < {cubesat.LOW_VOLTAGE:.2f}V) switch to safe mode', log=True)
            alerts.set(self.debug, 'voltage_low')
            state_machine.switch_to('Safe')
            return
            
        # Handle CPU temperature safety
        if cpu_temp_unsafe:
            self.debug(f'CPU temp too high ({temp:.2f}°C > {cubesat.HIGH_TEMP:.2f}°C) switching to safe mode', log=True)
            alerts.set(self.debug, 'temp_high')
            state_machine.switch_to('Safe')
            return
            
        # Handle battery temperature safety
        if battery_temp_unsafe:
            self.debug(f'Battery temp unsafe ({batt_temp:.2f}°C not in safe range {self.BATTERY_TEMP_MIN:.1f}-{self.BATTERY_TEMP_MAX:.1f}°C) switching to safe mode', log=True)
            alerts.set(self.debug, 'battery_temp_unsafe')
            self.disable_non_critical_systems()
            state_machine.switch_to('Safe')
            return
        
        # All conditions are safe
        self.debug_status(vbatt, temp, batt_temp)
        alerts.clear(self.debug, 'temp_high')
        alerts.clear(self.debug, 'voltage_low')
        alerts.clear(self.debug, 'battery_temp_unsafe')
        
        # Ensure non-critical systems are enabled when safe
        self.enable_non_critical_systems()

    async def main_task(self):
        """
        Enhanced safety monitoring including battery temperature.
        If voltage is too low, CPU temp too high, or battery temp is unsafe, switch to safe mode.
        If all conditions are safe, switch back to normal operations.
        Battery temperature monitoring prevents communications and other non-critical operations
        when battery temperature is outside safe operating range.
        """
        vbatt = cubesat.battery_voltage
        temp = cubesat.temperature_cpu
        batt_temp = cubesat.battery_temperature
        
        if state_machine.state == 'Safe':
            self.safe_mode(vbatt, temp, batt_temp)
        else:
            self.other_modes(vbatt, temp, batt_temp)