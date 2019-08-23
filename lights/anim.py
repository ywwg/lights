import sys
import threading
import time


class Animation(object):

  # Update lights every half second
  _SET_RATE = 0.5

  def __init__(self, lights, start_bulbs, end_bulbs, transition_time):
    # a Lights object for setting bulbs
    self._lights = lights

    # A dict of bulb name to RRGGBBWW
    self._start_bulbs = start_bulbs

    # A dict of bulb name to RRGGBBWW
    self._end_bulbs = end_bulbs

    self._start_time = time.time()
    self._transition_time = transition_time

    self._stop_anim = threading.Event()
    self._thread = threading.Thread(target=self._animate)
    self._thread.start()

  def stop(self):
    self._stop_anim.set()
    self._thread.join()

  def _animate(self):
    """loop through bulbs, interpolate, sleep until done or stopped
    """

    progress = 0
    while not self._stop_anim.is_set() and progress < 1.0:
      progress = self._progress()
      print ('animation progress %f' % (progress,))

      for bulb_name in self._end_bulbs:
        if bulb_name not in self._start_bulbs:
          print ('%s not in start bulb list: %s' % (bulb_name, self._start_bulbs))
          return

        src_val = self._start_bulbs[bulb_name]
        i_r, i_g, i_b, i_w = Animation._interp_vals(
            src_val, self._end_bulbs[bulb_name], progress)
        self._lights.set_rgbw_one(bulb_name, i_r, i_g, i_b, i_w)

      time.sleep(Animation._SET_RATE)

  def _progress(self):
    p = (time.time() - self._start_time) / self._transition_time
    if p < 0.0:
      p = 0.0
    if p > 1.0:
      p = 1.0
    return p

  @staticmethod
  def _interp_vals(src, dst, progress):
    s_r = int(src[0:2], 16)
    s_g = int(src[2:4], 16)
    s_b = int(src[4:6], 16)
    s_w = int(src[6:8], 16)

    d_r = int(dst[0:2], 16)
    d_g = int(dst[2:4], 16)
    d_b = int(dst[4:6], 16)
    d_w = int(dst[6:8], 16)

    i_r = s_r + (d_r - s_r) * progress
    i_g = s_g + (d_g - s_g) * progress
    i_b = s_b + (d_b - s_b) * progress
    i_w = s_w + (d_w - s_w) * progress

    return i_r, i_g, i_b, i_w


if __name__ == '__main__':
  # shitty tests

  src = "004466FF"
  dst = "FF664400"

  r,g,b,w = Animation._interp_vals(src, dst, 0.0)
  if r != 0 or g != 0x44 or b != 0x66 or w != 0xFF:
    print ('0%% fail: %d %d %d %d' % (r,g,b,w))
    sys.exit(1)

  r,g,b,w = Animation._interp_vals(src, dst, 1.0)
  if r != 0xff or g != 0x66 or b != 0x44 or w != 0x00:
    print ('100%% fail: %d %d %d %d' % (r,g,b,w))
    sys.exit(1)

  r,g,b,w = Animation._interp_vals(src, dst, 0.5)
  if r != 0x7F or g != 0x55 or b != 0x55 or w != 0x7F:
    print ('50%% fail: %d %d %d %d' % (r,g,b,w))
    sys.exit(1)

  print ('tests pass')
