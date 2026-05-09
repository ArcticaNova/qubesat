# initializes power of the cubesatz and allows it to check if there's enough power 

class PowerSystem(): 
  high_threshold=80.0 # this is arbitrary placeholder value rn, NEED TO BE UPDATED WITH REAL VALUES
  low_threshold=20.0 # again, NEED TO BE UPDATED
  level=0.0

  # also might need to be changed since instead of setting it with the assumption it's at full power, 
  # it should instead measure data to get the power level 
  def__init__():
    self.level=95.0 #should start/be initalized at full power, arbitrary place holder value rn 
  
  # method to return the current powerlevel
  def level():
    return self.level 

  # means power is low/not enough -> needs to go to idle/recharging state 
  def is_low():
    return self.level<=low_threshold

  # means power is high enough -> can go from idle state back to doing experiment
  def is_high():
    return self.level>=high_threshold
  
