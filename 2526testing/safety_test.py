#!/usr/bin/env python3
"""
Battery Temperature Safety Test Script
Tests the enhanced safety system with simulated values and process verification
"""

import time
import random
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ProcessStatus:
    """Track status of various satellite processes"""
    name: str
    enabled: bool
    critical: bool  # Critical processes should never be disabled
    power_consumption: float


class MockCubesat:
    """Mock cubesat object for testing"""
    
    LOW_VOLTAGE = 3.3
    HIGH_TEMP = 60.0
    
    def __init__(self):
        self._battery_voltage = 3.8
        self._cpu_temperature = 25.0
        self._battery_temperature = 25.0
        self.low_power_enabled = False
        
        # Track all satellite processes
        self.processes = {
            'radio_comms': ProcessStatus('Radio Communications', True, False, 2.5),
            'camera': ProcessStatus('Camera Operations', True, False, 3.0),
            'payload_science': ProcessStatus('Science Payload', True, False, 1.8),
            'attitude_control': ProcessStatus('Attitude Control', True, True, 1.2),
            'power_management': ProcessStatus('Power Management', True, True, 0.5),
            'flight_computer': ProcessStatus('Flight Computer', True, True, 1.0),
            'telemetry_basic': ProcessStatus('Basic Telemetry', True, True, 0.3),
            'data_storage': ProcessStatus('Data Storage', True, False, 0.8),
        }
    
    @property
    def battery_voltage(self):
        return self._battery_voltage
    
    @property
    def temperature_cpu(self):
        return self._cpu_temperature
    
    @property
    def battery_temperature(self):
        return self._battery_temperature
    
    def set_battery_temperature(self, temp):
        """Simulate changing battery temperature"""
        self._battery_temperature = temp
        print(f"  Battery temperature set to: {temp:.1f}°C")
    
    def set_battery_voltage(self, voltage):
        """Simulate changing battery voltage"""
        self._battery_voltage = voltage
        print(f" Battery voltage set to: {voltage:.2f}V")
    
    def set_cpu_temperature(self, temp):
        """Simulate changing CPU temperature"""
        self._cpu_temperature = temp
        print(f"  CPU temperature set to: {temp:.1f}°C")
    
    def enable_low_power(self):
        """Enable low power mode"""
        self.low_power_enabled = True
        print("⚡ LOW POWER MODE ENABLED")
    
    def disable_low_power(self):
        """Disable low power mode"""
        self.low_power_enabled = False
        print("⚡ Low power mode disabled")
    
    def disable_process(self, process_name):
        """Disable a specific process"""
        if process_name in self.processes:
            if self.processes[process_name].critical:
                print(f" CRITICAL PROCESS PROTECTION: Cannot disable {self.processes[process_name].name}")
                return False
            else:
                self.processes[process_name].enabled = False
                print(f" DISABLED: {self.processes[process_name].name}")
                return True
        return False
    
    def enable_process(self, process_name):
        """Enable a specific process"""
        if process_name in self.processes:
            self.processes[process_name].enabled = True
            print(f" ENABLED: {self.processes[process_name].name}")
            return True
        return False
    
    def get_process_status(self):
        """Get current status of all processes"""
        enabled_processes = [p.name for p in self.processes.values() if p.enabled]
        disabled_processes = [p.name for p in self.processes.values() if not p.enabled]
        total_power = sum(p.power_consumption for p in self.processes.values() if p.enabled)
        
        return {
            'enabled': enabled_processes,
            'disabled': disabled_processes,
            'total_power_consumption': total_power
        }


class MockStateMachine:
    """Mock state machine for testing"""
    
    def __init__(self):
        self.state = 'Normal'
        self.previous_state = 'Normal'
        self.states = ['Normal', 'Safe', 'Low_Power']
    
    def switch_to(self, new_state):
        """Switch to a new state"""
        if new_state != self.state:
            self.previous_state = self.state
            self.state = new_state
            print(f" STATE CHANGE: {self.previous_state} → {self.state}")


class MockAlerts:
    """Mock alerts system"""
    
    def __init__(self):
        self.active_alerts = set()
    
    def set(self, debug_func, alert_name):
        """Set an alert"""
        self.active_alerts.add(alert_name)
        print(f" ALERT SET: {alert_name}")
    
    def clear(self, debug_func, alert_name):
        """Clear an alert"""
        if alert_name in self.active_alerts:
            self.active_alerts.remove(alert_name)
            print(f" ALERT CLEARED: {alert_name}")


