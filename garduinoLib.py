import traceback
import serial
import datetime
import time
import signal
import logging
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import threading

logging.basicConfig(level=logging.INFO, 
                    filename='/home/pi/garden/log/garden.log', # log to this file
                    format='%(asctime)s %(message)s'
                    ) # include timestamp

#constants
soildryADC = 400
reservoirdryADC = 750
pumptimemax = datetime.timedelta(seconds = 30)
pumptimemin = 10
inittime = datetime.datetime.now()

class PlantMon(object):
    _registry = []
    def __init__(self,name,pump,bitlasharduino,soil=None,reservoir=None):
        self._registry.append(self)
        self.arduino = bitlasharduino
        self.name = name
        self.pump = pump
        self.soil = soil
        self.reservoir = reservoir
        self.lastWatered = None
        self.wateredCount = 0
        self.fault = 0

    def doesplantneedwater(self):
        logging.info('checking {name} water levels'.format(name=self.name))
        if self.soil is None and self.reservoir is None:
            logging.error("{name} has no sensors set".format(name=self.name))
            print "{name} has no sensors set".format(name=self.name)
            return 0
        if self.soil is None:
            soildry = 1
        else:
            if self.soil.readADC() < soildryADC:
                soildry = 0
            else:
                soildry = 1
            logging.info("soil ADC: {adc}".format(adc = self.soil.adc))
            logging.info("soil Setpoint: {adc}".format(adc = soildryADC))
        if self.reservoir is None:
            reservoirdry = 1
        else:
            if self.reservoir.readADC() < reservoirdryADC:
                reservoirdry = 0
            else:
                reservoirdry = 1
            logging.info("reservoir ADC: {adc}".format(adc = self.reservoir.adc))
            logging.info("reservoir Setpoint: {adc}".format(adc = reservoirdryADC))
        if soildry == 1 and reservoirdry == 1:
            logging.info("plant is dry")
            return 1
        else: 
            logging.info("plant is fine")
            return 0
        
    def water(self):
        if self.fault == 0:
            if self.doesplantneedwater() == 1:
                pumpstart = datetime.datetime.now()
                self.lastWatered = pumpstart
                self.wateredCount += 1
                self.pump.on()
                print "pump on"
                logging.info("{name} pump on".format(name=self.name))
                time.sleep(pumptimemin)
                while ((datetime.datetime.now() - pumpstart) < pumptimemax):
                    print 'waiting'
                    if self.doesplantneedwater() == 0:
                        self.pump.off()
                        print "pump off"
                        logging.info("{name} pump off".format(name=self.name))
                        break
                if ((datetime.datetime.now() - pumpstart) > pumptimemax):
                    self.pump.off()
                    self.fault = 1
                    print "pump fault"
                    logging.critical("{name} pump fault".format(name=self.name))
        else:
            if self.pump.state == 1:
                self.pump.off()

class Pump(object):
    _registry = []
    def __init__(self,cmd_on,cmd_off,bitlasharduino):
        #set a last switch time to avoid the relay going off too often
        self._registry.append(self)
        self.cmd_on = cmd_on
        self.cmd_off = cmd_off
        self.state = 0
        self.arduino = bitlasharduino
    def on(self):
        self.arduino.write(self.cmd_on)
        self.state = 1
        return self.state
    def off(self):
        self.arduino.write(self.cmd_off)
        self.state = 0
        return self.state


class SensorPower(object):
    def __init__(self,cmd_on,cmd_off,bitlasharduino):
        self.arduino = bitlasharduino
        self.cmd_on = cmd_on
        self.cmd_off = cmd_off
        self.state = 0
        self.requests = 0
    def on(self):
        self.arduino.write(self.cmd_on)
        self.state = 1
        return self.state
    def off(self):
        self.arduino.write(self.cmd_off)
        self.state = 0
        return self.state

class Sensor(object):
    def __init__(self,cmd_read,bitlasharduino,sensorpower):
        self.arduino = bitlasharduino
        self.power = sensorpower
        self.cmd_read = cmd_read
        self.adc = 0
    def readADC(self):
        self.power.on()
        time.sleep(0.5)
        self.adc = int(self.arduino.read(self.cmd_read))
        self.power.off()
        return self.adc

class BitlashArduino(object):
    def __init__(self, tty):
        self.serial = tty
        self.serial.readline()
    def write(self, cmd):
        self.serial.write(cmd)
        self.serial.readline()
        return self.serial.readline()
    def read(self, cmd):
        self.serial.write(cmd)
        self.serial.readline()
        return self.serial.readline()

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

def waterAll():
    print 'checking all plants'
    for plant in PlantMon._registry:
        print 'checking {plant}'.format(plant = plant.name)
        logging.info('checking {plant}'.format(plant = plant.name))
        plant.water()

class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type',    'text/html')
        self.end_headers()
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

#setup webserver
server = HTTPServer(('0.0.0.0', 80), MyHandler)
signal.signal(signal.SIGINT, sigint_handler)
webserverThread = threading.Thread(target=server.serve_forever)
webserverThread.start()
