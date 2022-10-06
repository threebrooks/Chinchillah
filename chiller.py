import os
import sys
import glob
import time
import datetime
from datetime import date
import matplotlib
from cycler import cycler
matplotlib.use('Agg')
#matplotlib.use('GTKAgg');
import matplotlib.pyplot as plt
import numpy as np
import configparser
import RPi.GPIO as GPIO
import BubbleDetector
from kasa import SmartPlug,Discover
import asyncio

config = configparser.ConfigParser()
config.sections()
config.read("chiller.ini")
operation_type = config.get('DEFAULT', 'type')
target_temp = config.getfloat('DEFAULT', 'target_temperature')
max_driver_to_target_dist = config.getfloat('DEFAULT', 'max_driver_to_target_dist')
seconds_between_actions = config.getfloat('DEFAULT', 'seconds_between_actions')

def GetKasaAddress(name):
  devices = asyncio.run(Discover.discover())
  for addr, dev in devices.items():
      if (dev.alias == name):
        return addr
      asyncio.run(dev.update())
  raise RuntimeError("Can't find "+name)

fridge_switch = SmartPlug(GetKasaAddress("Chiller"))

async def Fridge(onoff):
  try:
    await fridge_switch.update()
    if (onoff):
      await fridge_switch.turn_on()
    else:
      await fridge_switch.turn_off()
  except Exception as e:
    print(e)
    pass

def get_device_bias(device_name):
    if (not config.has_option("DEFAULT", device_name)):
       raise RuntimeError("ini file does not contain bias for device "+device_name)
    els = config.get("DEFAULT", device_name).split(",")
    return float(els[1])

def get_nice_name(device_name):
    if (not config.has_option("DEFAULT", device_name)):
       raise RuntimeError("ini file does not contain name for device "+device_name)
    els = config.get("DEFAULT", device_name).split(",")
    return els[0]

def get_device_name(nice_name):
    for (key, val) in config.items("DEFAULT"):
        if ("28-" not in key):
            continue
        els = val.split(",")
        if (els[0] == nice_name):
          return key
    print("Couldn't find device ID for "+nice_name+"!")
    sys.exit(-1)

script_dir = os.path.dirname(os.path.realpath(__file__))
 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
device_dir = '/sys/bus/w1/devices/'

def read_temp_raw(device):
    device_file = device + '/w1_slave'
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp(device):
    lines = read_temp_raw(device_dir+"/"+device)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw(device)
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def c2f(t):
    return 1.8*t+32

devices = glob.glob(device_dir+"28*")
devices = [sub.replace(device_dir,"") for sub in devices]

GPIO.setmode(GPIO.BCM)
bubble_detector = BubbleDetector.BubbleDetector(21)
bubble_detector.start()

async def main():
  times = []
  display_temps = {}
  display_bpm = []
  for device in devices:
      display_temps[device] = []
  
  while True:
      try:
          print("#### "+str(datetime.datetime.now())+" ####")
          times.append(datetime.datetime.fromtimestamp(time.time()))
          plt.clf()
          plt.gcf().autofmt_xdate()
      
          fig, ax1 = plt.subplots()
          ax2 = ax1.twinx()
          temps = {}
          for device in devices:
              while True:
                  temp = read_temp(device)
                  if (temp != None): 
                      temps[device.replace(device_dir,"")] = temp 
                      break
      
          lines = []
          lines.extend(ax1.plot(times, [c2f(target_temp)] * len(times), "r", label="target ("+"{:.1f}".format(c2f(target_temp))+"F)"))
          for device in devices:
            norm_temp = temps[device]-get_device_bias(device)
            print("  "+get_nice_name(device)+": "+str(norm_temp))
            display_temps[device].append(c2f(norm_temp))
            lines.extend(ax1.plot(times,display_temps[device], label=get_nice_name(device)+" ("+"{:.1f}".format(c2f(norm_temp))+"F)"))
      
          display_bpm.append(bubble_detector.get_bpm())
          lines.extend(ax2.plot(times,display_bpm, 'k--',label="Bubble per minute"))
      
          labels = [l.get_label() for l in lines]
          ax1.legend(lines, labels, loc='best')
          plt.title(datetime.datetime.now())
          plt.grid()
          plt.savefig("/var/www/html/tempi.png")
          plt.close()
          #os.system(script_dir+"/upload.sh")
          carboy_temp = temps[get_device_name("core_temp")]-get_device_bias(get_device_name("core_temp"))
          driver_temp = temps[get_device_name("driver_temp")]-get_device_bias(get_device_name("driver_temp"))
          action = False
          if (carboy_temp > target_temp):
            if (operation_type == "cool"):
              action = True
            else:
              action = False
          else:
            if (operation_type == "cool"):
              action = False
            else:
              action = True
          print("  Temp diff to target:"+str(target_temp-carboy_temp)+" => Switching driver "+str(action))
          if (
              (operation_type == "cool" and ((target_temp-driver_temp) > max_driver_to_target_dist)) or
              (operation_type == "heat" and ((driver_temp-target_temp) > max_driver_to_target_dist))):
            print("  However, preventing overshooting, swithing off")
            action = False
          await Fridge(action)
          time.sleep(seconds_between_actions)
          times = times[-400:]
          display_bpm = display_bpm[-400:]
          for device in devices:
            display_temps[device] = display_temps[device][-400:]
          sys.stdout.flush()
          sys.stderr.flush()
      except Exception as e:
          print(e)
          time.sleep(1)
          
asyncio.run(main())
 
