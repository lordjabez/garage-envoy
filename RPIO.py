BCM = 0
BOARD = 1

OUT = 0
IN = 1

PUD_UP = 0
PUD_DOWN = 1


def setmode(mode):
    pass


def setup(pin, mode, pull_up_down=None):
    pass


def input(pin):
    pass


def output(pin, state):
    pass


def add_interrupt_callback(pin, mode, debounce_timeout_ms=0):
    pass


def wait_for_interrupts(threaded):
    pass
