""" This is a pool for reusing threads """

import sys, traceback, cStringIO, atexit
from threading import Condition, Lock
from threading import Thread, currentThread
import Queue

import glock

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
            
            self.running = True
            atexit.register(self.__del__)
        
        def run (self):
            try:
                while True:
                    if self.func:
                        try:
                            self.func()
                        except:
                            if glock._rlock._RLock__owner == self:
                                # As a service we take care of releasing the gdk
                                # lock when a thread breaks to avoid freezes
                                for i in xrange(_rlock._RLock__count):
                                    glock.release()
                            
                            stringio = cStringIO.StringIO()
                            traceback.print_exc(file=stringio)
                            error = stringio.getvalue()
                            print ("Thread %s in threadpool " +
                                    "raised following error:\n%s") % (self, error)
                        
                        self.func = None
                        self.queue.put(self)
                    
                    self.wcond.acquire()
                    self.wcond.wait()
            except:
                if self.running:
                    raise
        
        def __del__ (self):
            self.running = False

pool = ThreadPool()

class PooledThread:
    def start (self):
        pool.start(self.run)
    
    def run (self):
        pass
    
    def join (self):
        raise NotImplementedError
    
    def setName (self, name):
        raise NotImplementedError
    
    def getName (self):
        raise NotImplementedError
    
    def isAlive (self):
        raise NotImplementedError
    
    def isDaemon (self):
        return True
    
    def setDaemon (self):
        raise NotImplementedError
