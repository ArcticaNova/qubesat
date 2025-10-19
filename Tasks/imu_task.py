# Task to obtain IMU sensor readings

from Tasks.template_task import Task
from collections import deque

class task(Task):
    priority = 5
    frequency = 5 # once every 10s
    name='imu'
    color = 'green'

    async def main_task(self):
        # take IMU readings

        readings = {
            'accel':self.cubesat.acceleration,
            'mag':  self.cubesat.magnetic,
            'gyro': self.cubesat.gyro,
        }

        if 'gyro_z_history' in self.cubesat.data_cache:
            self.cubesat.data_cache['gyro_z_history'].append(readings['gyro'][2])
            if len(self.cubesat.data_cache['gyro_z_history']) > 10 :
                self.cubesat.data_cache['gyro_z_history'].popleft()
        else:
            hist = deque((), 10)
            hist.append(readings['gyro'][2])
            self.cubesat.data_cache.update({'gyro_z_history':hist})

        # store them in our cubesat data_cache object
        self.cubesat.data_cache.update({'imu':readings})
        

        # print the readings with some fancy formatting
        self.debug('IMU readings (x,y,z)')
        for imu_type in self.cubesat.data_cache['imu']:
            self.debug(f"{imu_type:>5} {self.cubesat.data_cache['imu'][imu_type]}",2)



