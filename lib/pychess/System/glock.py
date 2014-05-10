import traceback
from threading import RLock, currentThread
from gtk.gdk import threads_enter, threads_leave
from pychess.System.Log import log
debug = False
_rlock = RLock()

def has (thread=None):
    if not thread:
        thread = currentThread()
    if type(_rlock._RLock__owner) == int:
        return _rlock._RLock__owner == thread._Thread__ident
    return _rlock._RLock__owner == thread

def _debug (debug_name, thread, msg):
    if debug:
        log.debug(msg, extra={"task": (thread.ident, thread.name, debug_name)})

def acquire():
    me = currentThread()
    # Ensure we don't deadlock if another thread is waiting on threads_enter
    # while we wait on _rlock.acquire()
    if me.getName() == "MainThread" and not has():
        _debug(acquire.debug_name, me, '-> threads_leave')
        threads_leave()
        _debug(acquire.debug_name, me, '<- threads_leave')
    # Acquire the lock, if it is not ours, or add one to the recursive counter
    _debug(acquire.debug_name, me, '-> _rlock.acquire')
    _rlock.acquire()
    _debug(acquire.debug_name, me, '<- _rlock.acquire')
    # If it is the first time we lock, we will acquire the gdklock
    if _rlock._RLock__count == 1:
        _debug(acquire.debug_name, me, '-> threads_enter')
        threads_enter()
        _debug(acquire.debug_name, me, '<- threads_enter')
acquire.debug_name = acquire.__module__.split('.')[-1] + '.' + acquire.__name__

def release():
    me = currentThread()
    # As it is the natural state for the MainThread to control the gdklock, we
    # only release it if _rlock has been released so many times that we don't
    # own it any more
    if me.getName() == "MainThread":
        if not has():
            _debug(release.debug_name, me, '-> threads_leave')
            threads_leave()
            _debug(release.debug_name, me, '<- threads_leave')
        else:
            _debug(release.debug_name, me, '-> _rlock.release')
            _rlock.release()
            _debug(release.debug_name, me, '<- _rlock.release')
    # If this is the last unlock, we also free the gdklock.
    elif has():
        if _rlock._RLock__count == 1:
            _debug(release.debug_name, me, '-> threads_leave')
            threads_leave()
            _debug(release.debug_name, me, '<- threads_leave')
        _debug(release.debug_name, me, '-> _rlock.release')
        _rlock.release()
        _debug(release.debug_name, me, '<- _rlock.release')
    else:
        log.warning("Tried to release un-owned glock\n%s" %
                    "".join(traceback.format_stack()),
                    extra={"task": (me.ident, me.name, release.debug_name)})
release.debug_name = release.__module__.split('.')[-1] + '.' + release.__name__

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
