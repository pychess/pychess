import time
import logging

from gi.repository import GObject, GLib


class LogEmitter(GObject.GObject):
    __gsignals__ = {
        "logged": (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }  # list of (str, float, str, int)

    def __init__(self):
        GObject.GObject.__init__(self)

        # We store everything in this list, so that the LogDialog, which is
        # imported a little later, will have all data ever given to Log.
        # When Dialog inits, it will set this list to None, and we will stop
        # appending data to it. Ugly? Somewhat I guess.
        self.messages = []


class GLogHandler(logging.Handler):
    def __init__(self, emitter):
        logging.Handler.__init__(self)
        self.emitter = emitter

    def emit(self, record):
        def _emit(record):
            message = self.format(record)
            if self.emitter.messages is not None:
                self.emitter.messages.append(
                    (record.task, time.time(), message, record.levelno)
                )

            self.emitter.emit(
                "logged", (record.task, time.time(), message, record.levelno)
            )

        GLib.idle_add(_emit, record)


logemitter = LogEmitter()
