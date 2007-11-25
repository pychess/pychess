from Queue import Queue
import os, sys, select, signal, errno, atexit, time
from threading import currentThread, RLock, Condition
from random import randint, choice
import subprocess, glock

if sys.platform != "win32":
    import pty
    import termios
    from termios import tcgetattr, tcsetattr
    from select import POLLIN, POLLPRI, POLLOUT, POLLERR, POLLHUP, POLLNVAL

    pollErrDic = {
        POLLIN: "There is data to read",
        POLLPRI: "There is urgent data to read",
        POLLOUT: "Ready for output: writing will not block",
        POLLERR: "Error condition of some sort",
        POLLHUP: "Hung up",
        POLLNVAL: "Invalid request: descriptor not open",
    }

    ERRORS = POLLERR | POLLHUP | POLLNVAL

from pychess.Utils.const import *

from Log import log

CHILD = 0

class SubProcessError (Exception): pass
class TimeOutError (Exception): pass

def searchPath (file):
    for dir in os.environ["PATH"].split(":"):
        path = os.path.join(dir, file)
        if os.path.isfile(path):
            return path



class SubProcessesPool:
    def __init__ (self):
        # TODO: no poll on win32...
        self.poll = select.poll()
        self.buffers = {}
        self.names = {}
        self.error = {}
        self.warnwords = {}
        self.newDataCondition = {}
        self.rlock = RLock()
    
    def addDescriptor (self, fd, defname, warnwords):
        self.buffers[fd] = ""
        self.names[fd] = defname
        self.warnwords[fd] = warnwords
        self.newDataCondition[fd] = Condition()
        self.poll.register(fd, POLLIN | POLLPRI | POLLERR | POLLHUP | POLLNVAL)
    
    def _handleBuffer (self, fd):
        i = self.buffers[fd].find("\n")
        if i >= 0:
            line = self.buffers[fd][:i]
            self.buffers[fd] = self.buffers[fd][i+1:]
            lline = line.lower()
            for word in self.warnwords[fd]:
                if word in lline:
                    log.warn(line+"\n", self.names[fd])
                    break
            else:
                log.debug(line+"\n", self.names[fd])
            return line
        
        elif fd in self.error:
            raise self.error[fd]
    
    def readline (self, fd, timeout=None):
        l = self._handleBuffer(fd)
        if l != None: return l
        
        while not self.rlock.acquire(blocking=False):
            self.newDataCondition[fd].acquire()
            self.newDataCondition[fd].wait()
            self.newDataCondition[fd].release()
            
            l = self._handleBuffer(fd)
            if l != None: return l
        
        try:
            while True:
                try:
                    readies = self.poll.poll(timeout)
                except select.error, e:
                    if e[0] == errno.EINTR:
                        continue
                    raise
                
                if not readies:
                    raise TimeOutError, "Reached %d milisec timeout" % timeout
                
                for someFd, event in readies:
                    if event & ERRORS:
                        errors = []
                        if event & POLLERR:
                            errors.append("Error condition of some sort")
                        if event & POLLHUP:
                            errors.append("Hung up")
                        if event & POLLNVAL:
                            errors.append("Descriptor not open")
                        self.error[someFd] = SubProcessError (event, errors)
                        self.poll.unregister(someFd)
                    else:
                        data = os.read(someFd, 4096)
                        data = data.replace("\r\n","\n").replace("\r","\n")
                        self.buffers[someFd] += data
                    if someFd != fd:
                        self.newDataCondition[someFd].acquire()
                        self.newDataCondition[someFd].notify()
                        self.newDataCondition[someFd].release()
                
                if "\n" in self.buffers[fd] or fd in self.error:
                    return self._handleBuffer(fd)
        finally:
            self.rlock.release()
            for cond in self.newDataCondition.values():
                cond.acquire()
                cond.notify()
                cond.release()

pool = SubProcessesPool()

