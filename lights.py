#!/usr/bin/python3

from lights import fluxhandler
from lights import lightserver

import socketserver
import sys

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print("Usage: lights.py [port] (--fake)")
    print(" --fake: Use fake lights, not real ones")
    sys.exit(1)

  port = int(sys.argv[1])
  fake = False
  if len(sys.argv) > 2:
    if sys.argv[2] == '--fake':
      fake = True

  lightserver.FluxHandler = fluxhandler.Lights(fake=fake, must_find_all=True)
  handler = lightserver.LightsHTTPRequestHandler
  httpd = socketserver.TCPServer(("", port), handler)
  print("serving at port", port)
  httpd.serve_forever()
