import os
import sys
import threading
import time

from flux_led import WifiLedBulb, BulbScanner, LedTimer

BULBS = {
  'A020A60EB2B6': 'couch',
  '840D8E5C69AE': 'kitchen',
}

class BulbNotFoundError(Exception):
  pass

class Lights(object):
  def __init__(self, fake=False):
    self._lights = {}
    self._timer = None
    if not fake:
      scanner = BulbScanner()
      scanner.scan(timeout=4)

      for scanned in scanner.getBulbInfo():
        bid = scanned['id']
        if bid in BULBS:
          print 'Found real bulb: %s' % (BULBS[bid],)
          self._lights[BULBS[bid]] = {'info': scanned}
    else:
      for i, id in enumerate(BULBS):
        print 'Found fake bulb: %s' % (BULBS[id],)
        self._lights[BULBS[id]] = {'info': {'ipaddr': '10.0.0.%d' % i}}

    for name, l in self._lights.iteritems():
      if not l['info']:
        print ('Did not find expected bulb', name)
        sys.exit(1)
      if not fake:
        l['bulb'] = WifiLedBulb(l['info']['ipaddr'])
      else:
        l['bulb'] = FakeBulb()

  def _bulbs(self):
    return [(name, l['bulb']) for name, l in self._lights.iteritems()]

  def list_bulbs(self):
    return [name for name in self._lights]

  def set_power(self, name, on=True):
    if name not in self._lights:
      print "bulb not found:", name
      return BulbNotFoundError
    b = self._lights[name]['bulb']
    print "setting bulb power:", name, on
    b.turnOn() if on else b.turnOff()

  def set_rgbw_all(self, r, g, b, w, brightness=None):
    for name in self._lights:
      self.set_rgbw_one(name, r, g, b, w, brightness)

  def set_rgbw_one(self, name, r, g, b, w, brightness=None):
    if name not in self._lights:
      raise BulbNotFoundError

    # The kitchen lights have r and g swapped, so flip them
    if name == 'kitchen':
      r, g = g, r

    if self._timer:
      self._timer.cancel()
    self._timer = threading.Timer(5.0, self._close)
    self._lights[name]['bulb'].setRgbw(r, g, b, w,
        brightness=brightness, retry=4)
    self._timer.start()

  def _close(self):
    for name in self._lights:
      self._lights[name]['bulb'].close()

  def refresh_state(self):
    for _, bulb in self._bulbs():
      bulb.refreshState()

class FakeBulb(object):
  def turnOn(self):
    print "light goes on"

  def turnOff(self):
    print "light goes off"

  def setRgbw(self, r, g, b, w, brightness=0, retry=2):
    print "set rgbw", r, g, b, w, brightness, retry

  def refreshState(self):
    print "refreshing state I guess"
