#!/usr/bin/env python


# Standard library imports
import time

# Additional library imports
import bottle
import RPIO


# These are logical pin numbers based on the Broadcom
# chip on the Raspberry Pi model A/B (not the plus).
TRIGGER_PIN = 17
OPEN_SENSOR = 25
CLOSED_SENSOR = 24


# Stores all events in memory. Eventually this may be
# moved to non-volitle storage, but this works for now.
events = {'open': [], 'closed': [], 'trigger': []}


def logevent(name, state=None):
    """ TODO add comments everywhere """
    event = {'time': time.time()}
    if state is not None:
        event['state'] = state
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
    n = int(bottle.request.query.get('n') or 0)
    return {'open': events['open'][-n:], 'closed': events['closed'][-n:], 'trigger': events['trigger'][-n:]}


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


bottle.run(server='waitress', host='0.0.0.0', port=80, quiet=True, debug=False)


RPIO.cleanup()
