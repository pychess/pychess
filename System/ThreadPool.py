from threading import Condition, Lock
from threading import Thread
from System.Log import log

maxThreads = 50

class ThreadPool:
    def __init__ (self):
        self.availables = []
        self.lock = Lock()
        self.cond = Condition()
        self.threads = 0
            
    def start (self, func, *args):
        self.lock.acquire()

        if not self.availables:
            if not maxThreads or self.threads < maxThreads:
                self.threads += 1
                a = self.Worker(self.availables, self.cond)
                a.setDaemon(True)
                a.start()
            else:
                self.lock.release()
                self.cond.acquire()
                while not self.availables:
                    self.cond.wait()
                self.lock.acquire()
                self.cond.release()
                a = self.availables.pop()
        else: a = self.availables.pop()

        a.func = lambda: func(*args)
        a.wcond.acquire()
        a.wcond.notify()
        a.wcond.release()
        
        self.lock.release()
    
    class Worker (Thread):
        def __init__ (self, availables, cond):
            Thread.__init__(self)
            self.func = None
            self.wcond = Condition()
            self.cond = cond
            self.availables = availables
        
        def run (self):
            while True:
                if self.func:
                    self.func()
                    self.func = None
                    self.availables.append(self)
                    self.cond.acquire()
                    self.cond.notifyAll()
                    self.cond.release()
                self.wcond.acquire()
                self.wcond.wait()

pool = ThreadPool()