class SubProcess:
    """ Pty based communication wrapper """
    
    def __init__(self, path, args=[], warnwords=[], type=SUBPROCESS_SUBPROCESS, env=None):
        self.path = path
        self.args = args
        self.env = env or os.environ
        self.warnwords = warnwords
        
        self.defname = os.path.split(path)[1]
        self.defname = self.defname[:1].upper() + self.defname[1:].lower()
        log.debug(path+"\n", self.defname)
        
        self.priority = 15
        
        if type == SUBPROCESS_PTY:
            self.initPty()
        elif type == SUBPROCESS_SUBPROCESS:
            self.initSub()
        elif type == SUBPROCESS_FORK:
            self.initGlc()
        
        pool.addDescriptor(self.fdin, self.defname, self.warnwords)
    
    def initPty (self):
        """ Init the subprocess using a pty """
        
        self.pid, fd = pty.fork()
        if self.pid == CHILD:
            os.nice(self.priority)
            print "path", self.path, "args", self.args
            os.execve(self.path, [self.path]+self.args, self.env)
            os._exit(-1)
        
        # Stop our commands being echoed back
        iflag, oflag, cflag, lflag, ispeed, ospeed, cc = tcgetattr(fd)
        lflag &= ~termios.ECHO
        tcsetattr(fd, termios.TCSANOW,
                [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
        
        self.fdin = fd
        self.fdout = fd
    
    def initSub (self):
        """ Init the subprocess using the python subprocess module """
        
        # The subprocess module is not very stable inside threads
        assert currentThread().getName() == "MainThread"
        
        p = subprocess.Popen([self.path]+self.args,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.fdout = p.stdin.fileno()
        self.fdin = p.stdout.fileno()
        
        self.pid = p.pid
        os.system("renice %d -p %d" % (self.priority, self.pid))
        # Using this subprocess call, which would save us from output to stdout,
        # but it seams that there are some raceconditions on using too many
        # subprocess calls in a row
        #subprocess.call("/usr/bin/renice %d -p %d" % (self.priority, self.pid))
        atexit.register(self.sigkill)
    
    def initGlc (self):
        """ Init the subprocess using fork the same way as glchess """
        
        # Pipe to communicate to engine with
        toManagerPipe = os.pipe()
        fromManagerPipe = os.pipe()
        
        # Store the file descripter for reading/writing
        self.fdout = toManagerPipe[1]
        self.fdin = fromManagerPipe[0]
        
        # Fork off a child process to manage the engine
        self.pid = os.fork()
        if self.pid == 0:
            # ..
            os.close(toManagerPipe[1])
            os.close(fromManagerPipe[0])
            
            # Make pipes to the engine
            stdinPipe = os.pipe()
            stdoutPipe = os.pipe()
            stderrPipe = os.pipe()
            
            # Fork off the engine
            engineFd = os.fork()
            if engineFd == 0:
                # Make the engine low priority for CPU usage
                os.nice(self.priority)
                
                # Connect stdin, stdout and stderr to the manager process
                os.dup2(stdinPipe[0], sys.stdin.fileno())
                os.dup2(stdoutPipe[1], sys.stdout.fileno())
                os.dup2(stderrPipe[1], sys.stderr.fileno())
                
                # Execute the engine
                try:
                    os.execve(self.path, [self.path] + self.args, self.env)
                except OSError:
                    pass
                os._exit(0)
                
            # Catch if the child dies
            def childDied(sig, stackFrame):
                try:
                    os.waitpid(-1, os.WNOHANG)
                except OSError:
                    return
                
                # Close connection to the application
                os.close(fromManagerPipe[1])
                    
                os._exit(0)
            signal.signal(signal.SIGCHLD, childDied)
            
            # Forward data between the application and the engine and wait for closed pipes
            inputPipes = [toManagerPipe[0], stdoutPipe[0], stderrPipe[0]]
            pipes = [toManagerPipe[0], toManagerPipe[1], stdinPipe[0], stdinPipe[1], stdoutPipe[0], stdoutPipe[1], stderrPipe[0], stderrPipe[1]]
            while True:                
                # Wait for data
                (rfds, _, xfds) = select.select(inputPipes, [], pipes, None)
                
                for fd in rfds:
                    data = os.read(fd, 65535)
                    
                    # One of the connections has closed - kill the engine and quit
                    if len(data) == 0:
                        os.kill(engineFd, signal.SIGQUIT)
                        os._exit(0)
                    
                    # Send data from the application to the engines stdin
                    if fd == toManagerPipe[0]:
                        os.write(stdinPipe[1], data)
                    # Send engine output to the application
                    else:
                        os.write(fromManagerPipe[1], data)
            
            os._exit(0)
        
        os.close(toManagerPipe[0])
        os.close(fromManagerPipe[1])
        atexit.register(self.sigkill)
    
    def readline (self, timeout=None):
        return pool.readline(self.fdin, timeout)
    
    def write (self, data):
        try:
            log.log(data, self.defname)
            os.write(self.fdout, data)
        except OSError, e:
            # Ignore hung up error, as we are going to find out about the death
            # in other ways
            if e.errno != 32:
                raise
    
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
                #No child processes
                return (0, os.strerror(0))
            else: raise OSError, error
        
        return (None, None)
    
    def sendSignal (self, sign, doclose):
        try:
            os.kill(self.pid, sign)
            #if doclose:
            #    os.close(self.fdout)
            #    os.close(self.fdin)
        except OSError, error:
            if error.errno == errno.ESRCH:
                #No such process
                pass
            else: raise OSError, error
    
    def gentleKill (self, first=0.5, second=0.25):
        code, string = self.wait4exit(timeout=first)
        if code == None:
            self.sigterm()
            code, string = self.wait4exit(timeout=second)
            if code == None:
                self.sigkill()
                return self.wait4exit()[0]
            return code
        return code
    
    def sigkill (self):
        self.sendSignal(signal.SIGKILL, True)
    
    def sigterm (self):
        self.sendSignal(signal.SIGTERM, True)
    
    def sigint (self):
        self.sendSignal(signal.SIGINT, False)

if __name__ == "__main__":
    paths = ("igang.dk", "google.com", "google.dk", "ahle.dk", "myspace.com", "yahoo.com")
    maxlen = max(len(p) for p in paths)
    ps = [(SubProcess("/bin/ping", [path]), path) for path in paths]
    for i in xrange(10):
        for subprocess, path in ps:
            print i, "\t", path.ljust(maxlen), subprocess.readline()
