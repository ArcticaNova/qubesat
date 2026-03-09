# this is a very general class that will represent the type of every "action" during the mission

class Task():


    # each class should have a name (String)
    # priority (int) that numerically quantifies/can be sorted to determine order relative to another
    # the perod = amount of time needed to wait before task is execued 
    # schedule_later (boolean) determines if task needs to be executed now or later
    # func is the method it calls for action to be executed 

     def __init__(self, name, priority, period, schedule_later, func):
        self.name = name
        self.priority = priority
        self.period = period
        self.schedule_later = schedule_later
        self.func = func                    
        self.last_run_time  = None          # in seconds, last_run_time represents the last time it was run, should be None at the beginning

    ''' 
        this method determines if the function for the task needs to be run right now 
        if last_run_time is None (task has never been run before) -> should run it
        otherwise -> see how much current time - last run time is (if it's more than period -> should run again)
    '''
    def is_due(self, now: float):
        if self.last_run_time is None:
            return True
        time_passed=now-self.last_run_time
        return (time_passed >= self.period_s)

    # this method should actually execute the task 
    def run(self):
        result = self.func()
        self.last_run_time = time.monotonic() # after the method is run -> record the last run_time with the current time 
        return result # this should return whatever result the task has 

