#!/usr/bin/env python


# Standard library imports
import argparse
import json
import logging
import logging.handlers
import time

# Additional library imports
import bottle
import RPIO


# These are logical pin numbers based on the Broadcom
# chip on the Raspberry Pi model A/B (not the plus).
TRIGGER_PIN = 17
OPEN_SENSOR = 25
CLOSED_SENSOR = 24


# Parse the command line parameters.
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='enable debug logging')
parser.add_argument('-l', '--log', help='path and file name for log files (will use console if not specified)')
args = parser.parse_args()


# Configure the logging module.
logformat = '%(asctime)s : %(levelname)s : %(name)s : %(message)s'
loglevel = logging.DEBUG if args.debug else logging.INFO
if args.log:
    loghandler = logging.handlers.RotatingFileHandler(args.log, maxBytes=16*1024*1024, backupCount=16)
    logging.basicConfig(handlers=[loghandler], format=logformat, level=loglevel)
else:
    logging.basicConfig(format=logformat, level=loglevel)


# Stores all events in memory. Eventually this may be
# moved to non-volitle storage, but this works for now.
events = {'open': [], 'closed': [], 'trigger': []}


def readevents(num):
    pass



def logevent(name, state=None):
    """ TODO add comments everywhere """
    event = {'name': name, 'time': time.time()}
    if state is not None:
        event['state'] = state
    logging.debug(str(event))
    return event


def logopen(_, state):
    logevent('open', state == 1)


def logclosed(_, state):
    logevent('closed', state == 1)


@bottle.post('/_trigger')
def posttrigger():
    RPIO.output(TRIGGER_PIN, False)
    time.sleep(0.2)
    RPIO.output(TRIGGER_PIN, True)
    logevent('trigger')


@bottle.get('/events')
def getevents():
    num = int(bottle.request.query.get('n') or 0)
    return readevents(100)
    #return {'open': events['open'][-n:], 'closed': events['closed'][-n:], 'trigger': events['trigger'][-n:]}


@bottle.get('/')
@bottle.get('/<filename:path>')
def getfile(filename='index.html'):
    response = bottle.static_file(filename, root='www')
    response.set_header('Cache-Control', 'max-age=31557600')
    return response


RPIO.setmode(RPIO.BCM)

RPIO.setup(TRIGGER_PIN, RPIO.OUT)
RPIO.output(TRIGGER_PIN, True)

RPIO.add_interrupt_callback(OPEN_SENSOR, logopen, debounce_timeout_ms=100)
RPIO.add_interrupt_callback(CLOSED_SENSOR, logclosed, debounce_timeout_ms=100)

RPIO.setup(OPEN_SENSOR, RPIO.IN, pull_up_down=RPIO.PUD_UP)
RPIO.setup(CLOSED_SENSOR, RPIO.IN, pull_up_down=RPIO.PUD_UP)

logopen(OPEN_SENSOR, RPIO.input(OPEN_SENSOR))
logclosed(CLOSED_SENSOR, RPIO.input(CLOSED_SENSOR))

RPIO.wait_for_interrupts(threaded=True)

# Configure and start the webserver
logging.getLogger('waitress').setLevel(loglevel)
bottle.run(server='waitress', host='0.0.0.0', port=80, quiet=(not args.debug), debug=args.debug)


RPIO.cleanup()
