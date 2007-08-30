import os, sys, time, gobject
from Queue import Queue

from GtkWorker import EmitPublisher, Publisher

logfile = "~/.pychess.log"

class LogPipe:
    def __init__ (self, to, flag=""):
        self.to = to
        self.flag = flag
    
    def write (self, data):
        if data.strip():
            log.debug (self.flag+data.strip())
        try:
            self.to.write(data)
        except IOError:
            log.error("Could not write data '%s' to pipe '%s'" % (data, repr(self.to)))

NEW_FILE, OLD_FILE, NO_FILE = range(3)
DEBUG, LOG, WARNING, ERROR = range(4)
labels = {DEBUG: "Debug", LOG: "Log", WARNING: "Warning", ERROR: "Error"}

class Log (gobject.GObject):
    
    __gsignals__ = {
        "logged": (gobject.SIGNAL_RUN_FIRST, None, (object,))
    }                                              # list of (str, str, int)
    
    def __init__ (self, logpath, storage):
        gobject.GObject.__init__(self)
        
        if storage == NO_FILE:
            self.file = None
        elif storage == NEW_FILE or not os.path.exists (logpath):
            self.file = open (logpath, "w")
        else:
            self.file = open (logpath, "a")
        
        # We store everything in ram for the sake of the LogViewer.
        # Not very smart really
        self.messages = []
        
        self.publisher = EmitPublisher (self, "logged", Publisher.SEND_LIST)
        self.publisher.start()

    def _format (self, task, message, type):
        t = time.strftime ("%F %T")
        return "%s %s %s: %s" % (t, task, labels[type], message)
    
    def _log (self, task, message, type):
        if self.file:
            formated = self._format(task, message, type)
            try:
                print >> self.file, formated
            except IOError, e:
                if not type == ERROR:
                    self.error("Unable to write '%s' to log file because of error: %s" % \
                            (formated, ", ".join(str(a) for a in e.args)))
        self.messages.append((task, message, type))
        self.publisher.put((task, message, type))
        if type == ERROR:
            print formated
    
    def debug (self, message, task="Default"):
        self._log (task, message, DEBUG)
    
    def log (self, message, task="Default"):
        self._log (task, message, LOG)
    
    def warn (self, message, task="Default"):
        self._log (task, message, WARNING)
    
    def error (self, message, task="Default"):
        self._log (task, message, ERROR)

log = Log (os.path.expanduser(logfile), NEW_FILE)
