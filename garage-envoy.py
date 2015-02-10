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


# The state history is stored in a flat file.
HISTORY_FILENAME = 'history.log'


# These are logical pin numbers based on the Broadcom
# chip on the Raspberry Pi model A/B (not the plus).
TRIGGER_PIN = 17
OPEN_SENSOR = 25
CLOSED_SENSOR = 24
VIBRATION_SENSOR = 23


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


# Remember the most recent state so the history file doesn't
# require parsing whenever state transitions take place.
currstate = {'name': None, 'time': 0.0}


# Vibration is measured by checking the delta time between the
# most recent and the previous statechange. If its less than this
# threshold in seconds, the sensor is vibrating, otherwise it is not.
VIBRATION_DELTA = 1.0

# Gotta remember the last vibration values for the above to work.
lastvibrationstatus = False
lastvibrationtime = 0.0


def readhistory(num=0):
    """
    Get state history items from.
    @param num: The number of items to read
    @return: List of state items
    """
    try:
        with open(HISTORY_FILENAME, 'r') as historyfile:
            history = [json.loads(line) for line in historyfile]
        return history[-num:]
    except OSError:
        return []


def writehistory(state):
    """
    Write a state item to the history file.
    @param state: The state object to write
    """
    with open(HISTORY_FILENAME, 'a') as historyfile:
        historyfile.write(json.dumps(state) + '\n')


def updatestate(name):
    """
    Update the current state.
    @param name: The name of the new state
    """
    currstate = {'time': int(time.time() * 1000), 'name': name}
    writehistory(currstate)


def evaluatestate(sensor, status):
    """
    Determine the new state given a sensor event.
    @param sensor: The sensor event name
    @param status: The value of the sensor
    """
    # The open and closed sensors authoritatively determine state
    if sensor == 'open':
        updatestate('open' if status else 'closing')
    elif sensor == 'closed':
        updatestate('closed' if status else 'opening')
    # Otherwise fall back to the vibration sensor, but only override
    # the current state if the door is neither open nor closed.
    elif sensor == 'vibration':
        if status:
            if currstate.get('name') == 'half-open':
                updatestate('closing')
            elif currstate.get('name') == 'half-closed':
                updatestate('opening')
        else:
            if currstate.get('name') == 'opening':
                updatestate('half-open')
            elif currstate.get('name') == 'closing':
                updatestate('half-closed')


def handleopen(id, value):
    """
    Process the change of the open sensor.
    @param id: The GPIO pin identifier for the sensor (ignored)
    @param value: The GPIO pin value where 0 = open and 1 = closed
    """
    status = value != 0
    evaluatestate('open', status)
    logging.info('Open sensor changed to ' + str(status))


def handleclosed(id, value):
    """
    Process the change of the closed sensor.
    @param id: The GPIO pin identifier for the sensor (ignored)
    @param value: The GPIO pin value where 0 = open and 1 = closed
    """
    status = value != 0
    evaluatestate('closed', status)
    logging.info('Closed sensor changed to ' + str(status))


def handlevibration(id, value):
    """
    Process the change of the vibration sensor.
    @param id: The GPIO pin identifier for the sensor (ignored)
    @param value: The GPIO pin value (ignored)
    """
    global lastvibrationstatus
    global lastvibrationtime
    # Determine the vibration state by checking to see how
    # long it's been since the last vibration event. If the
    # delta is small enough, the sensor is vibrating.
    now = time.time()
    status = (now - lastvibrationtime) < VIBRATION_DELTA
    lastvibrationtime = now
    # Only re-evaluate state if the vibration state actually changes.
    if status != lastvibrationstatus:
        lastvibrationstatus = status
        evaluatestate('vibration', status)
        logging.info('Vibration sensor changed to ' + str(status))


def handletrigger():
    """Figuratively 'press the door button' by briefly closing the relay."""
    RPIO.output(TRIGGER_PIN, False)
    time.sleep(0.2)
    RPIO.output(TRIGGER_PIN, True)
    logging.info('Trigger occurred')


