from threading import Thread
import Queue

from gobject import GObject, SIGNAL_RUN_FIRST
from ThreadPool import PooledThread

import glock

import time

#
# IDEA: We could implement gdk prioritizing by using a global PriorityQueue
#

class Publisher (PooledThread):
    """ Publisher can be used when a thread is often spitting out results,
        and you want to process these results in gtk as soon as possible.
        While waiting for gdk access, results will be stored, and depending on
        the send policy, either the entire list, or only the last item will be
        sent as an argument to the function specified in the __init__ """
    
    SEND_LIST, SEND_LAST = range(2)
    
    def __init__ (self, func, sendPolicy):
        self.queue = Queue.Queue()
        
        self.func = func
        self.sendPolicy = sendPolicy
    
    def run (self):
        while True:
            v = self.queue.get()
            if v == None:
                break
            glock.acquire()
            try:
                l = [v]
                while True:
                    try:
                        v = self.queue.get_nowait()
                    except Queue.Empty:
                        break
                    else: l.append(v)
                
                if self.sendPolicy == self.SEND_LIST:
                    self.func(l)
                elif self.sendPolicy == self.SEND_LAST:
                    self.func(l[-1])
            finally:
                glock.release()
    
    def put (self, task):
        self.queue.put(task)
    
    def __del__ (self):
        self.queue.put(None)

class EmitPublisher (Publisher):
    """ EmitPublisher is a version of Publisher made for the common task of
        emitting a signal after waiting for the gdklock """
    def __init__ (self, parrent, signal, sendPolicy):
        Publisher.__init__(self, lambda v: parrent.emit(signal, v), sendPolicy)

class GtkWorker (GObject, Thread):
    
    __gsignals__ = {
        "progressed": (SIGNAL_RUN_FIRST, None, (float,)),
        "published":  (SIGNAL_RUN_FIRST, None, (object,)),
        "done":       (SIGNAL_RUN_FIRST, None, (object,))
    }
    
    def __init__ (self, func):
        """ Initialize a new GtkWorker around a specific function """
        GObject.__init__(self)
        Thread.__init__(self)
        
        # By some reason we cannot access __gsignals__, so we have to do a
        # little double work here
        self.connections = {"progressed": 0, "published": 0, "done": 0}
        self.handler_ids = {}
        
        self.func = func
        self.cancelled = False
        self.done = False
        self.progress = 0
        
        ########################################################################
        # Publish and progress queues                                          #
        ########################################################################
        
        self.publisher = EmitPublisher (self, "published", Publisher.SEND_LIST)
        self.publisher.start()
        
        self.progressor = EmitPublisher (self, "progressed", Publisher.SEND_LAST)
        self.progressor.start()
    
    ############################################################################
    # We override the connect/disconnect methods in order to count the number  #
    # of clients connected to each signal.                                     #
    # This is done for performance reasons, as some work can be skipped, if no #
    # clients are connected anyways                                            #
    ############################################################################
    
    def _mul_connect (self, method, signal, handler, *args):
        self.connections[signal] += 1
        handler_id = method (self, signal, handler, *args)
        self.handler_ids[handler_id] = signal
        return handler_id
    
    def connect (self, detailed_signal, handler, *args):
        return self._mul_connect (GObject.connect,
                detailed_signal, handler, *args)
    def connect_after (self, detailed_signal, handler, *args):
        return self._mul_connect (GObject.connect_after,
                detailed_signal, handler, *args)
    def connect_object (self, detailed_signal, handler, gobject, *args):
        return self._mul_connect (GObject.connect_object,
                detailed_signal, handler, gobject, *args)
    def connect_object_after (self, detailed_signal, handler, gobject, *args):
        return self._mul_connect (GObject.connect,
                detailed_signal, handler, gobject, *args)
    
    def disconnect (self, handler_id):
        self.connections[self.handler_ids[handler_id]] -= 1
        del self.handler_ids[handler_id]
        return GObject.disconnect(self, handler_id)
    handler_disconnect = disconnect
    
    ############################################################################
    # The following methods (besides run()) are used to interact with the      #
    # worker                                                                   #
    ############################################################################
    
    def get (self, timeout=None):
        """ 'get' will block until the processed function returns, timeout
            happens, or the work is cancelled.
            You can test if you were cancelled by the isCancelled() method, and
            you can test if you reached the timeout by the isAlive() method.
            Notice, cancelling will not make 'get' unblock, besides if you build
            'isCancelled' calls into your function.
            
            Warning: the get function assumes that if you are the MainThread you
            have the gdklock and if you are not the MainThread you don't have
            the gdklock.
            If this is not true, and the work is not done, calling get will
            result in a deadlock.
            If you haven't used the gtk.gdk.threads_enter nor
            gtk.gdk.threads_leave function, everything should be fine."""
        
        if not self.isDone():
            glock.release()
            self.join(timeout)
            glock.acquire()
            if self.isAlive():
                return None
            self.done = True
        return self.result
    
    def execute (self):
        """ Start the worker """
        if not self.isDone():
            self.start()
    
    def run (self):
        self.result = self.func(self)
        self.done = True
        if self.connections["done"] >= 1:
            glock.acquire()
            try:
                # In python 2.5 we can use self.publishQueue.join() to wait for
                # all publish items to have been processed.
                self.emit("done", self.result)
            finally:
                glock.release()
    
    def cancel (self):
        """ Cancel work.
            As python has no way of trying to interupt a thread, we don't try
            to do so. The cancelled attribute is simply set to true, which means
            that no more signals are emitted.
            You can build 'isCancelled' calls into your function, to help it
            exit when it doesn't need to run anymore.
            while not worker.isCancelled():
                ...
            """
        self.cancelled = True
        self.publisher.__del__()
        self.progressor.__del__()
    
    ############################################################################
    # Get stuf                                                                 #
    ############################################################################
    
    def isCancelled (self):
        return self.cancelled
    
    def isDone (self):
        return self.done
    
    def getProgress (self):
        return self.progress
    
    ############################################################################
    # These methods are used by the function to indicate progress and publish  #
    # process                                                                  #
    ############################################################################
    
    def setProgress (self, progress):
        """ setProgress should be called from inside the processed function.
            When the gdklock gets ready, it will emit the "progressed" signal,
            with the value of the latest setProgress call """
        if self.isCancelled():
            return
        if self.progress != progress:
            self.progress = progress
            self.progressor.put(progress)
    
    def publish (self, val):
        """ Publish should be called from inside the processed function. It will
            queue up the latest results, and when we get access to the gdklock,
            it will emit the "published" signal. """
        if self.connections["published"] < 1 or self.isCancelled():
            return
        self.publisher.put(val)
    
    ############################################################################
    # Other                                                                    #
    ############################################################################
    
    def __del__ (self):
        self.cancel()

