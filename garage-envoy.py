#!/usr/bin/env python


# Standard library imports
import argparse
import json
import logging
import logging.handlers
import threading
import time

# Additional library imports
import bottle
import RPIO


# The event log is stored in a flat file.
EVENT_LOG_FILENAME = 'events.log'


# These are logical pin numbers based on the Broadcom
# chip on the Raspberry Pi model A/B (not the plus).
TRIGGER_PIN = 17
OPEN_SENSOR = 25
CLOSED_SENSOR = 24

# The max time it takes the garage door to open/close in seconds.
# This value is used to determine door state from sensor events.
DOOR_TIME = 15.0


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


# Remember the two most recent events so the event
# log file doesn't have to be read every time.
thisevent = None
prevevent = None


def isrecent(event):
    recenttime = time.time() - DOOR_TIME
    return event['time'] > recenttime


def issensor(event):
    return event['type'] == 'sensor'


def isstate(event):
    return event['type'] == 'state'


def istransient(event):
    return event['type'] == 'state' and event['name'].endswith('ing')


def isopening(event):
    return event['type'] == 'state' and event['name'] == 'opening'


def isclosing(event):
    return event['type'] == 'state' and event['name'] == 'closing'


def ishalfopen(event):
    return isstate(event) and event['name'] == 'half-open'


def ishalfclosed(event):
    return isstate(event) and event['name'] == 'half-closed'


def isopen(event):
    return issensor(event) and event['name'] == 'open'


def isclosed(event):
    return issensor(event) and event['name'] == 'closed'


def istrigger(event):
    return issensor(event) and event['name'] == 'trigger'


def istrue(event):
    return issensor(event) and event.get('value', False)


def readevents(num=0, type=None):
    with open(EVENT_LOG_FILENAME, 'r') as eventfile:
        events = [json.loads(line) for line in eventfile]
    if type:
        events = [e for e in events if e['type'] == type]
    return events[-num:]


def writeevent(event):
    with open(EVENT_LOG_FILENAME, 'a') as eventfile:
        eventfile.write(json.dumps(event) + '\n')


def logevent(type, name, value=None):
    global thisevent
    global prevevent
    prevevent = thisevent
    thisevent = {'time': time.time(), 'type': type, 'name': name, 'value': value}
    writeevent(thisevent)


def logstate():
    global thisevent
    global prevevent
    if isopen(thisevent):
        if istrue(thisevent):
            logevent('state', 'open')
        else:
            logevent('state', 'closing')
    elif isclosed(thisevent):
        if istrue(thisevent):
            logevent('state', 'closed')
        else:
            logevent('state', 'opening')
    elif istrigger(thisevent):
        if isclosing(prevevent) or ishalfclosed(prevevent):
            logevent('state', 'opening')
        elif isopening(prevevent) or ishalfopen(prevevent):
            logevent('state', 'closing')
    elif not isrecent(thisevent):
        if isopening(thisevent):
            logevent('state', 'half-open')
        elif isclosing(thisevent):
            logevent('state', 'half-closed')


def logstatelater():
    threading.Timer(DOOR_TIME, logstate).start()


def handleopen(_, value):
    logevent('sensor', 'open', value != 0)
    logstate()
    logstatelater()


def handleclosed(_, value):
    logevent('sensor', 'closed', value != 0)
    logstate()
    logstatelater()


def handletrigger():
    logevent('sensor', 'trigger')
    logstate()
    RPIO.output(TRIGGER_PIN, False)
    time.sleep(0.2)
    RPIO.output(TRIGGER_PIN, True)


@bottle.post('/_trigger')
def posttrigger():
    handletrigger()


@bottle.get('/events')
def getevents():
    num = int(bottle.request.query.get('n') or 0)
    type = bottle.request.query.get('t')
    return {'events': readevents(num, type)}


@bottle.get('/')
@bottle.get('/<filename:path>')
def getfile(filename='index.html'):
    response = bottle.static_file(filename, root='www')
    response.set_header('Cache-Control', 'max-age=31557600')
    return response


# Use logical numbering because that's the only
# thing compatible with the interrupt callbacks.
RPIO.setmode(RPIO.BCM)

# Set up the trigger output pin and ensure it is set to True, i.e. relay open.
RPIO.setup(TRIGGER_PIN, RPIO.OUT)
RPIO.output(TRIGGER_PIN, True)

# Set up callbacks that fire when sensor state changes.
RPIO.add_interrupt_callback(OPEN_SENSOR, handleopen, debounce_timeout_ms=100)
RPIO.add_interrupt_callback(CLOSED_SENSOR, handleclosed, debounce_timeout_ms=100)

# An additional setup call is required to ensure the pullup state
# is set properly. Since the sensors are wired as normally closed
# this allows the "magswitch closed" state to read as true.
RPIO.setup(OPEN_SENSOR, RPIO.IN, pull_up_down=RPIO.PUD_UP)
RPIO.setup(CLOSED_SENSOR, RPIO.IN, pull_up_down=RPIO.PUD_UP)

# Grab the initial state of each of the sensors.
handleopen(OPEN_SENSOR, RPIO.input(OPEN_SENSOR))
handleclosed(CLOSED_SENSOR, RPIO.input(CLOSED_SENSOR))

# Start the thread that watches for events and calls the interrupt handlers.
RPIO.wait_for_interrupts(threaded=True)


# Configure and start the webserver.
logging.getLogger('waitress').setLevel(loglevel)
bottle.run(server='waitress', host='0.0.0.0', port=80, quiet=(not args.debug), debug=args.debug)


# Release the GPIO resources at exit.
RPIO.cleanup()
