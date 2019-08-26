import os
import sys
import threading
import time
import traceback

from . import anim

from flux_led import WifiLedBulb, BulbScanner, LedTimer

BULBS = {
  'A020A60EB2B6': 'couch',
  '840D8E5C69AE': 'kitchen',
}

class BulbNotFoundError(Exception):
  pass

class Lights(object):
  def __init__(self, fake=False, must_find_all=False):
    self._lights = {}
    self._close_timer = None
    self._animation = None

    if not fake:
      scanner = BulbScanner()
      scanner.scan(timeout=4)

      for scanned in scanner.getBulbInfo():
        bid = scanned['id']
        if bid in BULBS:
          print('Found real bulb: %s' % (BULBS[bid],))
          self._lights[BULBS[bid]] = {'info': scanned}
    else:
      for i, id in enumerate(BULBS):
        print('Found fake bulb: %s' % (BULBS[id],))
        self._lights[BULBS[id]] = {'info': {'ipaddr': '10.0.0.%d' % i}}

    for name, l in self._lights.items():
      if not l['info']:
        print('Did not find expected bulb', name)
        sys.exit(1)
      if not fake:
        l['bulb'] = WifiLedBulb(l['info']['ipaddr'])
      else:
        l['bulb'] = FakeBulb(name)

    if must_find_all and len(self._lights) != len(BULBS):
      print("didn't find all the lights, exiting")
      sys.exit(1)
    self._start_close_timer()

  def _bulbs(self):
    return [(name, l['bulb']) for name, l in self._lights.items()]

  def list_bulbs(self):
    return [name for name in self._lights]

  def set_power(self, name, on=True):
    if name not in self._lights:
      print("bulb not found:", name)
      return BulbNotFoundError
    b = self._lights[name]['bulb']
    print("setting bulb power:", name, on)
    b.turnOn() if on else b.turnOff()
    self._start_close_timer()

  def start_animation(self, preset, transition_time):
    if self._animation:
      self._animation.stop()

    # In the case of "all", we have to specifically enumerate the bulbs because
    # the animator doesn't know about all the bulbs.
    dst_bulbs = preset.bulbs
    if 'all' in preset.bulbs:
      dst_bulbs = {}
      # If some bulbs are named in the preset we use them, otherwise we pull
      # from the "all" entry.
      for name in BULBS.values():
        if name in preset.bulbs:
          dst_bulbs[name] = preset.bulbs[name]
        else:
          dst_bulbs[name] = preset.bulbs['all']

    self._animation = anim.Animation(self, self._get_bulbs_state(), dst_bulbs,
                                     transition_time)

  def stop_animation(self):
    if self._animation:
      self._animation.stop()
      self._animation = None

  def _get_bulbs_state(self):
    state = {}
    for name in self._lights:
      self._lights[name]['bulb'].refreshState()
      r,g,b,w = self._lights[name]['bulb'].getRgbw()
      state[name] ='0x{:08x}'.format(int(r * 16**6 + g * 16**4 + b * 16**2 + w))[2:]
    return state

  def set_rgbw_all(self, r, g, b, w, brightness=None):
    for name in self._lights:
      self.set_rgbw_one(name, r, g, b, w, brightness)

  def set_rgbw_one(self, name, r, g, b, w, brightness=None):
    if name not in self._lights:
      raise BulbNotFoundError

    # The kitchen lights have r and g swapped, so flip them
    if name == 'kitchen':
      r, g = g, r

    self._lights[name]['bulb'].setRgbw(r, g, b, w,
        brightness=brightness, retry=4)
    self._start_close_timer()

  def _start_close_timer(self):
    """Launch a timeout to close down the connections so they don't get stale.
    If called multiple times it will cancel any existing timer and start a new
    one.
    """
    if self._close_timer:
      self._close_timer.cancel()
    self._close_timer = threading.Timer(5.0, self._close)
    self._close_timer.start()

  def _close(self):
    for name in self._lights:
      self._lights[name]['bulb'].close()

  def refresh_state(self):
    for _, bulb in self._bulbs():
      bulb.refreshState()

class FakeBulb(object):
  def __init__(self, name):
    self._name = name
    self._r = 0x00
    self._g = 0x00
    self._b = 0x00
    self._w = 0x00
    self._brightness = 0x00

  def turnOn(self):
    print('%s goes on' % self._name)

  def turnOff(self):
    print('%s goes off' % self._name)

  def getRgbw(self):
    return (self._r, self._g, self._b, self._w)

  def setRgbw(self, r, g, b, w, brightness=0, retry=2):
    print('%s: set rgbw' % self._name, r, g, b, w, brightness, retry)
    self._r = r
    self._g = g
    self._b = b
    self._w = w
    self._brightness = brightness

  def refreshState(self):
    print('%s: refreshing state I guess' % self._name)

  def close(self):
    print('%s: closing connection' % self._name)
