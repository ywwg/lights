import sys
import threading
import time

from flux_led import WifiLedBulb, BulbScanner


class Scanner(object):

  def __init__(self, bulb_map, period, fake=False):
    self._bulb_map = bulb_map
    self._period = period
    self._fake = fake
    self._thread = None
    self._lock = threading.Lock()
    self._stop = threading.Event()
    self._scanner = BulbScanner()

    self._lights = {}

    self._thread = threading.Thread(target=self._scan)
    self._thread.start()

  def stop(self):
    self._stop.set()
    self._thread.join()

  def lights(self):
    with self._lock:
      return self._lights

  def lock(self):
    return self._lock

  def _scan(self):
    while not self._stop.is_set():
      with self._lock:
        new_lights = {}
        print('Scanning for bulbs')
        old_names = tuple(self._lights.keys())
        found_names = []
        if not self._fake:
          self._scanner.scan(timeout=4)

          for scanned in self._scanner.getBulbInfo():
            bid = scanned['id']
            if bid in self._bulb_map:
              print('Found real bulb: %s' % (self._bulb_map[bid],))
              new_lights[self._bulb_map[bid]] = {'info': scanned}
              found_names.append(self._bulb_map[bid])
        else:
          for i, id in enumerate(self._bulb_map):
            print('Found fake bulb: %s' % (self._bulb_map[id],))
            new_lights[self._bulb_map[id]] = {'info': {'ipaddr': '10.0.0.%d' % i}}
            found_names.append(self._bulb_map[id])

        # Clear out any bulbs that went missing
        for name in old_names:
          if name not in found_names:
            print('Removing missing light: ', name)
        for name in found_names:
          if name not in old_names:
            print('Adding new bulb: ', name)

        for name, l in new_lights.items():
          if not l['info']:
            print('Did not find expected bulb', name)
            sys.exit(1)
          if not self._fake:
            l['bulb'] = WifiLedBulb(l['info']['ipaddr'])
          else:
            l['bulb'] = FakeBulb(name)

        if len(new_lights) != len(self._bulb_map):
          print("Warning: didn't find all the lights")
        self._lights = new_lights

      # Sleep, but keep checking for quit while we do.
      for i in range(0, self._period):
        if self._stop.is_set():
          return
        time.sleep(1)

class FakeBulb(object):
  def __init__(self, name):
    self._name = name
    self._r = 0x00
    self._g = 0x00
    self._b = 0x00
    self._w = 0x00
    self._brightness = 0x00
    self._power = False

  def turnOn(self):
    print('%s goes on' % self._name)
    self._power = True

  def turnOff(self):
    print('%s goes off' % self._name)
    self._power = False

  @property
  def is_on(self):
    return self._power

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
