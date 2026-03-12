
def is_due(self, now: float):
    if self.last_run_test == None:
        return True
    time_elapsed = now - self.last_run_time
    if time_elapsed >= self.period:
        return True
    return False


        # this method determines if the function for the task needs to be run right now 
        #if last_run_time is None (task has never been run before) -> should run it
        #otherwise -> see how much current time - last run time is (if it's more than period -> should run again)