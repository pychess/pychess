import os
import sys
import signal
import errno
import time
import threading

import gtk
import gobject

from pychess.Utils.const import *
from Log import log
from which import which
from pychess.System.ThreadPool import pool
from pychess.System import glock
from pychess.System.GtkWorker import EmitPublisher

class SubProcessError (Exception): pass
class TimeOutError (Exception): pass

def searchPath (file, access=os.R_OK, altpath=None):
    if altpath and os.path.isfile(altpath):
        if not os.access (altpath, access):
            log.warning("Not enough permissions on %s\n" % altpath)
        else:
            return altpath

    return which(file, mode=access)

subprocesses = []
def finishAllSubprocesses ():
    for subprocess in subprocesses:
        if subprocess.subprocExitCode[0] == None:
            subprocess.gentleKill(0,0.3)
    for subprocess in subprocesses:
        subprocess.subprocFinishedEvent.wait()

class SubProcess (gobject.GObject):
    
    __gsignals__ = {
        "line": (gobject.SIGNAL_RUN_FIRST, None, (object,)),
        "died": (gobject.SIGNAL_RUN_FIRST, None, ())
    }
    
    def __init__(self, path, args=[], warnwords=[], env=None, chdir="."):
        gobject.GObject.__init__(self)
        
        self.path = path
        self.args = args
        self.warnwords = warnwords
        self.env = env or os.environ
        self.buffer = ""
        
        self.linePublisher = EmitPublisher(self, "line", EmitPublisher.SEND_LIST)
        self.linePublisher.start()
        
        self.defname = os.path.split(path)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        t = time.time()
        self.defname = (self.defname,
                        time.strftime("%H:%m:%%.3f",time.localtime(t)) % (t%60))
        log.debug(path+"\n", extra={"task":self.defname})
        
        argv = [str(u) for u in [self.path]+self.args]
        self.pid, stdin, stdout, stderr = gobject.spawn_async(argv,
                working_directory=chdir, child_setup=self.__setup,
                standard_input=True, standard_output=True, standard_error=True,
                flags=gobject.SPAWN_DO_NOT_REAP_CHILD|gobject.SPAWN_SEARCH_PATH)
        
        self.__channelTags = []
        self.inChannel = self._initChannel(stdin, None, None, False)
        readFlags = gobject.IO_IN|gobject.IO_HUP#|gobject.IO_ERR
        self.outChannel = self._initChannel(stdout, readFlags, self.__io_cb, False)
        self.errChannel = self._initChannel(stderr, readFlags, self.__io_cb, True)
        
        self.channelsClosed = False
        self.channelsClosedLock = threading.Lock()
        gobject.child_watch_add(self.pid, self.__child_watch_callback)
        
        self.subprocExitCode = (None, None)
        self.subprocFinishedEvent = threading.Event()
        subprocesses.append(self)
        pool.start(self._wait4exit)
    
    def _initChannel (self, filedesc, callbackflag, callback, isstderr):
        channel = gobject.IOChannel(filedesc)
        if sys.platform != "win32":
            channel.set_flags(gobject.IO_FLAG_NONBLOCK)
        if callback:
            tag = channel.add_watch(callbackflag, callback, isstderr)
            self.__channelTags.append(tag)
        return channel
    
    def _closeChannels (self):
        self.channelsClosedLock.acquire()
        try:
            if self.channelsClosed == True:
                return
            self.channelsClosed = True
        finally:
            self.channelsClosedLock.release()

        for tag in self.__channelTags:
            gobject.source_remove(tag)
        for channel in (self.inChannel, self.outChannel, self.errChannel):
            try:
                channel.close()
            except gobject.GError, error:
                pass
    
    def __setup (self):
        os.nice(15)
    
    def __child_watch_callback (self, pid, code):
        # Kill the engine on any signal but 'Resource temporarily unavailable'
        if code != errno.EWOULDBLOCK:
            if type(code) == str:
                log.error(code+"\n", extra={"task":self.defname})
            else: log.error(os.strerror(code)+"\n", extra={"task":self.defname})
            self.emit("died")
            self.gentleKill()
    
    def __io_cb (self, channel, condition, isstderr):
        while True:
            try:
                line = channel.next()#readline()
            except StopIteration:
                self._wait4exit()
                self.__child_watch_callback(*self.subprocExitCode)
                break
            if not line:
                return True
            if isstderr:
                log.error(line, extra={"task":self.defname})
            else:
                for word in self.warnwords:
                    if word in line:
                        log.warning(line, extra={"task":self.defname})
                        break
                else: log.debug(line, extra={"task":self.defname})
            
            self.linePublisher.put(line)

    def write (self, data):
        if self.channelsClosed:
            log.warning("Chan closed for %r" % data, extra={"task":self.defname})
            return
        log.info(data, extra={"task":self.defname})
        self.inChannel.write(data)
        if data.endswith("\n"):
            try:
                self.inChannel.flush()
            except gobject.GError, e:
                log.error(str(e)+". Last line wasn't sent.\n", extra={"task":self.defname})

    def _wait4exit (self):
        try:
            pid, code = os.waitpid(self.pid, 0)
        except OSError, error:
            if error.errno == errno.ECHILD:
                pid, code = self.pid, error.errno
            else:
                raise

        self.subprocExitCode = (code, os.strerror(code))
    
    def sendSignal (self, sign):
        try:
            if sys.platform != "win32":
                os.kill(self.pid, signal.SIGCONT)
            os.kill(self.pid, sign)
        except OSError, error:
            if error.errno == errno.ESRCH:
                #No such process
                pass
            else: raise OSError, error
    
    def gentleKill (self, first=1, second=1):
        if pool is not None:
            pool.start(self.__gentleKill_inner, first, second)
    
    def __gentleKill_inner (self, first, second):
        self.resume()
        self._closeChannels()
        time.sleep(first)
        code, string = self.subprocExitCode
        if code == None:
            self.sigterm()
            time.sleep(second)
            code, string = self.subprocExitCode
            if code == None:
                self.sigkill()
                self.subprocFinishedEvent.set()
                return self.subprocExitCode[0]
            self.subprocFinishedEvent.set()
            return code
        self.subprocFinishedEvent.set()
        return code
    
    def pause (self):
        self.sendSignal(signal.SIGSTOP)
    
    def resume (self):
        if sys.platform != "win32":
            self.sendSignal(signal.SIGCONT)
    
    def sigkill (self):
        self.sendSignal(signal.SIGKILL)
    
    def sigterm (self):
        self.sendSignal(signal.SIGTERM)
    
    def sigint (self):
        self.sendSignal(signal.SIGINT)

if __name__ == "__main__":
    loop = gobject.MainLoop()
    paths = ("igang.dk", "google.com", "google.dk", "myspace.com", "yahoo.com")
    maxlen = max(len(p) for p in paths)
    def callback (subp, line, path):
        print "\t", path.ljust(maxlen), line.rstrip("\n")
    for path in paths:
        subp = SubProcess("/bin/ping", [path])
        subp.connect("line", callback, path)
    loop.run()
