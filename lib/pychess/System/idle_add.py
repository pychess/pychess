import gobject
from functools import wraps
from threading import currentThread
from pychess.System.Log import log
from pychess.System import fident
debug = False

def _debug (debug_name, msg):
    if debug:
        thread = currentThread()
        log.debug(msg, extra={'task': (thread.ident, thread.name, debug_name)})

def idle_add (f):
    @wraps(f)
    def new_func (*args):
        _debug('idle_add.new_func', '%s(%s)' % (fident(f),
                                                ','.join([str(a) for a in args])))
        gobject.idle_add(f, *args)
    return new_func
