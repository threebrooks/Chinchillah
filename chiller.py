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
import ConfigParser

config = ConfigParser.ConfigParser()
config.sections()
config.read(sys.argv[1])
operation_type = config.get('DEFAULT', 'type')
target_temp = config.getfloat('DEFAULT', 'target_temperature')
max_driver_to_target_dist = config.getfloat('DEFAULT', 'max_driver_to_target_dist')
seconds_between_actions = config.getfloat('DEFAULT', 'seconds_between_actions')

script_dir = os.path.dirname(os.path.realpath(__file__))
 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'

def read_temp_raw(device):
    device_file = device + '/w1_slave'
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp(device):
    lines = read_temp_raw(device)
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

devices = glob.glob(base_dir+"28*")
bias_accum = {
  "/sys/bus/w1/devices/28-020f9177206d":0.45, 
  "/sys/bus/w1/devices/28-020f9177329c":0.42,
  "/sys/bus/w1/devices/28-0205924504b1":-2.24,
  "/sys/bus/w1/devices/28-0217917707d4":1.36,
}
bias_count = 1 

if (operation_type == "heat"):
  driver_name = "Heating jacket"
else:
  driver_name = "Fridge"

id2Name = {
  "6d": "Carboy bottom",
  "d4": driver_name,
  "9c": "Basement",
  "b1": "Carboy probe"
}

def name_to_id(name):
  for shortId in id2Name.keys():
    if (id2Name[shortId] is name):
      for longId in bias_accum.keys():
        shortLongId = longId[-2:]
        if shortLongId == shortId:
          return longId
  print("Couldn't find ID!")
  exit(-1)

estimate_biases = False
if estimate_biases:
    for device in devices:
        bias_accum[device] = 0.0
    bias_count = 0 

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
                temps[device] = temp 
                break

    if estimate_biases:
        avg = 0
        for device in devices:
            avg += temps[device]
        avg /= len(devices)
        for device in devices:
          bias_accum[device] += temps[device]-avg
        bias_count += 1
    plt.plot(times, [c2f(target_temp)] * len(times), "r", label="target ("+"{:.1f}".format(c2f(target_temp))+"F)")
    for device in devices:
      color = "b"
      if (id2Name[device[-2:]] == "Carboy bottom"):
        color = "k--"
      elif (id2Name[device[-2:]] == "Basement"):
        color = "k-."
      elif (id2Name[device[-2:]] == driver_name):
        color = "b-"
      elif (id2Name[device[-2:]] == "Carboy probe"):
        color = "y-"
      norm_temp = temps[device]-bias_accum[device]/bias_count
      print(device+": "+str(norm_temp))
      display_temps[device].append(c2f(norm_temp))
      plt.plot(times,display_temps[device], color, label=id2Name[device[-2:]]+" ("+"{:.1f}".format(c2f(norm_temp))+"F)")
      if estimate_biases:
          sys.stdout.write(device[-2:]+"="+"{:.2f}".format(bias_accum[device]/bias_count)+" ")

    if estimate_biases:
        print("")
        sys.stdout.flush() 
    plt.legend(loc='best')
    plt.grid()
    plt.savefig("/var/www/html/tempi.png")
    os.system(script_dir+"/upload.sh")
    carboy_temp = temps[name_to_id("Carboy probe")]-bias_accum[name_to_id("Carboy probe")]/bias_count 
    driver_temp = temps[name_to_id(driver_name)]-bias_accum[name_to_id(driver_name)]/bias_count 
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
    print("Temp diff to target:"+str(target_temp-carboy_temp)+" => Switching "+driver_name+" "+action)
    if (abs(driver_temp-target_temp) > max_driver_to_target_dist):
      print("However, preventing overshooting, swithing off")
      action = "off"
    os.system(script_dir+"/wemo.sh "+action)
    time.sleep(seconds_between_actions)
    times = times[-400:]
    for device in devices:
      display_temps[device] = display_temps[device][-400:]

