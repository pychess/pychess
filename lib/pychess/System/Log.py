import os
import sys
import time
import logging

from prefix import addUserDataPrefix

newName = time.strftime("%Y-%m-%d_%H-%M-%S") + ".log"
logformat = "%(asctime)s %(task)s %(levelname)s: %(message)s"
logging.basicConfig(filename=addUserDataPrefix(newName), format=logformat, datefmt='%H:%M:%S')

class ExtraAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        kwargs["extra"] = kwargs.get("extra", {"task": "Default"})
        return msg, kwargs

class LogEmitter():
    messages = []
    def connect(self, signal, messages):
        return

logemitter = LogEmitter()

def set_gui_log_emitter():
    global logemitter
    import gobject
    from GtkWorker import EmitPublisher, Publisher

    class LogEmitter(gobject.GObject):
        __gsignals__ = {
            "logged": (gobject.SIGNAL_RUN_FIRST, None, (object,))
        }                                              # list of (str, float, str, int)
        def __init__ (self):
            gobject.GObject.__init__(self)

            # We store everything in this list, so that the LogDialog, which is
            # imported a little later, will have all data ever given to Log.
            # When Dialog inits, it will set this list to None, and we will stop
            # appending data to it. Ugly? Somewhat I guess.
            self.messages = []

            self.publisher = EmitPublisher (self, "logged",
                'LogEmitter.publisher.emit', Publisher.SEND_LIST)
            self.publisher.start()

    class GLogHandler(logging.Handler):
        def __init__ (self, emitter):
            logging.Handler.__init__(self)
            self.emitter = emitter
            
        def emit(self, record):
            message = self.format(record)
            if self.emitter.messages != None:
                self.emitter.messages.append((record.task, time.time(), message, record.levelno))
            
            self.emitter.publisher.put((record.task, time.time(), message, record.levelno))

    logemitter = LogEmitter()
    logger.addHandler(GLogHandler(logemitter))
    

logger = logging.getLogger()
log = ExtraAdapter(logger, {})
    
    
class LogPipe:
    def __init__ (self, to, flag=""):
        self.to = to
        self.flag = flag
    
    def write (self, data):
        try:
            self.to.write(data)
        except IOError:
            if self.flag == "stdout":
                # Certainly hope we never end up here
                pass
            else:
                log.error("Could not write data '%s' to pipe '%s'" % (data, repr(self.to)))
        if log:
            log.debug (data, extra={"task": self.flag})
    
    def flush (self):
        self.to.flush()
    
    def fileno (self):
        return self.to.fileno()

sys.stdout = LogPipe(sys.stdout, "stdout")
sys.stderr = LogPipe(sys.stderr, "stdout")
