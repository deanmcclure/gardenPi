import traceback
import serial
#import RPi.GPIO as GPIO
import datetime
import time
import signal
import threading
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from garduinoLib import *


ser = serial.Serial(
    port='/dev/ttyUSB0',
    #port='COM4',
    timeout=5,
    baudrate=57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)

print "starting"
#read stupid bitlash starting line
#arduino.readline()

#hydroponic res, different system but monitored on this unit
hydroRes = localSensor(sensorGPIO = 24, powerGPIO = 26)

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
capsicum = PlantMon('Capsicum',capsicumPump,arduino,soil=capsicumSoil,reservoir=capsicumRes)
tomfar = PlantMon('Tomato Far',tomfarPump,arduino,reservoir=tomfarRes)
tomclose = PlantMon('Tomato Close',tomclosePump,arduino,reservoir=tomcloseRes)

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type',    'text/html')
        self.end_headers()
        self.wfile.write('Hydropronic Reservoir Dry?: {dry}<br>'.format(dry = 'Yes' if hydroRes.read() else 'No'))
        self.wfile.write('<br><br>')
        for plant in PlantMon._registry:
            self.wfile.write('<b>{plant}</b><br>'.format(plant = plant.name))
            if plant.fault:
                self.wfile.write('WATERING SYSTEM FAULTED<br>')
            else:
                self.wfile.write('Watering System Operational<br>')
            if plant.soil:
                self.wfile.write('Soil is currently at {adc} dryness (water at {dry})<br>'.format(adc = plant.soil.adc, dry =
                soildryADC))
            if plant.reservoir:
                self.wfile.write('Reservoir is currently at {adc} dryness (water at {dry})<br>'.format(adc = plant.reservoir.adc,
                dry = reservoirdryADC))
            if plant.lastWatered:
                self.wfile.write('Last watered {time}<br>'.format(time = plant.lastWatered.strftime("%Y/%m/%d %H:%M:%S")))
                self.wfile.write('Watered {count} time(s) since {time}<br>'.format(count = plant.wateredCount, time =
                inittime.strftime("%Y/%m/%d %H:%M:%S")))
            else:
                self.wfile.write('Not watered since {time}<br>'.format(time = inittime.strftime("%Y/%m/%d %H:%M:%S")))
            self.wfile.write('<br><br>')

def sigint_handler(signum,frame):
    shutdown()

def shutdown():
    print 'shutting down web server'
    server.socket.close()
    print 'shutting down all pumps'
    for pump in Pump._registry:
        pump.off()
    for plant in PlantMon._registry:
        print 'shutting down {plant} pump'.format(plant = plant.name)
        logging.info('shutting down {plant} pump'.format(plant = plant.name))
        plant.pump.off()
    exit()

#setup webserver
server = HTTPServer(('0.0.0.0', 80), MyHandler)
signal.signal(signal.SIGINT, sigint_handler)
webserverThread = threading.Thread(target=server.serve_forever)
webserverThread.start()


while(True):
    print 'looping'
    print 'Checking Hydroponic Reservoir'
    hydroRes.read()
    waterAll()
    time.sleep(300)

