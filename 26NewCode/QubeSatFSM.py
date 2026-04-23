import time 

class QubeSatFSM():
    high_level_threshold=80.0
    low_level_threshold=20.0

    '''
        let mission time be counted in seconds since FSM starts
        for a task:
            if scheduled_later==False -> wait the amount of time specified by period
            otherwise -> execute state immediately
    '''

    def __init__(self):
        self.state        = StateID.IDLE   # default state = idle / low power
        self.current_code = STATE_IDLE     # integer code matching self.state
        self.missionTime  = 0.0
        self.power        = PowerLevel()

        # period in seconds for each recurring task
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

        # boolean values to check different stages of mission
        self.experiment_started   = False
        self.sd_card_initialized  = False
        self.solar_panels_on      = False

        # boolean values to confirm equipment is functional
        self.equipment_check = {
            "sd_card": False, "burn_wire": False,
            "payload": False, "solar_panel": False, "radio": False,
        }

        self.tasks = self._build_tasks_for_state(self.state)

        # Set up comms — wrapped in try/except so a radio failure doesn't
        # prevent the rest of the FSM from starting.
        try:
            radio = configure_radio()
            self.comms = CommsManager(radio)
            self.comms.state_code       = self.current_code        # sync NVM to current state
            self.comms.on_state_command = self._on_remote_state_command
            self.comms.on_tx_window     = self._on_tx_window
            self.equipment_check["radio"] = True
        except Exception as e:
            print("[FSM] Radio init failed:", e)
            self.comms = None

    # ── Task list builders ─────────────────────────────────────────────────────

    def _build_tasks_for_state(self, state):
        builders = {
            StateID.IDLE:    self.build_idle_tasks,
            StateID.DEPLOY:  self.build_deploy_tasks,
            StateID.SCIENCE: self.build_science_tasks,
            StateID.DATA:    self.build_data_tasks,
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

    def build_science_tasks(self):
        return [
            Task("Initialize Payload", 1, self.periods["init_payload"],  schedule_later=False, func=self._task_init_payload),
            Task("Receive Data",       2, self.periods["receive_data"],   schedule_later=True,  func=self._task_receive_data),
            Task("Record to Memory",   3, self.periods["record_memory"],  schedule_later=True,  func=self._task_record_memory),
            Task("Transition Check",   4, self.periods["transition"],     schedule_later=True,  func=self._task_transition_check),
        ]

    def build_data_tasks(self):
        return [
            Task("Battery Check",    1, self.periods["battery_check"], schedule_later=True, func=self._task_battery_check),
            Task("Transition Check", 2, self.periods["transition"],    schedule_later=True, func=self._task_transition_check),
        ]

    def build_comms_tasks(self):
        # Comms runs in parallel via self.comms, not as a state.
        # This builder is kept in case it's needed for a dedicated comms window.
        return [
            Task("Solar Panel Enable", 1, self.periods["battery_check"], schedule_later=False, func=self._task_enable_solar_panels),
            Task("Battery Check",      2, self.periods["battery_check"], schedule_later=True,  func=self._task_battery_check),
            Task("Beacon",             3, self.periods["beacon"],        schedule_later=True,  func=self._task_beacon),
            Task("Transition Check",   4, self.periods["transition"],    schedule_later=True,  func=self._task_transition_check),
        ]

    # ── Main loop ──────────────────────────────────────────────────────────────

    def tick(self):
        """
        Call this every loop iteration from main.py / code.py.
        Runs all due FSM tasks, then runs one comms tick in parallel.
        """
        now = time.monotonic()
        for task in self.tasks:
            if task.is_due(now):
                task.run()
        if self.comms is not None:
            self.comms.update()

    # ── State transitions ──────────────────────────────────────────────────────

    def transition(self, new_state):
        if new_state == self.state:
            return  # already here, do nothing
        self.state        = new_state
        self.current_code = _state_to_code(new_state)
        if self.comms is not None:
            self.comms.state_code = self.current_code   # keep NVM in sync
        self.tasks = self._build_tasks_for_state(new_state)

    def task_battery_check():
        level = self.power.curr_level() # this has to be connected to some sort of hardware call to check battery 
        if level < low_level_threshold: 
            self.transition(StateID.IDLE)

    def halt_transmission(self):
        """Stop all radio activity immediately and remove the beacon task."""
        if self.comms is not None:
            self.comms.state_code = STATE_STOP   # makes comms.update() a no-op
        self.tasks = [t for t in self.tasks if t.name != "Beacon"]

    # ── Comms callbacks ────────────────────────────────────────────────────────

    def _on_remote_state_command(self, code):
        """
        Called by CommsManager when a valid encrypted state command arrives from ground.
        Maps the integer code back to a StateID and triggers the FSM transition.
        """
        if code == STATE_STOP:
            self.halt_transmission()
            return
        new_state = _code_to_state(code)
        if new_state is not None:
            self.transition(new_state)

    def _on_tx_window(self, window_num, cadence):
        """
        Called by CommsManager at the start of every TX window.
        Push telemetry every N windows as configured by cadence.
        Replace the push_telemetry() call with richer data when telemetry is ready.
        """
        if self.comms is None:
            return
        if window_num % cadence == 0:
            self.comms.push_telemetry(bytes([self.comms.state_code]))

    # ── Task implementations (stubs — wire to hardware calls) ─────────────────

    def _task_battery_check(self):
        level = self.power.curr_level()
        if level < self.low_level_threshold:
            self.transition(StateID.IDLE)

    def _task_beacon(self): pass
    def _task_transition_check(self): pass
    def _task_init_sd_card(self): pass
    def _task_activate_burn_wire(self): pass
    def _task_enable_solar_panels(self): pass # lowkey shouldnt it always be turned on?
    def _task_init_payload(self): pass
    def _task_receive_data(self): pass
    def _task_record_memory(self): pass


# ── Code ↔ StateID helpers ─────────────────────────────────────────────────────
# These map between the integer codes used by Comms.py and the StateID enum
# used by the FSM. Must stay in sync with both StateCodeGenerator.py and Comms.py.

def _code_to_state(code):
    return {
        STATE_IDLE:    StateID.IDLE,
        STATE_DEPLOY:  StateID.DEPLOY,
        STATE_SCIENCE: StateID.SCIENCE,
        STATE_DATA:    StateID.DATA,
    }.get(code)


def _state_to_code(state):
    return {
        StateID.IDLE:    STATE_IDLE,
        StateID.DEPLOY:  STATE_DEPLOY,
        StateID.SCIENCE: STATE_SCIENCE,
        StateID.DATA:    STATE_DATA,
    }.get(state, STATE_STOP)
