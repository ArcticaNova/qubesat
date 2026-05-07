import time
from pycubed import cubesat
from StateCodeGenerator import StateID, StateCodec
from PowerLevel import PowerLevel
from BurnWire import BurnWire
from Task import Task
from Comms import CommsManager, configure_radio, build_beacon_packet

# Battery voltage thresholds
HIGH_LEVEL_THRESHOLD = 8.4   # enforced by pycubed hardware
LOW_LEVEL_THRESHOLD  = 6.0   # transition to IDLE for charging

# Minimum time to stay in IDLE before attempting deployment (45-minute safety holdoff)
DEPLOY_HOLDOFF_S = 45 * 60


class QubeSatFSM:

    def __init__(self):
        self.state        = StateID.IDLE
        self.current_code = StateCodec.encode(StateID.IDLE)
        self.mission_time = 0.0

        self.power = PowerLevel()

        # mission flags
        self.experiment_started  = False
        self.sd_card_initialized = False
        self.solar_panels_on     = False
        self.log_file            = None
        self.latest_data         = None

        # equipment health
        self.equipment_check = {
            "sd_card":     False,
            "burn_wire":   False,
            "payload":     False,
            "solar_panel": False,
            "radio":       False,
        }

        # task periods in seconds
        self.periods = {
            "beacon":        30 * 60,
            "battery_check": 60,
            "transition":    10,
            "sd_card":       30 * 60,
            "burn_wire":     30 * 60,
            "receive_data":  10,
            "record_memory": 10,
            "init_payload":  30 * 60,
        }

        # initialise comms / radio
        try:
            radio = configure_radio()
            self.comms = CommsManager(radio)
            self.comms.state_code     = self.current_code
            self.comms.on_state_command = self._on_ground_state_command
            self.comms.on_tx_window   = self._on_tx_window
            self.equipment_check["radio"] = True
            print("[FSM] Radio initialized.")
        except Exception as e:
            print("[FSM] Radio init failed:", e)
            self.comms = None

        # build initial task list
        self.tasks = self._build_tasks_for_state(self.state)

    # ── Task list builders ──────────────────────────────────────────────────────

    def _build_tasks_for_state(self, state):
        builders = {
            StateID.IDLE:    self.build_idle_tasks,
            StateID.DEPLOY:  self.build_deploy_tasks,
            StateID.SCIENCE: self.build_science_tasks,
            StateID.COMMS:   self.build_comms_tasks,
        }
        return builders[state]()

    def build_idle_tasks(self):
        return [
            Task("Beacon",           1, self.periods["beacon"],        schedule_later=False, func=self._task_beacon),
            Task("Battery Check",    2, self.periods["battery_check"], schedule_later=True,  func=self._task_battery_check),
            Task("Transition Check", 3, self.periods["transition"],    schedule_later=True,  func=self._task_transition_check),
        ]

    def build_deploy_tasks(self):
        return [
            Task("SD Card",          1, self.periods["sd_card"],       schedule_later=False, func=self._task_init_sd_card),
            Task("Burn Wire",        2, self.periods["burn_wire"],      schedule_later=True,  func=self._task_activate_burn_wire),
            Task("Battery Check",    3, self.periods["battery_check"], schedule_later=True,  func=self._task_battery_check),
            Task("Beacon",           4, self.periods["beacon"],        schedule_later=True,  func=self._task_beacon),
            Task("Transition Check", 5, self.periods["transition"],    schedule_later=True,  func=self._task_transition_check),
        ]

    def build_comms_tasks(self):
        return [
            Task("Solar Panel Enable", 1, self.periods["battery_check"], schedule_later=False, func=self._task_enable_solar_panels),
            Task("Battery Check",      2, self.periods["battery_check"], schedule_later=True,  func=self._task_battery_check),
            Task("Beacon",             3, self.periods["beacon"],        schedule_later=True,  func=self._task_beacon),
            Task("Transition Check",   4, self.periods["transition"],    schedule_later=True,  func=self._task_transition_check),
        ]

    def build_science_tasks(self):
        return [
            Task("Initialize Payload", 1, self.periods["init_payload"],  schedule_later=False, func=self._task_init_payload),
            Task("Receive Data",       2, self.periods["receive_data"],   schedule_later=True,  func=self._task_receive_data),
            Task("Record to Memory",   3, self.periods["record_memory"],  schedule_later=True,  func=self._task_record_memory),
            Task("Transition Check",   4, self.periods["transition"],     schedule_later=True,  func=self._task_transition_check),
        ]

    # ── State transitions ───────────────────────────────────────────────────────

    def transition(self, new_state):
        if new_state == self.state:
            return
        print(f"[FSM] {self.state} -> {new_state}")
        self.state        = new_state
        self.current_code = StateCodec.encode(new_state)
        if self.comms:
            self.comms.state_code = self.current_code
        self.tasks = self._build_tasks_for_state(new_state)

    def _on_ground_state_command(self, new_code):
        """Called by CommsManager when an authenticated ground command changes state."""
        try:
            new_state = StateCodec.decode(new_code)
            if new_state is not None:
                self.transition(new_state)
        except ValueError as e:
            print("[FSM] Bad state code from ground:", e)

    def _on_tx_window(self, window_num, cadence):
        """Push a telemetry beacon on every `cadence`-th TX window."""
        if window_num % cadence == 0:
            self._push_beacon()

    # ── Task implementations ────────────────────────────────────────────────────

    def _task_battery_check(self):
        try:
            vbatt = cubesat.battery_voltage
            print(f"[BATTERY] {vbatt:.2f} V")
            if vbatt <= LOW_LEVEL_THRESHOLD:
                print("[BATTERY] Low — going IDLE.")
                self.transition(StateID.IDLE)
        except Exception as e:
            print("[BATTERY] Error:", e)

    def _task_beacon(self):
        """Build and enqueue a TinyGS-compatible telemetry beacon."""
        self._push_beacon()

    def _push_beacon(self):
        """Collect live telemetry, build a beacon packet, and push it to the TX queue."""
        if not self.comms:
            return
        try:
            vbatt = cubesat.battery_voltage
        except Exception:
            vbatt = 0.0
        try:
            temp_c = cubesat.temperature
        except Exception:
            temp_c = 0.0

        packet = build_beacon_packet(
            self.current_code,
            vbatt,
            temp_c,
            int(self.mission_time),
        )
        self.comms.push_telemetry(packet)
        print(
            f"[BEACON] Queued: state={self.current_code} "
            f"batt={vbatt:.2f}V temp={temp_c:.1f}C t={int(self.mission_time)}s"
        )

    def _task_transition_check(self):
        """Evaluate whether to advance to the next FSM state."""
        if self.state == StateID.IDLE:
            # Move to DEPLOY after the deployment safety holdoff
            if self.mission_time >= DEPLOY_HOLDOFF_S:
                print("[FSM] Holdoff complete — transitioning to DEPLOY.")
                self.transition(StateID.DEPLOY)

        elif self.state == StateID.DEPLOY:
            # Move to SCIENCE once burn wire has fired and SD card is ready
            if self.equipment_check["burn_wire"] and self.sd_card_initialized:
                print("[FSM] Deployment complete — transitioning to SCIENCE.")
                self.transition(StateID.SCIENCE)

        # SCIENCE <-> COMMS transitions are driven by ground commands only
        # (_on_ground_state_command handles those)

    def _task_enable_solar_panels(self):
        try:
            charging_current = cubesat.charging_current
            print(f"[COMMS] Charge current: {charging_current:.3f} A")
            self.solar_panels_on = charging_current > 0
            self.equipment_check["solar_panel"] = self.solar_panels_on
            if self.solar_panels_on:
                print("[COMMS] Solar panels confirmed charging.")
            else:
                print("[COMMS] Warning: no charge current detected.")
        except Exception as e:
            print("[COMMS] Solar panel check error:", e)

    def _task_activate_burn_wire(self):
        try:
            burn = BurnWire()
            burn.cubesatBurn("1", 0.25, 30)  # wire 1, 25% duty cycle, 30 s
            self.solar_panels_on = True
            self.equipment_check["burn_wire"] = True
            print(f"[DEPLOY] Burn wire status: {burn.burningCheck()}")
        except Exception as e:
            print("[DEPLOY] Burn wire error:", e)

    def _task_init_sd_card(self):
        try:
            self.log_file = cubesat.new_file('/data/mission', binary=False)
            self.sd_card_initialized = True
            self.equipment_check["sd_card"] = True
            print(f"[DEPLOY] SD card ready: {self.log_file}")
        except Exception as e:
            self.sd_card_initialized = False
            print("[DEPLOY] SD card init failed:", e)

    def _task_init_payload(self):
        # Fill in payload-specific initialization (IMU, camera, etc.)
        print("[SCIENCE] Payload init (not yet implemented).")

    def _task_receive_data(self):
        # Read from your payload and store the result in self.latest_data.
        print("[SCIENCE] Receive data (not yet implemented).")

    def _task_record_memory(self):
        if not self.sd_card_initialized or self.log_file is None:
            print("[DATA] SD not ready, skipping record.")
            return
        if self.latest_data is None:
            print("[DATA] No data to record.")
            return
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{self.mission_time:.1f},{self.latest_data}\n")
            print(f"[DATA] Recorded at t={self.mission_time:.1f}s")
        except Exception as e:
            print("[DATA] Record error:", e)

    def halt_transmission(self):
        self.tasks = [t for t in self.tasks if t.name != "Beacon"]

    # ── Main loop ───────────────────────────────────────────────────────────────

    def run(self):
        print("[FSM] Mission start.")
        while True:
            try:
                now = time.monotonic()
                self.mission_time = now

                for task in self.tasks:
                    if task.is_due(now):
                        task.run()

                if self.comms:
                    self.comms.update()

                time.sleep(0.1)

            except Exception as e:
                print("[FSM] FATAL:", e)
                try:
                    cubesat.c_state_err += 1
                    cubesat.log(f"{e},{cubesat.c_state_err},{cubesat.c_boot}")
                except Exception:
                    pass
                time.sleep(10)
                cubesat.micro.on_next_reset(cubesat.micro.RunMode.NORMAL)
                cubesat.micro.reset()
