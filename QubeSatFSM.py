class QubeSatFSM():
  # constructor for cubesat
  def__init__(self):

    # need to initalize the hardware 
    self.sd = SD() # initialize an sd card 
    self.power = PowerSystem() #initalize power 
    

    # also need to initialize states
    self.mission_time=0.0 # keeps track of how much time has passed 
    self.started_experiment # true = experiment has started


