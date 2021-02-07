#!/usr/bin/python3

from lights import fluxhandler
from lights import lightserver

import argparse
import json
import socketserver
import sys

class ThreadedTCPServer(socketserver.ThreadingMixIn,socketserver.TCPServer): pass

def LoadConfig(path):
  """Load a json config.

  The config should have three sections: bulbs, groups, and presets.
  bulbs is a map of hex ID to bulb name.
  groups is a map of group name to list of bulb names.
  presets is a map of preset name to the Preset namedtuple:
    sort_order, which is an int sorting of the presets, and
    bulbs, which is a map of bulb name to rgbw value

  Raises:
    Whatever various function calls might raise, like FileNotFound, etc.
  """
  config = None
  with open(path) as f:
    config = json.load(f)

  presets = {}
  for name in config['presets']:
    presets[name] = lightserver.Preset(**config['presets'][name])

  return config['bulbs'], config['groups'], presets

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("--port", help="port to run on",
                    type=int, default=8000)
  parser.add_argument("--fake", help="use fake lights")
  parser.add_argument("config", help="configuration file",
                    type=str)
  args = parser.parse_args()

  bulbs, groups, presets = LoadConfig(args.config)

  lightserver.FluxHandler = fluxhandler.Lights(
    bulbs, fake=args.fake, must_find_all=True)

  def handler(*args, **kwargs):
    lightserver.LightsHTTPRequestHandler(
      groups, presets, *args, **kwargs)

  httpd = ThreadedTCPServer(("", args.port), handler)
  print("serving at port", args.port)
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    pass
  httpd.server_close()
