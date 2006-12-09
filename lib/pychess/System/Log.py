import os, sys, time, gobject

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

DEBUG, LOG, WARNING, ERROR = range(4)
labels = {DEBUG: "Debug", LOG: "Log", WARNING: "Warning", ERROR: "Error"}

class Log (gobject.GObject):
    
    __gsignals__ = {
        'logged': (gobject.SIGNAL_RUN_FIRST, None, (str, str, int))
    }
    
    def __init__ (self, logpath):
        gobject.GObject.__init__(self)
        
        #if not os.path.exists (logpath):
        #    self.file = open (logpath, "w")
        #else: self.file = open (logpath, "a")
        
        # As we do not want gigantic logfiles, 
        # we should probably erase it every time we start.
        self.file = open (logpath, "w")
        
        self.messages = []

    def _format (self, task, message, type):
        t = time.strftime ("%F %T")
        return "%s %s %s: %s" % (t, task, labels[type], message)
    
    def _log (self, task, message, type):
        formated = self._format(task, message, type)
        print >> self.file, formated
        self.messages.append ((task, message, type))
        self.emit ("logged", task, message, type)
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

log = Log (os.path.expanduser(logfile))
