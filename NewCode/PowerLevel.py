class PowerLevel():
    level=0.0
    high_level_threshold=80.0
    low_level_threshold=20.0
    
    def __init__(self):
        self.level=95.0 # this is arbitrary, should be changed, also should probably be a measured value
    
    # if power level is too low -> can't carry out experiment -> needs to go to recharging/idle mode
    def is_low():
        return self.level<=self.low_level_threshold
    
    # if it's high enough -> can start or resume experiment (either from deployment or switch from idle)
    def is_high():
        return self.level>=self.high_level_threshold
    
    # should return the current level at any point <- need to add measurement aspect later
    def currLevel():
        return self.level
    