@bottle.post('/_trigger')
def posttrigger():
    """
    Trigger the garage door.
    @return: 204 NO CONTENT if the door is triggered successfully
             500 INTERNAL SERVER ERROR with an {error.json} document if an unknown problem occurs
    """
    bottle.response.status = 204
    handletrigger()


@bottle.get('/history')
def gethistory():
    """
    Get a list of states that represent door history.
    @return: 200 OK with a {history.json} document if the data is fetched successfully
             500 INTERNAL SERVER ERROR with an {error.json} document if an unknown problem occurs
    """
    num = int(bottle.request.query.get('n') or 0)
    return {'history': readhistory(num)}


@bottle.get('/')
@bottle.get('/<filename:path>')
def getfile(filename='index.html'):
    """
    Serve static content to clients, setting the cache value to one year.
    @param filename: The full path to the content being requested
    @return: 200 OK with the content if retrieved successfully
             404 NOT FOUND with an {error.json} document if the content is not available
             500 INTERNAL SERVER ERROR with an {error.json} document if an unknown problem occurs
    """
    response = bottle.static_file(filename, root='www')
    response.set_header('Cache-Control', 'max-age=31557600')
    return response


@bottle.error(400)
@bottle.error(404)
@bottle.error(422)
@bottle.error(500)
@bottle.error(504)
def _error(error):
    """
    Return an error message to clients.
    @param error: The error message from an above function
    @return: The appropriate error code with the {error.json} document
    """
    bottle.response.set_header('Cache-Control', 'no-cache')
    bottle.response.set_header('Content-Type', 'application/json')
    return json.dumps({'details': error.body})


def setupgpio():
    """Perform all necessary GPIO initialization."""

    # Use logical numbering because that's the only
    # thing compatible with the interrupt callbacks.
    RPIO.setmode(RPIO.BCM)

    # Set up the trigger output pin and ensure it is set to True, i.e. relay open.
    RPIO.setup(TRIGGER_PIN, RPIO.OUT)
    RPIO.output(TRIGGER_PIN, True)

    # Set up callbacks that fire when sensor state changes. Note the
    # smaller debounce on the vibration pin. Using a larger value would
    # suppress the very small changes the code is trying to detect.
    RPIO.add_interrupt_callback(OPEN_SENSOR, handleopen, debounce_timeout_ms=100)
    RPIO.add_interrupt_callback(CLOSED_SENSOR, handleclosed, debounce_timeout_ms=100)
    RPIO.add_interrupt_callback(VIBRATION_SENSOR, handlevibration, debounce_timeout_ms=20)

    # An additional setup call is required to ensure the pullup state
    # is set properly. Since the sensors are wired as normally closed
    # this allows the "switch closed" state to read as true.
    RPIO.setup(OPEN_SENSOR, RPIO.IN, pull_up_down=RPIO.PUD_UP)
    RPIO.setup(CLOSED_SENSOR, RPIO.IN, pull_up_down=RPIO.PUD_UP)
    RPIO.setup(VIBRATION_SENSOR, RPIO.IN, pull_up_down=RPIO.PUD_UP)

    # Start the thread that watches for events and calls the interrupt handlers.
    RPIO.wait_for_interrupts(threaded=True)


def cleanupgpio():
    """Release all GPIO resources."""
    RPIO.cleanup_interrupts()
    RPIO.cleanup()


def runwebserver():
    """Set up and run the webserver. This routine does not return until process termination."""
    logging.getLogger('waitress').setLevel(loglevel)
    bottle.run(server='waitress', host='0.0.0.0', port=80, quiet=(not args.debug), debug=args.debug)


# Start things up if running as the main module. Be sure to tidy up when done.
if __name__ == '__main__':
    try:
        setupgpio()
        runwebserver()
    finally:
        cleanupgpio()
