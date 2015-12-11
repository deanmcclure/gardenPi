import traceback
import serial
#import RPi.GPIO as GPIO
import datetime
import time
from garduinoLib import *

ser = serial.Serial(
    port='/dev/ttyUSB0',
    #port='COM4',
    baudrate=57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)

print "starting"
#read stupid bitlash starting line
#arduino.readline()

#Access to Arduino via bitlash via Serial over USB
arduino = BitlashArduino(ser)

#Sensor Power Pin
sensorPower = SensorPower('senseon()\r','senseoff()\r',arduino)

#Sensors
capsicumSoil = Sensor('print a7read()\r',arduino,sensorPower)
capsicumRes = Sensor('print a6read()\r',arduino,sensorPower)
tomfarRes = Sensor('print a5read()\r',arduino,sensorPower)
tomcloseRes = Sensor('print a4read()\r',arduino,sensorPower)

#pumps
capsicumPump = Pump('p1on()\r','p1off()\r',arduino)
tomfarPump = Pump('p2on()\r','p2off()\r',arduino)
tomclosePump = Pump('p3on()\r','p3off()\r',arduino)

#plants
try:
    capsicum = PlantMon('capsicum',capsicumPump,arduino,soil=capsicumSoil,reservoir=capsicumRes)
    capsicum.start()
    tomfar = PlantMon('Tomato Far',tomfarPump,arduino,reservoir=tomfarRes)
    tomfar.start()
    tomclose = PlantMon('Tomato Close',tomclosePump,arduino,reservoir=tomcloseRes)
    tomclose.start()
except:
    print "failed initialisation"
    shutdown()

while(True):
    time.sleep(1)
