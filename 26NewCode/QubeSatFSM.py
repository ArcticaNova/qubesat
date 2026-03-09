import time 

class QubeSatFSM():

    # initalizing some values/parts of the qubesat (still very incomplete atp)
        '''
            let mission time be counted in seconds since FSM starts
            for a task:
                if scheduled_later==False -> wait the amount of time specified by period 
                otherwise -> execute state immediately
        '''

    def __init__(self):
        self.state = State.idle #default state = charging mode 
        self.missionTime = 0.0 # how much time has passed so far, 0 at the beginning
        self.power = PowerLevel() 
        
        # making a dictionary with key = "equipment" and value = period (in seconds)
        # have to fill in the periods for the other things later on!!
        self.periods = {"beacon": 30*60, "battery-check": , "transition": , 'sd_card': 30*60, "burn_wire": , 
        "receive_data": , "init_payload": (30*60)}

        #boolean values to check different stages of mission
        self.experiment_started=False #this is True if experiment has started/isrunning and false if not 
        self.sd_card_initalized = False #shouldn't be initalized until after deployment 
        self.solar_panels_on=False 

        # boolean values to check that the equipment is functional 
        # initialize them to false (after they are checked -> every value should = True)
        self.equipment_check={"sd_card": False, "burn_wire": False, "payload": False, "solar_panel": False, "radio": False}

        # making a dictionary to be able to call each state 
        # should execute all of the actions in each state 
        self.tasks={State.IDLE: self.build_idle_tasks(), State.DEPLOY: self.build_deploy_tasks(), 
        State.SCIENCE: self.build_science_tasks(),self.COMMS: self.build_comms_tasks()}


    # building tasks for each of the states 

    # tasks that should be executed when in the idle state 
    def build_idle_tasks():
        tasks=[Task("Beacon", 1, self.periods["beacon"], schedule_later=False, func=self._task_beacon),
            Task("Battery Check", , self.periods["battery_check"],schedule_later=True, func=self._task_battery_check),
            Task("Transition Check", 3, self.periods["transition"], schedule_later=True,func=self._task_transition_check),]

    def build_deployment_tasks():
   
    def build_comms_tasks():

    
    def build_science_tasks():

    '''
        this state is entered when battery is below the low_power_threshold

    '''
    def run_idle(self): 

    





