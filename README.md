Overview
========

Garage Envoy is a system that provides an abstract HTTP JSON API (and accompanying mobile application) for garage doors. This API and GUI can be used by a variety of personal electronic devices (e.g. smartphones, tablets, laptops) to get status on the garage door, plus trigger it to open/close on demand. It is designed to be plug and play with minimal configuration required.

Hardware
========

- Raspberry Pi Model B
- 4GB SD card
- 5.25v DC power adapter
- 5v two channel relay
- magnetic sensors x 2
- vibration sensor

Software
========

Server
------

- Python 3
- waitress WSGI server
- bottle WSGI microframework
- jsonschema JSON validator
- RPIO interface library for GPIO

Client
------

- HTML / CSS
- Angular / JavaScript
- Ionic / Cordova
