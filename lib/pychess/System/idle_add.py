from functools import wraps
from threading import currentThread

from gi.repository import GLib

from pychess.System.Log import log
from pychess.System import fident

debug = False

def idle_add (f):
    @wraps(f)
    def new_func (*args):
        thread = currentThread()
        if debug:
            msg = '%s(%s)' % (fident(f), ','.join([str(a) for a in args]))
            log.debug(msg, extra={'task': (thread.ident, thread.name, 'idle_add.new_func')})
        if thread.name == "MainThread":
            f(*args)
        else:
            GLib.idle_add(f, *args)
    return new_func
