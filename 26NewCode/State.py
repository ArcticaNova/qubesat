
# theoretically, this is the class that can switch between the deployment + idle + science states 
class State():
    
    # instance variables:
    # schedule_later (boolean)
    # period (boolean)


    def __init__(self, period, schedule_later, func):
        self.period=period
        self.schedule_later=schedule_later
        self.func=func
    
    
