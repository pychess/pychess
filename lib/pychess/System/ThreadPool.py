""" This is a pool for reusing threads """

import sys as sys_
import traceback, cStringIO, atexit
import threading
from threading import Thread, currentThread, Condition, Lock
import Queue

import glock

if not hasattr(Thread, "_Thread__bootstrap_inner"):
    class SafeThread (Thread):
        def encaps(self):
            try:
                self._Thread__bootstrap_inner()
            except:
                if self.__daemonic and (sys_ is None or sys_.__doc__ is None):
                    return
                raise
    setattr(SafeThread, "_Thread__bootstrap_inner", SafeThread._Thread__bootstrap)
    setattr(SafeThread, "_Thread__bootstrap", SafeThread.encaps)
    threading.Thread = SafeThread

maxThreads = sys_.maxint

class ThreadPool:
    def __init__ (self):
        self.queue = Queue.Queue()
        self.lock = Lock()
        self.threads = 0
    
    def start (self, func, *args, **kw):
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
        
        a.func = lambda: func(*args, **kw)
        a.wcond.acquire()
        a.wcond.notify()
        a.wcond.release()
        
        self.lock.release()
    
    class Worker (threading.Thread):
        def __init__ (self, queue):
            Thread.__init__(self)
            self.func = None
            self.wcond = Condition()
            self.queue = queue
            
            self.running = True
            atexit.register(self.__del__)
            
            # We catch the trace from the thread, that created the worker
            stringio = cStringIO.StringIO()
            traceback.print_stack(file=stringio)
            self.tracestack = traceback.extract_stack()
        
        def run (self):
            try:
                while True:
                    if self.func:
                        try:
                            self.func()
                        except Exception, e:
                            #try:
                            #    if glock._rlock._RLock__owner == self:
                            #        # As a service we take care of releasing the gdk
                            #        # lock when a thread breaks to avoid freezes
                            #        for i in xrange(glock._rlock._RLock__count):
                            #            glock.release()
                            #except AssertionError, e:
                            #    print e
                            #    pass
                            
                            list = self.tracestack[:-2] + \
                                    traceback.extract_tb(sys_.exc_traceback)[2:]
                            error = "".join(traceback.format_list(list))
                            print error.rstrip()
                            print str(e.__class__), e
                        
                        self.func = None
                        self.queue.put(self)
                    
                    self.wcond.acquire()
                    self.wcond.wait()
            except:
                self.threads -= 1
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
    
    def join (self, timeout=None):
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
