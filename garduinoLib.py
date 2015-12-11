import traceback
import serial
#import RPi.GPIO as GPIO
import datetime
import time
import threading
import signal
import logging

logging.basicConfig(level=logging.INFO, 
                    filename='garden.log', # log to this file
                    format='%(asctime)s %(message)s') # include timestamp

tty_lock = threading.Lock()

#constants
soildryADC = 400
reservoirdryADC = 750
pumptimemax = datetime.timedelta(seconds = 10)
pumptimemin = 2

class PlantMon(threading.Thread):
#class PlantMon(object):
    _registry = []
    def __init__(self,name,pump,bitlasharduino,soil=None,reservoir=None):
        self._registry.append(self)
        threading.Thread.__init__(self)
        self._stop = threading.Event()
        self.arduino = bitlasharduino
        self.name = name
        self.pump = pump
        self.soil = soil
        self.reservoir = reservoir
        self.fault = 0
    def doesplantneedwater(self):
        logging.info('checking {name} water levels'.format(name=self.name))
        if self.soil is None and self.reservoir is None:
            logging.error("{name} has no sensors set".format(name=self.name))
            #print "{name} has no sensors set".format(name=self.name)
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
                self.pump.on()
                #print "pump on"
                logging.info("{name} pump on".format(name=self.name))
                time.sleep(pumptimemin)
                while ((datetime.datetime.now() - pumpstart) < pumptimemax):
                    #print 'waiting'
                    if self.doesplantneedwater() == 0:
                        self.pump.off()
                        #print "pump off"
                        logging.info("{name} pump off".format(name=self.name))
                        break
                if ((datetime.datetime.now() - pumpstart) > pumptimemax):
                    self.pump.off()
                    self.fault = 1
                    #print "pump fault"
                    logging.critical("{name} pump fault".format(name=self.name))
        else:
            if self.pump.state == 1:
                self.pump.off()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        while not self.stopped():
            self.water()
            time.sleep(5)


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
        self.requests += 1
        if self.state == 0 and self.requests > 0:
            self.arduino.write(self.cmd_on)
            self.state == 1
        return self.state
    def off(self):
        self.requests -= 1
        if self.state == 1 and self.requests == 0:
            self.arduino.write(self.cmd_off)
            self.state == 0
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
        with tty_lock:
            self.serial.readline()
    def write(self, cmd):
        with tty_lock:
            self.serial.write(cmd)
            self.serial.readline()
            return self.serial.readline()
    def read(self, cmd):
        with tty_lock:
            self.serial.write(cmd)
            self.serial.readline()
            return self.serial.readline()

def sigint_handler(signum,frame):
    shutdown()

def shutdown():
    print 'closing plant monitor threads'
    try:
        for plant in PlantMon._registry:
            plant.stop()
        for plant in PlantMon._registry:
            plant.join()
    except:
        print 'failed to join threads'
    print 'shutting down all pumps'
    for pump in Pump._registry:
        pump.off()
    for plant in PlantMon._registry:
        print 'shutting down {plant} pump'.format(plant = plant.name)
        plant.pump.off()
    exit()

signal.signal(signal.SIGINT, sigint_handler)