################################################################################
# Demo usage                                                                   #
################################################################################

if __name__ == "__main__":
    def findPrimes (worker):
        from math import sqrt
        limit = 10**4.
        primes = []
        for n in xrange(2, int(limit)+1):
            for p in primes:
                if worker.isCancelled():
                    return primes
                if p > n**2:
                    break
                if n % p == 0:
                    break
            else:
                primes.append(n)
                worker.publish(n)
            worker.setProgress(n/limit)
        return primes
    
    import gtk
    w = gtk.Window()
    vbox = gtk.VBox()
    w.add(vbox)
    
    worker = GtkWorker(findPrimes)
    
    sbut = gtk.Button("Start")
    def callback (button, *args):
        sbut.set_sensitive(False)
        worker.execute()
    sbut.connect("clicked", callback)
    vbox.add(sbut)
    
    cbut = gtk.Button("Cancel")
    def callback (button, *args):
        cbut.set_sensitive(False)
        worker.cancel()
    cbut.connect("clicked", callback)
    vbox.add(cbut)
    
    gbut = gtk.Button("Get")
    def callback (button, *args):
        gbut.set_sensitive(False)
        print "Found:", worker.get()
    gbut.connect("clicked", callback)
    vbox.add(gbut)
    
    prog = gtk.ProgressBar()
    def callback (worker, progress):
        prog.set_fraction(progress)
    worker.connect("progressed", callback)
    vbox.add(prog)
    
    field = gtk.Entry()
    def process (worker, primes):
        field.set_text(str(primes[-1]))
    worker.connect("published", process)
    vbox.add(field)
    
    def done (worker, result):
        print "Finished, Cancelled:", worker.isCancelled()
    worker.connect("done", done)
    
    w.connect("destroy", gtk.main_quit)
    w.show_all()
    gtk.gdk.threads_init()
    gtk.main()
