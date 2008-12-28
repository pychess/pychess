import os
import signal
import errno
import time

import gtk
import gobject

from pychess.Utils.const import *
from Log import log
from pychess.System.ThreadPool import pool
from pychess.System import glock

class SubProcessError (Exception): pass
class TimeOutError (Exception): pass

def searchPath (file, pathvar="PATH", access=os.R_OK):
    for dir in os.environ[pathvar].split(os.pathsep):
        dir = os.path.abspath(dir)
        path = os.path.join(dir, file)
        if os.path.isfile(path):
            if not os.access (path, access):
                log.warn("Not enough permissions on %s\n" % path)
            else:
                return path
    return None

hasPrivateLooper = False

class SubProcess (gobject.GObject):
    
    __gsignals__ = {
        "line": (gobject.SIGNAL_RUN_FIRST, None, (str,)),
        "died": (gobject.SIGNAL_RUN_FIRST, None, ())
    }
    
    def __init__(self, path, args=[], warnwords=[], env=None):
        gobject.GObject.__init__(self)
        
        self.path = path
        self.args = args
        self.warnwords = warnwords
        self.env = env or os.environ
        self.buffer = ""
        
        self.defname = os.path.split(path)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        t = time.time()
        self.defname = (self.defname,
                        time.strftime("%H:%m:%%.3f",time.localtime(t)) % (t%60))
        log.debug(path+"\n", self.defname)
        
        argv = [str(u) for u in [self.path]+self.args]
        self.pid, stdin, stdout, stderr = gobject.spawn_async(argv,
                child_setup=self.__setup,
                standard_input=True, standard_output=True, standard_error=True,
                flags=gobject.SPAWN_DO_NOT_REAP_CHILD|gobject.SPAWN_SEARCH_PATH)
        
        self.inChannel = self._initChannel(stdin, None, None, False)
        readFlags = gobject.IO_IN|gobject.IO_PRI|gobject.IO_ERR
        self.outChannel = self._initChannel(stdout, readFlags, self.__io_cb, False)
        self.errChannel = self._initChannel(stderr, readFlags, self.__io_cb, True)
        
        gobject.child_watch_add(self.pid, self.__child_watch_callback)
    
    def _initChannel (self, filedesc, callbackflag, callback, isstderr):
        channel = gobject.IOChannel(filedesc)
        channel.set_flags(channel.get_flags() | gobject.IO_FLAG_NONBLOCK)
        if callback:
            channel.add_watch(callbackflag, callback, isstderr)
        return channel
    
    def __setup (self):
        os.nice(15)
    
    def __child_watch_callback (self, pid, code):
        if code not in (0,11): # Success and 'Resource temporarily unavailable'
            log.error(os.strerror(code)+"\n", self.defname)
            self.emit("died")
    
    def __io_cb (self, channel, condition, isstderr):
        
        while True:
            line = channel.readline()
            if not line:
                return True
            
            if isstderr:
                log.error(line, self.defname)
            else:
                for word in self.warnwords:
                    if word in line:
                        log.warn(line, self.defname)
                        break
                else: log.debug(line, self.defname)
            
            self.emit("line", line)
    
    def write (self, data):
        log.log(data, self.defname)
        self.inChannel.write(data)
        if data.endswith("\n"):
            try:
                self.inChannel.flush()
            except gobject.GError, e:
                log.error(str(e)+". Last line wasn't sent.\n", self.defname)
    
    def wait4exit (self, timeout=None):
        """ Wait timeout seconds for process to die. Returns true if process
            is dead (and was reaped), false if alive. """
        
        try:
            if timeout:
                # Try a few times to reap the process with waitpid:
                totalwait = timeout
                deltawait = timeout/1000.0
                if deltawait < 0.01 and totalwait > 0.01:
                    deltawait = 0.01
                while totalwait > 0:
                    pid, code = os.waitpid(self.pid, os.WNOHANG)
                    if pid:
                        code = (code, os.strerror(code))
                        log.debug("Exitcode %d %s\n" % code, self.defname)
                        return code
                    time.sleep(deltawait)
                    totalwait -= deltawait
            else:
                # If no timeout, we don't add os.WNOHANG, to block until data
                pid, code = os.waitpid(self.pid, 0)
                code = (code, os.strerror(code))
                log.debug("Exitcode %d %s\n" % code, self.defname)
                return code
        
        except OSError, error:
            if error.errno == errno.ECHILD:
                log.debug("waitpid raised 'No child processes'\n", self.defname)
                return (0, os.strerror(0))
            else: raise OSError, error
        
        return (None, None)
    
    def sendSignal (self, sign):
        try:
            os.kill(self.pid, signal.SIGCONT)
            os.kill(self.pid, sign)
        except OSError, error:
            if error.errno == errno.ESRCH:
                #No such process
                pass
            else: raise OSError, error
    
    def gentleKill (self, first=1.0, second=0.5):
        code, string = self.wait4exit(timeout=first)
        if code == None:
            self.sigterm()
            code, string = self.wait4exit(timeout=second)
            if code == None:
                self.sigkill()
                return self.wait4exit()[0]
            return code
        return code
    
    def pause (self):
        self.sendSignal(signal.SIGSTOP)
    
    def resume (self):
        self.sendSignal(signal.SIGCONT)
    
    def sigkill (self):
        self.sendSignal(signal.SIGKILL)
    
    def sigterm (self):
        self.sendSignal(signal.SIGTERM)
    
    def sigint (self):
        self.sendSignal(signal.SIGINT)

if __name__ == "__main__":
    loop = gobject.MainLoop()
    paths = ("igang.dk", "google.com", "google.dk", "ahle.dk", "myspace.com", "yahoo.com")
    maxlen = max(len(p) for p in paths)
    def callback (subp, line, path):
        print "\t", path.ljust(maxlen), line.rstrip("\n")
    for path in paths:
        subp = SubProcess("/bin/ping", [path])
        subp.connect("line", callback, path)
    loop.run()