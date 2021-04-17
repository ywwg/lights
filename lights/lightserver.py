import http.server
import json
import mimetypes
import os
import posixpath
import shutil
import threading
import urllib.request, urllib.parse, urllib.error

from collections import namedtuple

Preset = namedtuple('Preset', ['sort_order', 'bulbs'])

FluxHandler = None
FluxHandlerLock = threading.Lock()

# Most of the code is ripped from SimpleHTTPRequestHandler
class LightsHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

  server_version = "Lights/1.0"

  def __init__(self, groups, presets, *args, **kwargs):
    self._groups = groups
    self._presets = presets
    super().__init__(*args, **kwargs)

  def do_GET(self):
    # Usually we will serve files as requested, but if they ask for one of
    # our specially-handled paths then we call flux, etc.

    print ("Get Received: ", self.path)

    req = self.path.split('?',1)[0]
    req = req.split('#',1)[0]
    req = posixpath.normpath(urllib.parse.unquote(req))
    req = req.split('/')[-1]

    # Our custom handlers
    if req == 'list_lights':
      return self.ListLights()
    if req == 'list_groups':
      return self.ListGroups()
    elif req == 'list_presets':
      return self.ListPresets()
    elif req == 'activate_preset':
      return self.ActivatePreset(self.path)
    elif req == 'set_lights':
      return self.SetLights(self.path)
    elif req == 'anim_progress':
      return self.GetAnimProgress()

    f = self._send_head()
    if f:
      shutil.copyfileobj(f, self.wfile)
      f.close()

  def ListGroups(self):
    with FluxHandlerLock:
      lights = sorted(list(self._groups.keys()))
    self._send_as_json(lights)

  def ListLights(self):
    with FluxHandlerLock:
      lights = FluxHandler.list_bulbs()
    self._send_as_json(lights)

  def ListPresets(self):
    preset_names = sorted(list(self._presets.keys()), key=lambda x: self._presets[x].sort_order)
    self._send_as_json(preset_names)

  def ActivatePreset(self, path):
    url = urllib.parse.urlparse(path)
    query = urllib.parse.parse_qs(url.query)
    if 'name' not in query:
      return self._send_as_json(False)

    with FluxHandlerLock:
      preset = None
      try:
        preset = self._presets[query['name'][0]]
      except Exception as e:
        print ('Error getting preset by name: ', e)
        return self._send_as_json(True)
      transition_time = 0
      try:
        transition_time = int(query['transition_time'][0])
      except Exception as e:
        print ('error getting transition_time, defaulting to 0:', e)
      if transition_time > 0:
        FluxHandler.start_animation(preset, transition_time)
        return self._send_as_json(True)
      FluxHandler.stop_animation()
      preset = preset.bulbs
      for bulb, val in preset.items():
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
    # path format: /set_lights?bulb=[name,name2]&power=[on/off]&rgbw=AABBCCDD
    FluxHandler.stop_animation()
    url = urllib.parse.urlparse(path)
    query = urllib.parse.parse_qs(url.query)
    with FluxHandlerLock:
      bulbs = []
      if query['bulb'][0] == 'all':
        bulbs = FluxHandler.list_bulbs()
      elif query['bulb'][0] in self._groups:
        bulbs = self._groups[query['bulb'][0]]
      else:
        bulbs = [b.strip() for b in query['bulb'][0].split(',')]
      for bulb in bulbs:
        if bulb not in FluxHandler.list_bulbs():
          print("unknown bulb (is it off?):", bulb)
          continue
        if 'power' in query:
          val = query['power'][0]
          if val == 'on':
            FluxHandler.set_power(bulb, True)
          elif val == 'off':
            FluxHandler.set_power(bulb, False)
          else:
            print("invalid power setting:", val)
        if 'rgbw' in query:
          val = query['rgbw'][0]
          if len(val) != 8:
            print("invalid rgbw val (must be 8 hex digits)")
            continue
          try:
            r = int(val[0:2], 16)
            g = int(val[2:4], 16)
            b = int(val[4:6], 16)
            w = int(val[6:8], 16)
            FluxHandler.set_rgbw_one(bulb, r, g, b, w)
          except ValueError:
            print("ValueError parsing rgbw hex:", val)
    self._send_as_json(True)

  def GetAnimProgress(self):
    self._send_as_json(FluxHandler.get_animation_progress())

  def do_HEAD(self):
    """Returns header information if the user is requesting a valid file.
    Otherwise, does nothing. For json calls, we will send the headers as part
    of the do_GET call instead. This seems to work ok."""
    f = self._send_head()
    if f:
      f.close()

  def _send_as_json(self, pyob):
    """Encodes the passed-in python object as json and writes it out.
    Also sends headers."""
    jsonob = json.dumps(pyob)
    self.send_response(200)
    self.send_header("Content-type", "application/json")
    self.send_header("Content-Length", len(jsonob))
    # self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
    self.end_headers()
    self.wfile.write(jsonob.encode())

  def _send_head(self):
    """Unchanged from SimpleHTTPRequestHandler, for basic file serving."""
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
    Custom hack: add on "/html" for this server.
    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)
    """
    # abandon query parameters
    path = path.split('?',1)[0]
    path = path.split('#',1)[0]
    path = posixpath.normpath(urllib.parse.unquote(path))
    words = path.split('/')
    words = [w for w in words if w]

    # XXXXXX custom hack here:
    path = os.path.join(os.getcwd(), 'html')
    for word in words:
      drive, word = os.path.splitdrive(word)
      head, word = os.path.split(word)
      if word in (os.curdir, os.pardir): continue
      path = os.path.join(path, word)
    return path

  def _guess_type(self, path):
    """Unchanged from SimpleHTTPRequestHandler, for basic file serving."""
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
