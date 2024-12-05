import psutil

def battery(self):
    battery = psutil.sensors_battery()
    percent = battery.percent
    power_plugged = battery.power_plugged

    if power_plugged:
        status = "Зарядка"
    else:
        status = "Разрядка"

    print(f"Уровень батареи: {percent}% ({status})")