import fileinput
import threading


BCM = 0
BOARD = 1

OUT = 0
IN = 1

PUD_UP = 0
PUD_DOWN = 1


_pins = {}
_callbacks = {}


_keyinput = input


def _setpin(pin, value):
    _pins[pin] = value
    _callbacks[pin](pin, value)


def _togglepin(pin):
    _setpin(pin, 0 if _pins[pin] else 1)


def _getinputs():
    while True:
        code = _keyinput()
        if code == 'c':
            _togglepin(24)
        elif code == 'o':
            _togglepin(25)


def setmode(mode):
    pass


def setup(pin, mode, pull_up_down=None):
    if mode == IN:
        _pins[pin] = 0


def input(pin):
    return _pins[pin]


def output(pin, state):
    _pins[pin] = state


def add_interrupt_callback(pin, callback, debounce_timeout_ms=0):
    _callbacks[pin] = callback


def wait_for_interrupts(threaded):
    if threaded:
        threading.Thread(target=_getinputs).start()
    else:
        _getinputs()


def cleanup():
    pass


def _setclosed():
    _setpin(24, 1)


def _setopen():
    _setpin(25, 1)


def _dotrigger():
    if pin == 17:
        if _pins.get(24):
            _togglepin(24)
        elif _pins.get(25):
            _togglepin(25)
        else:
            threading.Timer(7.5, _setclosed).start()
