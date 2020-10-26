import time
import os
import RPi.GPIO as GPIO
from multiprocessing import Process, Manager

class BubbleDetector:
  def __init__(self, pin):
    self.pin = pin
    GPIO.setup(self.pin, GPIO.IN, GPIO.PUD_DOWN)

    self.smoothed_gpio = 0
    self.gpio_smooth_fac = 0.99
    self.prev_smoothed_gpio_state = 1
    self.bpm_smooth_fac = 0.99
    self.manager = Manager()
    self.smoothed_bpm = self.manager.Value('smoothed_bpm',0.0)
    self.last_bubble_time = -1

  def process_loop(self):
    while(True):
      val = GPIO.input(self.pin)
      self.smoothed_gpio = self.smoothed_gpio*self.gpio_smooth_fac+(1.0-self.gpio_smooth_fac)*val
      new_smoothed_gpio_state = self.prev_smoothed_gpio_state
      if (self.smoothed_gpio > 0.75):
        new_smoothed_gpio_state = 1
      elif (self.smoothed_gpio < 0.25):
        new_smoothed_gpio_state = 0
  
      if (new_smoothed_gpio_state == 0 and self.prev_smoothed_gpio_state == 1):
        new_bubble = True
      else:
        new_bubble = False
      self.prev_smoothed_gpio_state = new_smoothed_gpio_state
  
      if (new_bubble):
        print("Bubble!")
        if (self.last_bubble_time > 0):
          time_since_last_bubble = time.time()-self.last_bubble_time
          self.smoothed_bpm.value = self.smoothed_bpm.value*self.bpm_smooth_fac+(1.0-self.bpm_smooth_fac)*(60.0/time_since_last_bubble)
        self.last_bubble_time = time.time()
      time.sleep(0.01)

  def start(self):
    self.p = Process(target=self.process_loop)
    self.p.start()
     
  def get_bpm(self):   
    return self.smoothed_bpm.value