class EnhancedSafetySystem:
    """Enhanced safety system with battery temperature monitoring"""
    
    # Battery temperature safe operating range (Celsius)
    BATTERY_TEMP_MIN = 0    # Minimum safe battery temperature
    BATTERY_TEMP_MAX = 5    # Maximum safe battery temperature (updated to match user's change)
    
    # Hysteresis margins to prevent state jittering
    TEMP_MARGIN = 2  # Temperature margin for returning to normal operations
    
    def __init__(self, cubesat, state_machine, alerts):
        self.cubesat = cubesat
        self.state_machine = state_machine
        self.alerts = alerts
        self.name = 'safety'
        
    def debug(self, message, log=False):
        """Debug logging function"""
        prefix = "  SAFETY:" if log else "   "
        print(f"{prefix} {message}")
    
    def is_battery_temp_safe(self, batt_temp):
        """Check if battery temperature is within safe operating range"""
        return self.BATTERY_TEMP_MIN <= batt_temp <= self.BATTERY_TEMP_MAX
    
    def is_battery_temp_safe_with_margin(self, batt_temp):
        """Check if battery temperature is within safe range with hysteresis margin"""
        return (self.BATTERY_TEMP_MIN + self.TEMP_MARGIN) <= batt_temp <= (self.BATTERY_TEMP_MAX - self.TEMP_MARGIN)
    
    def disable_non_critical_systems(self):
        """Disable non-critical systems when battery temperature is unsafe"""
        self.debug(' DISABLING NON-CRITICAL SYSTEMS: Battery temperature unsafe', log=True)
        
        disabled_count = 0
        for process_name, process in self.cubesat.processes.items():
            if not process.critical and process.enabled:
                if self.cubesat.disable_process(process_name):
                    disabled_count += 1
        
        print(f"📊 SHUTDOWN SUMMARY: {disabled_count} non-critical processes disabled")
        self.print_system_status()
    
    def enable_non_critical_systems(self):
        """Re-enable non-critical systems when battery temperature is safe"""
        self.debug(' RE-ENABLING NON-CRITICAL SYSTEMS: Battery temperature safe', log=True)
        
        enabled_count = 0
        for process_name, process in self.cubesat.processes.items():
            if not process.critical and not process.enabled:
                if self.cubesat.enable_process(process_name):
                    enabled_count += 1
        
        print(f"📊 RECOVERY SUMMARY: {enabled_count} non-critical processes re-enabled")
        self.print_system_status()
    
    def print_system_status(self):
        """Print current system status"""
        status = self.cubesat.get_process_status()
        print(f"📊 SYSTEM STATUS:")
        print(f"    Enabled: {len(status['enabled'])} processes")
        print(f"    Disabled: {len(status['disabled'])} processes")
        print(f"   ⚡ Power consumption: {status['total_power_consumption']:.1f}W")
        
        if status['disabled']:
            print(f"    Disabled processes: {', '.join(status['disabled'])}")
    
    def debug_status(self, vbatt, temp, batt_temp):
        """Print current sensor readings"""
        self.debug(f'Voltage: {vbatt:.2f}V | CPU: {temp:.1f}°C | Battery: {batt_temp:.1f}°C', log=True)
    
    def check_safety_conditions(self, vbatt, temp, batt_temp, with_margin=False):
        """Check all safety conditions"""
        if with_margin:
            voltage_safe = vbatt >= self.cubesat.LOW_VOLTAGE + 0.1
            cpu_temp_safe = temp < self.cubesat.HIGH_TEMP - 1
            battery_temp_safe = self.is_battery_temp_safe_with_margin(batt_temp)
        else:
            voltage_safe = vbatt >= self.cubesat.LOW_VOLTAGE
            cpu_temp_safe = temp <= self.cubesat.HIGH_TEMP
            battery_temp_safe = self.is_battery_temp_safe(batt_temp)
        
        return {
            'voltage_safe': voltage_safe,
            'cpu_temp_safe': cpu_temp_safe,
            'battery_temp_safe': battery_temp_safe,
            'all_safe': voltage_safe and cpu_temp_safe and battery_temp_safe
        }
    
    def safe_mode(self, vbatt, temp, batt_temp):
        """Handle safe mode operations"""
        self.cubesat.enable_low_power()
        
        # Check all safety conditions with margins
        conditions = self.check_safety_conditions(vbatt, temp, batt_temp, with_margin=True)
        
        # Log any unsafe conditions
        if not conditions['voltage_safe']:
            self.debug(f'Voltage too low ({vbatt:.2f}V < {self.cubesat.LOW_VOLTAGE + 0.1:.2f}V)', log=True)
            self.alerts.set(self.debug, 'voltage_low')
        
        if not conditions['cpu_temp_safe']:
            self.debug(f'CPU temp too high ({temp:.1f}°C >= {self.cubesat.HIGH_TEMP - 1:.1f}°C)', log=True)
            self.alerts.set(self.debug, 'temp_high')
        
        if not conditions['battery_temp_safe']:
            range_min = self.BATTERY_TEMP_MIN + self.TEMP_MARGIN
            range_max = self.BATTERY_TEMP_MAX - self.TEMP_MARGIN
            self.debug(f'Battery temp unsafe ({batt_temp:.1f}°C not in safe range {range_min:.1f}-{range_max:.1f}°C)', log=True)
            self.alerts.set(self.debug, 'battery_temp_unsafe')
            self.disable_non_critical_systems()
        
        # Only exit safe mode if ALL conditions are safe
        if conditions['all_safe']:
            self.debug_status(vbatt, temp, batt_temp)
            self.debug(f'All safety conditions met, switching back to {self.state_machine.previous_state} mode', log=True)
            self.enable_non_critical_systems()
            self.alerts.clear(self.debug, 'battery_temp_unsafe')
            self.cubesat.disable_low_power()
            self.state_machine.switch_to(self.state_machine.previous_state)
        else:
            self.debug_status(vbatt, temp, batt_temp)
    
    def other_modes(self, vbatt, temp, batt_temp):
        """Handle normal operation mode safety checks"""
        conditions = self.check_safety_conditions(vbatt, temp, batt_temp, with_margin=False)
        
        # Check for unsafe conditions
        if not conditions['voltage_safe']:
            self.debug(f'Voltage too low ({vbatt:.2f}V < {self.cubesat.LOW_VOLTAGE:.2f}V) switching to safe mode', log=True)
            self.alerts.set(self.debug, 'voltage_low')
            self.state_machine.switch_to('Safe')
            return
        
        if not conditions['cpu_temp_safe']:
            self.debug(f'CPU temp too high ({temp:.1f}°C > {self.cubesat.HIGH_TEMP:.1f}°C) switching to safe mode', log=True)
            self.alerts.set(self.debug, 'temp_high')
            self.state_machine.switch_to('Safe')
            return
        
        if not conditions['battery_temp_safe']:
            self.debug(f'Battery temp unsafe ({batt_temp:.1f}°C not in range {self.BATTERY_TEMP_MIN:.1f}-{self.BATTERY_TEMP_MAX:.1f}°C) switching to safe mode', log=True)
            self.alerts.set(self.debug, 'battery_temp_unsafe')
            self.disable_non_critical_systems()
            self.state_machine.switch_to('Safe')
            return
        
        # All conditions are safe
        self.debug_status(vbatt, temp, batt_temp)
        self.alerts.clear(self.debug, 'temp_high')
        self.alerts.clear(self.debug, 'voltage_low')
        self.alerts.clear(self.debug, 'battery_temp_unsafe')
        
        # Ensure non-critical systems are enabled when safe
        self.enable_non_critical_systems()
    
    def run_safety_check(self):
        """Main safety check function"""
        vbatt = self.cubesat.battery_voltage
        temp = self.cubesat.temperature_cpu
        batt_temp = self.cubesat.battery_temperature
        
        print(f"\n{'='*60}")
        print(f"SAFETY CHECK - State: {self.state_machine.state}")
        print(f"{'='*60}")
        
        if self.state_machine.state == 'Safe':
            self.safe_mode(vbatt, temp, batt_temp)
        else:
            self.other_modes(vbatt, temp, batt_temp)


