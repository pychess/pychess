
import os, select, signal, errno, termios
from select import POLLIN, POLLPRI, POLLOUT, POLLERR, POLLHUP, POLLNVAL
from termios import tcgetattr, tcsetattr
from random import randint, choice

from pychess.System.Log import log

pollErrDic = {
    POLLIN: "There is data to read",
    POLLPRI: "There is urgent data to read",
    POLLOUT: "Ready for output: writing will not block",
    POLLERR: "Error condition of some sort",
    POLLHUP: "Hung up",
    POLLNVAL: "Invalid request: descriptor not open",
}

ERRORS = POLLERR | POLLHUP | POLLNVAL

CHILD = 0

class SubProcessError (Exception): pass
class TimeOutError (Exception): pass

def searchPath (file):
    for dir in os.environ["PATH"].split(":"):
        path = os.path.join(dir, file)
        if os.path.isfile(path):
            return path

class SubProcess:
    """ Pty based communication wrapper """
    
    def __init__(self, path, args=[], env=None, warnwords=[]):
        self.path = path
        self.args = args
        
        self.defname = os.path.split(path)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        log.debug(path+"\n", self.defname)
        
        self.pid, self.fd = os.forkpty()
        if self.pid == CHILD:
            os.nice(15)
            print "path", path, "args", args
            if env == None:
                env = os.environ
            os.execve(path, [path]+args, env)
            os._exit(-1)
        
        # Stop our commands being echoed back
        iflag, oflag, cflag, lflag, ispeed, ospeed, cc = tcgetattr(self.fd)
        lflag &= ~termios.ECHO
        tcsetattr(self.fd, termios.TCSANOW,
        		[iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        
        self.buffer = ""
        
        self.poll = select.poll()
        self.poll.register(self.fd,
            POLLIN | POLLPRI | POLLERR | POLLHUP | POLLNVAL)
        
        self.warnwords = warnwords
        
    def readline (self, timeout=None):
    	
        i = self.buffer.find("\n")
        if i >= 0:
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line:
                log.debug(line+"\n", self.defname)
                return line
        
        while True:
            try:
                readies = self.poll.poll(timeout)
            except select.error, e:
                if e[0] == errno.EINTR:
                    continue
                raise
            
            if not readies:
                raise TimeOutError, "Reached %d milisec timeout" % timeout
            
            fd, event = readies[0]
            if event & ERRORS:
                errors = []
                if event & POLLERR:
                    errors.append("Error condition of some sort")
                if event & POLLHUP:
                    errors.append("Hung up")
                if event & POLLNVAL:
                    errors.append("Invalid request: descriptor not open")
                raise SubProcessError (event, errors)
            
            data = os.read(self.fd, 1024)
            self.buffer += data.replace("\r\n","\n").replace("\r","\n")
            
            i = self.buffer.find("\n")
            if i < 0: continue
            
            line = self.buffer[:i]
            self.buffer = self.buffer[i+1:]
            if line:
                if self.warnwords:
                    lline = line.lower()
                    for word in self.warnwords:
                        if word in lline:
                            log.warn(line+"\n", self.defname)
                            break
                    else:
                        log.debug(line+"\n", self.defname)
                return line
    
    def write (self, data):
        log.log(data, self.defname)
        os.write(self.fd, data)
    
    def wait4exit (self):
        try:
            pid, code = os.waitpid(self.pid, 0)
            log.debug(os.strerror(code)+"\n", self.defname)
        except OSError, error:
            if error.errno == errno.ECHILD:
                #No child processes
                pass
            else: raise OSError, error
    
    def sendSignal (self, sign, doclose):
        try:
            os.kill(self.pid, sign)
            if doclose:
                os.close(self.fd)
        except OSError, error:
            if error.errno == errno.ESRCH:
                #No such process
                pass
            else: raise OSError, error
    
    def sigkill (self):
        self.sendSignal(signal.SIGKILL, True)
    
    def sigterm (self):
        self.sendSignal(signal.SIGTERM, True)
    
    def sigint (self):
        self.sendSignal(signal.SIGINT, False)
