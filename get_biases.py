import os
import sys
import glob
import time
import datetime
from cycler import cycler
 
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

devices = glob.glob(base_dir+"28*")
bias_accum = {}
for device in devices:
    bias_accum[device] = 0.0
bias_count = 0 
while True:
    temps = {}
    for device in devices:
        while True:
            temp = read_temp(device)
            if (temp != None): 
                temps[device] = temp
                break

    avg = 0
    for device in devices:
        avg += temps[device]
    avg /= len(devices)
    bias_count += 1
    for device in devices:
      bias_accum[device] += temps[device]-avg
      sys.stdout.write(device[-2:]+"="+"{:.2f}".format(bias_accum[device]/bias_count)+" ")
    
    print("")
    sys.stdout.flush()
    time.sleep(60)

