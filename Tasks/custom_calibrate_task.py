from Tasks.template_task import Task
from time import sleep

class task(Task):
    priority = 1
    frequency = 1
    name='calibrate'
    color='pink'

    async def main_task(self):
        dc = self.cubesat.data_cache
        if 'calibrate_timer' not in dc:
            dc['calibrate_timer'] = 0

        if dc['calibrate_timer'] == 0:
            self.cubesat.RGB = (255, 255, 255)

            if (
                'gyro_z_history' not in self.cubesat.data_cache or
                len(self.cubesat.data_cache['gyro_z_history']) < 10
            ):
                return
            else:
                total = 0
                for _ in range(len(dc['gyro_z_history'])):
                    num = dc['gyro_z_history'].popleft()
                    total += num
                    dc['gyro_z_history'].append(num)
                avg = total / len(dc['gyro_z_history'])
                self.cubesat.data_cache['gyro_z_calibration'] = avg
                dc['calibrate_timer'] = 180
        else:
            dc['calibrate_timer'] -= 1

        
