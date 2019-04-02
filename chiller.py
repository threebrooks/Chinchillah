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

script_dir = os.path.dirname(os.path.realpath(__file__))
 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'

target_temp = 11.1
 
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
  "/sys/bus/w1/devices/28-020f9177206d":-0.02,
  "/sys/bus/w1/devices/28-020f9177329c":0.19,
  "/sys/bus/w1/devices/28-0205924504b1":-0.72,
  "/sys/bus/w1/devices/28-0217917707d4":0.55
}
bias_count = 1 

id2Name = {
  "6d": "Carboy bottom",
  "9c": "Basement",
  "d4": "Fridge",
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
      elif (id2Name[device[-2:]] == "Fridge"):
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
    fridge_temp = temps[name_to_id("Fridge")]-bias_accum[name_to_id("Fridge")]/bias_count 
    if ((carboy_temp > target_temp) and (fridge_temp > (target_temp-0.0)/2.0)):
      print("Switching fridge on")
      os.system(script_dir+"/wemo.sh on")
    elif (carboy_temp < target_temp):
      print("Switching fridge off")
      os.system(script_dir+"/wemo.sh off")
    time.sleep(5*60)
    times = times[-400:]
    for device in devices:
      display_temps[device] = display_temps[device][-400:]

