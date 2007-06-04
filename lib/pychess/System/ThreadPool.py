""" This is a pool for reusing threads """

from threading import Condition, Lock
from threading import Thread
from Log import log
import Queue

maxThreads = 50

class ThreadPool:
    def __init__ (self):
        self.queue = Queue.Queue()
        self.lock = Lock()
        self.threads = 0
    
    def start (self, func, *args):
        self.lock.acquire()
        
        try:
            a = self.queue.get_nowait()
        except Queue.Empty:
            if self.threads < maxThreads:
                self.threads += 1
                a = self.Worker(self.queue)
                a.setDaemon(True)
                a.start()
            else:
                a = self.queue.get()
        
        a.func = lambda: func(*args)
        a.wcond.acquire()
        a.wcond.notify()
        a.wcond.release()
        
        self.lock.release()
    
    class Worker (Thread):
        def __init__ (self, queue):
            Thread.__init__(self)
            self.func = None
            self.wcond = Condition()
            self.queue = queue
        
        def run (self):
            while True:
                if self.func:
                    self.func()
                    self.func = None
                    self.queue.put(self)
                self.wcond.acquire()
                self.wcond.wait()

pool = ThreadPool()
