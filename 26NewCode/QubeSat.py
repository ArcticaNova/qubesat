class QubeSat():

    # initalizing some values/parts of the qubesat (still very incomplete atp)
    def __init__(self):
        self.SD=SDCard()
        self.power=PowerLevel() 
        self.missionTime=0.0 # how much time has passed so far, 0 at the beginning
        self.experiment_Active=False # this is True if experiment has started/isrunning and false if not 
    