import traceback
import serial
import datetime
import time
import logging
import csv
import sys
import os
import RPi.GPIO as GPIO


logLocation = '/home/pi/garden/log/garden.log'
dataLocation = '/home/pi/garden/data/'

logging.basicConfig(level=logging.INFO, 
                    filename=logLocation, # log to this file
                    format='%(asctime)s %(message)s'
                    ) # include timestamp

#constants
soildryADC = 385
reservoirdryADC = 750
pumptimemax = datetime.timedelta(seconds = 30)
pumptimemin = 10
inittime = datetime.datetime.now()

class Log(object):
    def __init__(self,name):
        self.name = name
        self.filepath = str(dataLocation) + str(self.name) + '.csv'
        self.log = []
        self.readLogFile()
    def getLog(self):
        return self.log
    def readLogFile(self):
        if os.path.isfile(self.filepath):
            csvFile = open(self.filepath, 'rt')
            reader = csv.reader(csvFile)
            self.log = list(reader)
            csvFile.close()
            return True
        else:
            self.log = []
            return False
    def addLog(self,data):
        if not os.path.exists(dataLocation):
            os.makedirs(dataLocation)
        row = [str(i) for i in data]
        csvFile = open(self.filepath, 'a')
        writer = csv.writer(csvFile)
        writer.writerow(row)
        csvFile.close()
        return True

class localSensor(object):
    def __init__(self,sensorGPIO,powerGPIO):
        self.sensorGPIO = sensorGPIO
        self.powerGPIO = powerGPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.powerGPIO, GPIO.OUT)
        GPIO.setup(self.sensorGPIO, GPIO.IN)
        self.sense = self.read()
    def read(self):
        GPIO.output(self.powerGPIO, True)
        time.sleep(0.5)
        self.sense = GPIO.input(self.sensorGPIO)
        GPIO.output(self.powerGPIO, False)
        return self.sense
        
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
        self.waterLog = Log(self.name+'_water')
        self.soilLog = Log(self.name+'_soil')
        self.reservoirLog = Log(self.name+'_reservoir')

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
            self.soilLog.addLog([datetime.datetime.now(), self.soil.adc])
        if self.reservoir is None:
            reservoirdry = 1
        else:
            if self.reservoir.readADC() < reservoirdryADC:
                reservoirdry = 0
            else:
                reservoirdry = 1
            logging.info("reservoir ADC: {adc}".format(adc = self.reservoir.adc))
            logging.info("reservoir Setpoint: {adc}".format(adc = reservoirdryADC))
            self.reservoirLog.addLog([datetime.datetime.now(), self.reservoir.adc])
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
                self.waterLog.addLog([pumpstart,(datetime.datetime.now() - pumpstart)])
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
        l = [int(self.arduino.read(self.cmd_read)) for _ in range(20)]
        self.adc = reduce(lambda x, y: x + y, l) / len(l)
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

def waterAll():
    print 'checking all plants'
    for plant in PlantMon._registry:
        print 'checking {plant}'.format(plant = plant.name)
        logging.info('checking {plant}'.format(plant = plant.name))
        plant.water()

