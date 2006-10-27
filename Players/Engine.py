from Player import Player

class EngineDead (Exception): pass

class Engine (Player):
   
    def setStrength (self, strength):
        """Takes strength 0, 1, 2 (higher is better)"""
        abstract
    
    def setTime (self, seconds, gain):
        abstract
    
    def setBoard (self, history):
        abstract
    
    def canAnalyze (self):
        abstract
    
    def analyze (self):
        pass #Won't be used if "canAnalyze" responds false
    
    def undoMoves (self, moves = 1):
        """Undos a number of moves."""
        pass #No yet used

    # Other methods
        
    def __repr__ (self):
        """For example 'GNU Chess 5.07'"""
        abstract
    
    def wait (self):
        pass #optional

from System.Log import log
import os, select, signal, time, errno, tty
import gobject
CHILD = 0

class EngineConnection (gobject.GObject):

    __gsignals__ = {
        'readline': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, (str,)),
        'hungup': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    def __init__(self, executable):
        gobject.GObject.__init__(self)
        self.pid, self.fd = os.forkpty()
        if self.pid == CHILD:
            os.nice(10)
            os.execv(executable, [""])
        
        self.defname = os.path.split(executable)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        
        log.debug(executable+"\n", self.defname)
        
        self.buffer = ""
        gobject.io_add_watch(self.fd, gobject.IO_HUP, self.recieved)

    def recieved (self, fd, condition):
        log.warn("hungup\n", self.defname)
        self.emit("hungup")
        return False
        
    def readline (self, timeout=600):
        i = self.buffer.find("\n")
        if i >= 0:
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line:
                return line
            
        while True:
            try:
                rlist, _, _ = select.select([self.fd], [], [], timeout)
                assert rlist
            except:
                return None
                
            try:
                data = os.read(self.fd, rlist[0])
            except OSError, error:
                if error.errno in (5, 9): # ioerrro, file-descriptor error
                    return None
                else: raise
                
            self.buffer += data.replace("\r\n","\n").replace("\r","\n")
            i = self.buffer.find("\n")
            if i < 0: continue
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line.strip():
                log.debug(line+"\n", self.defname)
                return line
    
    def write (self, data):
        try:
            log.log(data, self.defname)
            os.write(self.fd, data)
        except:
            pass

    def wait4exit (self):
        try:
            pid, code = os.waitpid(self.pid, 0)
            log.debug(os.strerror(code)+"\n", self.defname)
        except OSError, error:
            if error.errno == 10:
                #No child processes
                pass
            else: raise OSError, error

    def sigkill (self):
        #print "kill"
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.close(self.fd)
        except OSError, error:
            if error.errno == 3:
                #No such process
                pass
            else: raise OSError, error
    
    def sigterm (self):
        #print "term"
        try:
            os.kill(self.pid, signal.SIGTERM)
            os.close(self.fd)
        except OSError, error:
            if error.errno == 3:
                #No such process
                pass
            else: raise OSError, error
    
    def sigint (self):
        #print "int"
        try:
            os.kill(self.pid, signal.SIGINT)
        except OSError, error:
            if error.errno == 3:
                #No such process
                pass
            else: raise OSError, error
