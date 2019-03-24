#!/usr/bin/python2.7
import BaseHTTPServer
import cgi
import json
import mimetypes
import os
import posixpath
import shutil
import SimpleHTTPServer
import SocketServer
import sys
import threading
import time
import urllib
import urlparse
try:
    from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO

from flux_led import WifiLedBulb, BulbScanner, LedTimer


# STATUS:
# OK, the basics are coming together.  Even if we just have presets and on/off,
# that's a good start.
#
# The big next thing is getting the color wheel selector working, and adding
# a slider for the custom colors.
#
# After that, creating presets would be nice but maybe it's just easier to
# edit the file, y'know.

class BulbNotFoundError(Exception):
  pass

BULBS = {
  'A020A60EB2B6': 'couch',
  '840D8E5C69AE': 'kitchen',
}

# presets:
#  name => tuple:
#   sort order, dict:
#    name of bulb => RGBW
PRESETS = {
  '100': (0, {'all': '000000FF'}),
  '50': (1, {'all': '00000088'}),
  '20': (2, {'all': '00000022'}),
  'tv med': (3, {'kitchen': '00000066',
             'couch': '00000044'}),
  'tv low': (4, {'kitchen': '00000011',
             'couch': '00000022'}),
  'blue': (5, {'all': '0000FF00'}),
  'purple': (6, {'all': 'FF00FF00'}),
}

class Lights(object):
  def __init__(self, fake=False):
    self._lights = {}
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

    self._lights[name]['bulb'].setRgbw(r, g, b, w,
        brightness=brightness, retry=3)

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


# Most of the code is ripped from SimpleHTTPRequestHandler
class LightsHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

  server_version = "Lights/1.0"

  def do_GET(self):
    # usually we will serve files as requested, but if they ask for one of
    # our specially-handled paths then we call flux, etc.

    print "requested path:", self.path

    req = self.path.split('?',1)[0]
    req = req.split('#',1)[0]
    req = posixpath.normpath(urllib.unquote(req))
    req = req.split('/')[-1]

    # Our custom handlers
    if req == 'list_lights':
      return self.ListLights()
    elif req == 'list_presets':
      return self.ListPresets()
    elif req == 'activate_preset':
      return self.ActivatePreset(self.path)
    elif req == 'set_lights':
      return self.SetLights(self.path)

    f = self._send_head()
    if f:
      shutil.copyfileobj(f, self.wfile)
      f.close()

  def ListLights(self):
    with FluxHandlerLock:
      lights = FluxHandler.list_bulbs()
    self._send_as_json(lights)

  def ListPresets(self):
    preset_names = sorted(PRESETS.keys(), key=lambda x: PRESETS[x][0])
    self._send_as_json(preset_names)

  def ActivatePreset(self, path):
    url = urlparse.urlparse(path)
    query = urlparse.parse_qs(url.query)
    print "query:", query
    if 'name' not in query:
      return self._send_as_json(False)

    with FluxHandlerLock:
      preset = PRESETS[query['name'][0]][1]
      # The preset is dict
      for bulb, val in preset.iteritems():
        r = int(val[0:2], 16)
        g = int(val[2:4], 16)
        b = int(val[4:6], 16)
        w = int(val[6:8], 16)
        if bulb == 'all':
          FluxHandler.set_rgbw_all(r, g, b, w)
        else:
          FluxHandler.set_rgbw_one(bulb, r, g, b, w)
    return self._send_as_json(True)

  def SetLights(self, path):
    # path format: /set_lights?bulb=[name]&power=[on/off]&rgbw=AABBCCDD
    url = urlparse.urlparse(path)
    query = urlparse.parse_qs(url.query)
    # TODO: like, at least a *little* input validation
    print 'query:', query
    with FluxHandlerLock:
      bulbs = []
      if query['bulb'][0] == 'all':
        bulbs = FluxHandler.list_bulbs()
      else:
        bulbs = [b.strip() for b in query['bulb'][0].split(',')]
      for bulb in bulbs:
        if 'power' in query:
          FluxHandler.set_power(bulb, True if query['power'][0] == 'on' else False)
        if 'rgbw' in query:
          r = int(query['rgbw'][0][0:2], 16)
          g = int(query['rgbw'][0][2:4], 16)
          b = int(query['rgbw'][0][4:6], 16)
          w = int(query['rgbw'][0][6:8], 16)
          FluxHandler.set_rgbw_one(bulb, r, g, b, w)
    self._send_as_json(True)

  def do_HEAD(self):
    f = self._send_head()
    if f:
      f.close()

  def _send_as_json(self, pyob):
    """Encodes the passed-in python object as json and writes it out."""
    jsonob = json.dumps(pyob)
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.send_header("Content-Length", len(jsonob))
    # self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
    self.end_headers()
    self.wfile.write(jsonob)

  def _send_head(self):
    path = self._translate_path(self.path)
    f = None
    if os.path.isdir(path):
      if not self.path.endswith('/'):
        # redirect browser - doing basically what apache does
        self.send_response(301)
        self.send_header("Location", self.path + "/")
        self.end_headers()
        return None
      for index in "index.html", "index.htm":
        index = os.path.join(path, index)
        if os.path.exists(index):
          path = index
          break
      else:
        # don't bother handling directory requests
        return None
    ctype = self._guess_type(path)
    try:
      # Always read in binary mode. Opening files in text mode may cause
      # newline translations, making the actual size of the content
      # transmitted *less* than the content-length!
      f = open(path, 'rb')
    except IOError:
      self.send_error(404, "File not found")
      return None
    self.send_response(200)
    self.send_header("Content-type", ctype)
    fs = os.fstat(f.fileno())
    self.send_header("Content-Length", str(fs[6]))
    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
    self.end_headers()
    return f

  def _translate_path(self, path):
    """Translate a /-separated PATH to the local filename syntax.
    Add on /templates for this server.
    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)
    """
    # abandon query parameters
    path = path.split('?',1)[0]
    path = path.split('#',1)[0]
    path = posixpath.normpath(urllib.unquote(path))
    words = path.split('/')
    words = filter(None, words)

    # XXXXXX custom hack here:
    path = os.path.join(os.getcwd(), 'templates')
    for word in words:
      drive, word = os.path.splitdrive(word)
      head, word = os.path.split(word)
      if word in (os.curdir, os.pardir): continue
      path = os.path.join(path, word)
    return path

  def _guess_type(self, path):
    base, ext = posixpath.splitext(path)
    if ext in self.extensions_map:
      return self.extensions_map[ext]
    ext = ext.lower()
    if ext in self.extensions_map:
      return self.extensions_map[ext]
    else:
      return self.extensions_map['']

  if not mimetypes.inited:
    mimetypes.init() # try to read system mime.types
  extensions_map = mimetypes.types_map.copy()
  extensions_map.update({
    '': 'application/octet-stream', # Default
    '.py': 'text/plain',
    '.c': 'text/plain',
    '.h': 'text/plain',
  })

FluxHandler = None
FluxHandlerLock = threading.Lock()

if __name__ == '__main__':
  # lights = Lights()
  # lights.set_power(True)
  # lights.set_rgbw_all(0xff, 0x00, 0xff, 0x00)
  # lights.refresh_state()
  # time.sleep(1)
  # lights.set_power(False)
  # time.sleep(1)

  port = int(sys.argv[1])
  fake = False
  if len(sys.argv) > 2:
    if sys.argv[2] == 'fake':
      fake = True

  FluxHandler = Lights(fake=fake)
  handler = LightsHTTPRequestHandler
  httpd = SocketServer.TCPServer(("", port), handler)
  print "serving at port", port
  httpd.serve_forever()
