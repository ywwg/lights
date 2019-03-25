import BaseHTTPServer
import cgi
import json
import mimetypes
import os
import posixpath
import shutil
import SimpleHTTPServer
import threading
import time
import urllib
import urlparse
try:
    from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO

# presets:
#  name => tuple:
#   sort order, dict:
#    name of bulb => RGBW
PRESETS = {
  '100': (0, {'all': '000000FF'}),
  '50': (1, {'all': '00000088'}),
  '20': (2, {'all': '00000022'}),
  'tv med': (3, {'kitchen': '00000009',
                   'couch': '00000018'}),
  'tv low': (4, {'kitchen': '00000004',
                   'couch': '00000006'}),
  'blue': (5, {'all': '0000FF00'}),
  'purple': (6, {'all': 'FF00FF00'}),
}

FluxHandler = None
FluxHandlerLock = threading.Lock()

# Most of the code is ripped from SimpleHTTPRequestHandler
class LightsHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

  server_version = "Lights/1.0"

  def do_GET(self):
    # Usually we will serve files as requested, but if they ask for one of
    # our specially-handled paths then we call flux, etc.

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
    Add on /html for this server.
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
    path = os.path.join(os.getcwd(), 'html')
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
