from Tasks.template_task import Task

class task(Task):
    priority = 6
    frequency = 5
    name = 'custom'
    color = 'yellow'

    async def main_task(self):
        dc = self.cubesat.data_cache

        if 'gyro_z_calibration' not in dc or 'imu' not in dc:
            return  

        gz = dc['imu']['gyro'][2]
        bias = dc['gyro_z_calibration']
        rate_dps = gz - bias

        angle_deg = dc.get('yaw_angle_deg', 0.0)

        dt = 1.0 / self.frequency  # 0.2 s
        angle_deg += rate_dps * dt

        if angle_deg >= 180.0:
            angle_deg -= 360.0
        elif angle_deg < -180.0:
            angle_deg += 360.0

        in_pos_range = (angle_deg >= 0.0)  
        if in_pos_range:
            self.cubesat.RGB = (0, 0, 255)
        else:
            self.cubesat.RGB = (255, 0, 0)

        dc['yaw_angle_deg'] = angle_deg
        dc['yaw_in_pos_range'] = in_pos_range

        self.debug(f"Yaw: {angle_deg:.2f}°, pos_range={in_pos_range}", 2)