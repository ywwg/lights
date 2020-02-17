#!/usr/bin/python3

from lights import fluxhandler
from lights import lightserver

import socketserver
import sys

class ThreadedTCPServer(socketserver.ThreadingMixIn,socketserver.TCPServer): pass

if __name__ == '__main__':
  if len(sys.argv) < 2:
    print("Usage: lights.py (--fake) [port]")
    print(" --fake: Use fake lights, not real ones")
    sys.exit(1)

  fake = False
  if len(sys.argv) > 2:
    if sys.argv[1] == '--fake':
      fake = True

  port = int(sys.argv[-1])

  lightserver.FluxHandler = fluxhandler.Lights(fake=fake, must_find_all=True)
  handler = lightserver.LightsHTTPRequestHandler
  httpd = ThreadedTCPServer(("", port), handler)
  print("serving at port", port)
  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    pass
  httpd.server_close()