def run_test_scenario(name, cubesat, safety_system, setup_func):
    """Run a test scenario"""
    print(f"\n{'TEST SCENARIO: ' + name:=^80}")
    setup_func(cubesat)
    time.sleep(0.5)  # Brief pause for readability
    safety_system.run_safety_check()
    time.sleep(1)  # Brief pause between scenarios


def main():
    """Main test function"""
    print("BATTERY TEMPERATURE SAFETY SYSTEM TEST")
    print("="*80)
    
    # Initialize mock objects
    cubesat = MockCubesat()
    state_machine = MockStateMachine()
    alerts = MockAlerts()
    safety_system = EnhancedSafetySystem(cubesat, state_machine, alerts)
    
    print(f"Safety temperature range: {safety_system.BATTERY_TEMP_MIN}°C to {safety_system.BATTERY_TEMP_MAX}°C")
    print(f"Initial system status:")
    safety_system.print_system_status()
    
    # Test scenarios
    test_scenarios = [
        ("Normal Operations", lambda c: c.set_battery_temperature(3.0)),
        ("Battery Too Cold", lambda c: c.set_battery_temperature(-5.0)),
        ("Battery Too Hot", lambda c: c.set_battery_temperature(10.0)),
        ("Battery Barely Safe", lambda c: c.set_battery_temperature(4.5)),
        ("Recovery Test", lambda c: c.set_battery_temperature(2.5)),
        ("Multiple Failures", lambda c: [c.set_battery_temperature(15.0), c.set_battery_voltage(3.1)]),
        ("CPU Overheat", lambda c: c.set_cpu_temperature(65.0)),
        ("All Systems Recovery", lambda c: [c.set_battery_temperature(3.0), c.set_battery_voltage(3.8), c.set_cpu_temperature(25.0)]),
    ]
    
    for name, setup_func in test_scenarios:
        run_test_scenario(name, cubesat, safety_system, setup_func)
    
    print(f"\n{'🏁 TEST COMPLETE':=^80}")
    print(f"Final state: {state_machine.state}")
    print(f"Active alerts: {list(alerts.active_alerts) if alerts.active_alerts else 'None'}")
    safety_system.print_system_status()


if __name__ == "__main__":
    main()