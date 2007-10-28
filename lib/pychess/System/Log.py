import os, sys, time, gobject
from Queue import Queue
from GtkWorker import EmitPublisher, Publisher
from prefix import getHomePrefix, addHomePrefix

MAXFILES = 10
DEBUG, LOG, WARNING, ERROR = range(4)
labels = {DEBUG: "Debug", LOG: "Log", WARNING: "Warning", ERROR: "Error"}

class LogPipe:
    def __init__ (self, to, flag=""):
        self.to = to
        self.flag = flag
    
    def write (self, data):
        try:
            self.to.write(data)
        except IOError:
            log.error("Could not write data '%s' to pipe '%s'" % (data, repr(self.to)))
        if log:
            log.debug (data, self.flag)
        #self.flush()
    
    def flush (self):
        self.to.flush()
        #log.debug (".flush()", self.flag)
    
    def fileno (self):
        return self.to.fileno()

class Log (gobject.GObject):
    
    __gsignals__ = {
        "logged": (gobject.SIGNAL_RUN_FIRST, None, (object,))
    }                                              # list of (str, str, int)
    
    def __init__ (self, logpath):
        gobject.GObject.__init__(self)
        
        self.file = open(logpath, "w")
        
        self.printTime = True
        
        # We store everything in this list, so that the LogDialog, which is
        # imported a little later, will have all data ever given to Log.
        # When Dialog inits, it will set this list to None, and we will stop
        # appending data to it. Ugly? Somewhat I guess.
        self.messages = []
        
        self.publisher = EmitPublisher (self, "logged", Publisher.SEND_LIST)
        self.publisher.start()
    
    def _format (self, task, message, type):
        t = time.strftime ("%T")
        return "%s %s %s: %s" % (t, task, labels[type], message)
    
    def _log (self, task, message, type):
        if not message: return
        
        if self.printTime:
            message = self._format(task, message, type)
        self.printTime = message[-1] == ("\n")
        
        try:
            self.file.write(message)
            self.file.flush()
        except IOError, e:
            if not type == ERROR:
                self.error("Unable to write '%s' to log file because of error: %s" % \
                        (formated, ", ".join(str(a) for a in e.args)))
        
        if self.messages != None:
            self.messages.append((task, message, type))
        self.publisher.put((task, message, type))
        
        if type == ERROR and task != "stdout":
            print formated
    
    def debug (self, message, task="Default"):
        self._log (task, message, DEBUG)
    
    def log (self, message, task="Default"):
        self._log (task, message, LOG)
    
    def warn (self, message, task="Default"):
        self._log (task, message, WARNING)
    
    def error (self, message, task="Default"):
        self._log (task, message, ERROR)

oldlogs = [l for l in os.listdir(getHomePrefix()) if l.endswith(".log")]
if len(oldlogs) >= MAXFILES:
    oldlogs.sort()
    os.remove(addHomePrefix(oldlogs[0]))
newName = time.strftime("%Y-%m-%d_%H-%M-%S") + ".log"

log = Log (addHomePrefix(newName))

sys.stdout = LogPipe(sys.stdout, "stdout")
sys.stderr = LogPipe(sys.stderr, "stdout")
