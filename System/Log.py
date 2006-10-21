import os, sys, time

debug = False
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
class Log:
    errors = []
    
    def __init__ (self, logpath):
        if not os.path.exists (logpath):
            self.file = open (logpath, "w")
        else: self.file = open (logpath, "a")

    def _format (self, message, type=""):
        t = time.strftime ("%F %T")
        return "%s %s: %s\n" % (t, type, message)
    
    def debug (self, message, flush = False):
        self.file.write (self._format(message, "Debug"))
        if flush: self.file.flush ()
        if debug:
            sys.stdout.write ("D %s\n" % message)
    
    def log (self, message, flush = True):
        self.file.write (self._format(message))
        sys.stdout.write ("L %s\n" % message)
        if flush: self.file.flush ()
    
    def warn (self, message, flush = True):
        self.file.write (self._format(message, "Warning"));
        if flush: self.file.flush ()
        sys.stderr.write ("*W* %s\n" % message)
    
    def error (self, message, flush = True):
        self.file.write (self._format(message, "Error"));
        if flush: self.file.flush ()
        sys.stderr.write ("*E* %s\n" % message)
        global debug
        debug = True
        if len (self.errors) > 0 and self.errors[-1][0] == message:
            self.errors[-1][1] += 1
        else: self.errors += [[message, 1]]
    
    def _times (self, number):
        return number == 1 and "1 time" or ("%d times" % number)
    
    def getErrors (self):
        return "\n".join (["Reported %s: <i>%s</i>" % (self._times(cnt),mes) \
                for mes, cnt in self.errors])
    
    def clearErrors (self):
        del self.errors[:]

log = Log (os.path.expanduser(logfile))
