# Lights

A little webserver for controlling my Flux smart WiFi lights.  This might be useful for
other people who hate the MagicHome app!

![UI Screenshot](screenshot.png?raw=true)

## Setup

* Install [flux_led](https://github.com/Danielhiversen/flux_led).
* run `npm update` to install js deps
* Run `flux_led -s` to scan for bulbs.
* Edit fluxhandler.py and add your bulb MAC addresses to the list of BULBS, and give them names.
* Edit lightserver.py to create whatever PRESETS you want to have.  Use "all" to apply the same color to all bulbs, or you can set different values for different bulbs

## Running

Start up the server on port 8000

```shell
./lights.py 8000
```

And then go to [http://localhost:8000](http://localhost:8000).

## Testing

You can run the server without actually connecting to real lightbulbs by doing:

```shell
./lights 8000 --fake
```
