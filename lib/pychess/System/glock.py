import sys, traceback
from threading import RLock, currentThread
from gtk.gdk import threads_enter, threads_leave
import time
from pychess.System.prefix import addUserDataPrefix
#logfile = open(addUserDataPrefix(time.strftime("%Y-%m-%d_%H-%M-%S") + "-glocks.log"), "w")
debug = False
debug_stream = sys.stdout
gdklocks = {}
_rlock = RLock()

def has():
    me = currentThread()
    if type(_rlock._RLock__owner) == int:
        return _rlock._RLock__owner == me._Thread__ident
    return _rlock._RLock__owner == me

def acquire():
    me = currentThread()
    t = time.strftime("%H:%M:%S")
    if me.ident not in gdklocks:
        gdklocks[me.ident] = 0
    # Ensure we don't deadlock if another thread is waiting on threads_enter
    # while we wait on _rlock.acquire()
    if me.getName() == "MainThread" and not has():
        if debug:
            print >> debug_stream, "%s %s: %s: glock.acquire: ---> threads_leave()" % (t, me.ident, me.name)
        threads_leave()
        gdklocks[me.ident] -= 1
        if debug:
            print >> debug_stream, "%s %s: %s: glock.acquire: <--- threads_leave()" % (t, me.ident, me.name)
    # Acquire the lock, if it is not ours, or add one to the recursive counter
    if debug:
        print >> debug_stream, "%s %s: %s: glock.acquire: ---> _rlock.acquire()" % (t, me.ident, me.name)
    _rlock.acquire()
    if debug:
        print >> debug_stream, "%s %s: %s: glock.acquire: <--- _rlock.acquire()" % (t, me.ident, me.name)
    # If it is the first time we lock, we will acquire the gdklock
    if _rlock._RLock__count == 1:
        if debug:
            print >> debug_stream, "%s %s: %s: glock.acquire: ---> threads_enter()" % (t, me.ident, me.name)
        threads_enter()
        gdklocks[me.ident] += 1
        if debug:
            print >> debug_stream, "%s %s: %s: glock.acquire: <--- threads_enter()" % (t, me.ident, me.name)

def release():
    me = currentThread()
    t = time.strftime("%H:%M:%S")
    # As it is the natural state for the MainThread to control the gdklock, we
    # only release it if _rlock has been released so many times that we don't
    # own it any more
    if me.getName() == "MainThread":
        if not has():
            if debug:
                print >> debug_stream, "%s %s: %s: glock.release: ---> threads_leave()" % (t, me.ident, me.name)
            threads_leave()
            gdklocks[me.ident] -= 1
            if debug:
                print >> debug_stream, "%s %s: %s: glock.release: <--- threads_leave()" % (t, me.ident, me.name)
        else:
            if debug:
                print >> debug_stream, "%s %s: %s: glock.release: ---> _rlock.release()" % (t, me.ident, me.name)
            _rlock.release()
            if debug:
                print >> debug_stream, "%s %s: %s: glock.release: <--- _rlock.release()" % (t, me.ident, me.name)
    # If this is the last unlock, we also free the gdklock.
    elif has():
        if _rlock._RLock__count == 1:
            if debug:
                print >> debug_stream, "%s %s: %s: glock.release: ---> threads_leave()" % (t, me.ident, me.name)
            threads_leave()
            gdklocks[me.ident] -= 1
            if debug:
                print >> debug_stream, "%s %s: %s: glock.release: <--- threads_leave()" % (t, me.ident, me.name)
        if debug:
            print >> debug_stream, "%s %s: %s: glock.release: ---> _rlock.release()" % (t, me.ident, me.name)
        _rlock.release()
        if debug:
            print >> debug_stream, "%s %s: %s: glock.release: <--- _rlock.release()" % (t, me.ident, me.name)
    else:
        print "%s %s: %s: Warning: Tried to release unowned glock\nTraceback was: %s" % \
            (t, me.ident, me.name, traceback.extract_stack())

def glock_connect(emitter, signal, function, *args, **kwargs):
    def handler(emitter, *extra):
        acquire()
        try:
            function(emitter, *extra)
        finally:
            release()
        return False
    if "after" in kwargs and kwargs["after"]:
        return emitter.connect_after(signal, handler, *args)
    return emitter.connect(signal, handler, *args)

def glock_connect_after(emitter, signal, function, *args):
    return glock_connect(emitter, signal, function, after=True, *args)

def glocked(f):
    def newFunction(*args, **kw):
        acquire()
        try:
            return f(*args, **kw)
        finally:
            release()
    return newFunction

if __name__ == "__main__":
    from threading import Thread
    def do ():
        acquire()
        acquire()
        release()
        print _rlock._RLock__owner
        print currentThread()
        release()
        print _rlock._RLock__owner
    t = Thread(target=do)
    t.start()
    t.join()
