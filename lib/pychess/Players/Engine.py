from Player import Player
from pychess.Utils.const import ARTIFICIAL

class EngineDead (Exception): pass

class Engine (Player):
   
    __type__ = ARTIFICIAL
   
    def setStrength (self, strength):
        """ Takes strength 0, 1, 2 (higher is better) """
        abstract
    
    def setDepth (self, depth):
        """ Sets the depth of the engine. Should only be used for analyze engines.
            Other engines will use the setStrength method. """
        pass
    
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

from time import time
from pychess.System.Log import log
import os, select, signal, errno, tty
import gobject
from random import randint, choice
CHILD = 0

class EngineConnection (gobject.GObject):

    __gsignals__ = {
        'hungup': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
    }

    def __init__(self, executable):
        gobject.GObject.__init__(self)
        self.pid, self.fd = os.forkpty()
        if self.pid == CHILD:
            os.nice(15)
            environ = {}
            if "PYTHONPATH" in os.environ:
                environ["PYTHONPATH"] = os.path.abspath(os.environ["PYTHONPATH"])
            os.execve(executable, [""], environ)
        
        self.defname = os.path.split(executable)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        
        # This can be done smarter, when an enginepool is written
        #chars = [(ord("a"), ord("z")), (ord("A"), ord("Z"))]
        #self.defname  = self.defname+"#"+chr(randint(*choice(chars)))
        
        log.debug(executable+"\n", self.defname)
        
        self.buffer = ""
        gobject.io_add_watch(self.fd, gobject.IO_HUP, self.recieved)

    def recieved (self, fd, condition):
        log.warn("hungup\n", self.defname)
        self.emit("hungup")
        return False
        
    def readline (self, timeout=-1):
    	if timeout < 0:
    		timeout = time()+600
    	
        i = self.buffer.find("\n")
        if i >= 0:
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line:
                log.debug(line+"\n", self.defname)
                return line
            
        while True:
            while True:
                try:
                    t = timeout-time()
                    if t < 0: t = 0
                    rlist, _, _ = select.select([self.fd], [], [], t)
                except select.error, error: 
                    if error.args[0] == 4: #Interupt
                        continue
                    raise
                break
                
            if not rlist:
                # We have reached timeout
                return None
            
            try:
                data = os.read(self.fd, rlist[0])
                #print repr(data)
            except OSError, error:
                if error.errno in (5, 9): # ioerrro, file-descriptor error
                    return None
                else: raise
            
            self.buffer += data.replace("\r\n","\n").replace("\r","\n")
            #print repr(self.buffer)
            i = self.buffer.find("\n")
            if i < 0: continue
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line:
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
