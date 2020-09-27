import os
import sys
import glob
import time
import datetime
import matplotlib
from cycler import cycler
matplotlib.use('Agg')
#matplotlib.use('GTKAgg');
import matplotlib.pyplot as plt
import numpy as np
import configparser

config = configparser.ConfigParser()
config.sections()
config.read("chiller.ini")
operation_type = config.get('DEFAULT', 'type')
target_temp = config.getfloat('DEFAULT', 'target_temperature')
max_driver_to_target_dist = config.getfloat('DEFAULT', 'max_driver_to_target_dist')
seconds_between_actions = config.getfloat('DEFAULT', 'seconds_between_actions')

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

times = []
display_temps = {}
for device in devices:
    display_temps[device] = []
while True:
    times.append(datetime.datetime.fromtimestamp(time.time()))
    plt.clf()
    plt.gcf().autofmt_xdate()
    temps = {}
    for device in devices:
        while True:
            temp = read_temp(device)
            if (temp != None): 
                temps[device.replace(device_dir,"")] = temp 
                break

    plt.plot(times, [c2f(target_temp)] * len(times), "r", label="target ("+"{:.1f}".format(c2f(target_temp))+"F)")
    for device in devices:
      norm_temp = temps[device]-get_device_bias(device)
      print(device+": "+str(norm_temp))
      display_temps[device].append(c2f(norm_temp))
      plt.plot(times,display_temps[device], label=get_nice_name(device)+" ("+"{:.1f}".format(c2f(norm_temp))+"F)")

    plt.legend(loc='best')
    plt.grid()
    plt.savefig("/var/www/html/tempi.png")
    #os.system(script_dir+"/upload.sh")
    carboy_temp = temps[get_device_name("core_temp")]-get_device_bias(get_device_name("core_temp"))
    driver_temp = temps[get_device_name("driver_temp")]-get_device_bias(get_device_name("driver_temp"))
    action = "off"
    if (carboy_temp > target_temp):
      if (operation_type == "cool"):
        action = "on"
      else:
        action = "off"
    else:
      if (operation_type == "cool"):
        action = "off"
      else:
        action = "on"
    print("Temp diff to target:"+str(target_temp-carboy_temp)+" => Switching driver "+action)
    if (abs(driver_temp-target_temp) > max_driver_to_target_dist):
      print("However, preventing overshooting, swithing off")
      action = "off"
    os.system(script_dir+"/wemo.sh "+action)
    time.sleep(seconds_between_actions)
    times = times[-400:]
    for device in devices:
      display_temps[device] = display_temps[device][-400:]

