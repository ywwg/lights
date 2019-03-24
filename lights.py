#!/usr/bin/python2.7
from  BaseHTTPServer import BaseHTTPRequestHandler
import SimpleHTTPServer
import SocketServer
import sys

from flux_led import WifiLedBulb, BulbScanner, LedTimer

PORT = 8000

# We need a wrapper class for the kitchen lights where R and G are swapped
# We need some sort of html/css for the main display, should do a mockup first.
# Maybe the initial design is on/off, and white brightness

# the get handler will need to take in params and then make calls to flux as
# needed

class Flux(object):
  def __init__(self):
    scanner = BulbScanner()
    scanner.scan(timeout=4)

    self._lights = {}
    self._lights['couch'] = {'info': scanner.getBulbInfoByID('A020A60EB2B6')}
    self._lights['kitchen'] = {'info': scanner.getBulbInfoByID('840D8E5C69AE')}

    for name, l in self._lights.iteritems():
      if not l['info']:
        print ('Did not find expected bulb', name)
        sys.exit(1)
      print 'Found bulb: ', name
      l['bulb'] = WifiLedBulb(l['info']['ipaddr'])

  def _bulbs(self):
    return [(name, l['bulb']) for name, l in self._lights.iteritems()]

  def list_bulbs(self):
    return [name for name in self._lights]

  def set_power(self, on=True):
    """If true, turn on. If false, turn off"""
    for _, b in self._bulbs():
      b.turnOn() if on else b.turnOff()

  def set_all(self, r, g, b, w, brightness=None):
    for name, bulb in self._bulbs():
      # The kitchen lights have r and g swapped, so flip them
      set_r, set_g = r, g
      if name == 'kitchen':
        set_r, set_g = g, r
      bulb.setRgbw(set_r, set_g, b, w, brightness=brightness)

  def refresh_state(self):
    for _, bulb in self._bulbs():
      bulb.refreshState()


# class LightsHTTPRequestHandler(BaseHTTPRequestHandler):
  
#   def __init__(self, flux):
#     """flux is the handler that can be called to set brightnesses"""
#     self._flux = flux
#     # self._lights = an array of the available detected bulbs (get from flux)
  
#   def do_GET(self):
#     # 
#     self.send_response(200)
#     self.end_headers()
#     self.wfile.write(b'Hello, world!')

if __name__ == '__main__':
  flux = Flux()
  # flux.set_power(True)
  # flux.set_all(0x00, 0x00, 0x00, 0xff)
  # flux.set_power(False)
  # handler = LightsHTTPRequestHandler
  # httpd = SocketServer.TCPServer(("", PORT), handler)
  # print "serving at port", PORT
  # httpd.serve_forever()