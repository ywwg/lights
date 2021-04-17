import threading

from . import anim, scanner

class BulbNotFoundError(Exception):
  pass

class Lights(object):

  SCAN_PERIOD_SECS = 60 * 5

  def __init__(self, bulbs, fake=False):
    self._close_timer = None
    self._animation = None
    self._scanner = scanner.Scanner(bulbs, self.SCAN_PERIOD_SECS, fake)

    self._start_close_timer()

  def stop(self):
    self._scanner.stop()

  def _bulbs(self):
    lights = self._scanner.lights()
    return [(name, l['bulb']) for name, l in lights.items()]

  def list_bulbs(self):
    lights = self._scanner.lights()
    return sorted([name for name in lights])

  def set_power(self, name, on=True):
    lights = self._scanner.lights()
    if name not in lights:
      print("bulb not found:", name)
      return BulbNotFoundError
    b = lights[name]['bulb']
    print("setting bulb power:", name, on)
    b.turnOn() if on else b.turnOff()
    self._start_close_timer()

  def get_power(self, name):
    lights = self._scanner.lights()
    if name not in lights:
      print("bulb not found:", name)
      return BulbNotFoundError
    b = lights[name]['bulb']
    return b.is_on

  def start_animation(self, preset, transition_time):
    lights = self._scanner.lights()
    if self._animation:
      self._animation.stop()

    # In the case of "all", we have to specifically enumerate the bulbs because
    # the animator doesn't know about all the bulbs.
    dst_bulbs = preset.bulbs
    if 'all' in preset.bulbs:
      dst_bulbs = {}
      # If some bulbs are named in the preset we use them, otherwise we pull
      # from the "all" entry.
      for name in lights.keys():
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

  def get_animation_progress(self):
    """Returns an int between 0 and 100 if there's an animation happening,
    or -1 if no anim"""
    if self._animation is None:
      return -1
    if not self._animation.running():
      self._animation = None
      return -1
    return int(self._animation.progress() * 100.0)

  def _get_bulbs_state(self):
    lights = self._scanner.lights()
    state = {}
    for name in lights:
      lights[name]['bulb'].refreshState()
      r,g,b,w = lights[name]['bulb'].getRgbw()
      r = r and r or 0
      g = g and g or 0
      b = b and b or 0
      w = w and w or 0
      if lights[name]['bulb'].is_on:
        state[name] = '0x{:08x}'.format(int(r * 16**6 + g * 16**4 + b * 16**2 + w))[2:]
      else:
        state[name] = '00000000'
    return state

  def set_rgbw_all(self, r, g, b, w, brightness=None):
    lights = self._scanner.lights()
    for name in lights:
      self.set_rgbw_one(name, r, g, b, w, brightness)

  def set_rgbw_one(self, name, r, g, b, w, brightness=None):
    lights = self._scanner.lights()
    if name not in lights:
      raise BulbNotFoundError

    # The led strip has r and g swapped, so flip them
    if name == 'led strip':
      r, g = g, r

    if r + g + b + w == 0:
      lights[name]['bulb'].turnOff()
      self._start_close_timer()
      return

    if not lights[name]['bulb'].is_on:
      lights[name]['bulb'].turnOn(retry=4)

    # Don't set white if there's any color, and vice versa
    # (Newer bulbs support do support this)
    if r+g+b > 0:
      w = None
    elif w > 0:
      r = g = b = None

    lights[name]['bulb'].setRgbw(r, g, b, w,
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
    lights = self._scanner.lights()
    for name in lights:
      lights[name]['bulb'].close()

  def refresh_state(self):
    for _, bulb in self._bulbs():
      bulb.refreshState()
