from threading import Condition
from threading import Thread
from System.Log import log

class ThreadPool:
    def __init__ (self):
        self.availables = []
        self.cond = Condition()
    
    def start (self, func, *args):
        self.cond.acquire()

        if not self.availables:
            a = self.Worker(self.availables)
            a.setDaemon(True)
            a.start()
        else: a = self.availables.pop()

        a.func = lambda: func(*args)
        a.wcond.acquire()
        a.wcond.notify()
        a.wcond.release()
        
        self.cond.release()
    
    class Worker (Thread):
        def __init__ (self, availables):
            Thread.__init__(self)
            self.func = None
            self.wcond = Condition()
            self.availables = availables
        
        def run (self):
            while True:
                if self.func:
                    self.func()
                    self.func = None
                    self.availables.append(self)
                self.wcond.acquire()
                self.wcond.wait()

pool = ThreadPool()
