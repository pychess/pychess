import sys
from cStringIO import *
import traceback
import tempfile
import os
import logging
import threading
from os.path import basename
from pychess.Utils.const import *

LOGGER = logging.getLogger(__name__)

def bug_buddy_exception(type, value, tb):
    # Shamelessly stolen from /gnome-python/examples/bug-buddy-integration.py
    # Original credit to Fernando Herrera
    msg = "".join(traceback.format_exception(type, value, tb))
    fd, name = tempfile.mkstemp()
    try:
        os.write(fd,msg)
        os.system("bug-buddy --include=\"%s\" --appname=\"%s\"" % (name, (NAME+' '+VERSION_NAME+' '+VERSION)))
    finally:
        os.unlink(name)

_exception_in_progress = 0
def _info(type, value, tb):
    global _exception_in_progress
    if _exception_in_progress:
        _excepthook_save(type, value, tb)
        return
    _exception_in_progress = 1
   
    bug_buddy_exception(type, value, tb)
    
    _exception_in_progress = 0

def install_thread_excepthook():
    """
    Workaround for sys.excepthook thread bug
    (https://sourceforge.net/tracker/?func=detail&atid=105470&aid=1230540&group_id=5470).
    Call once from __main__ before creating any threads.
    If using psyco, call psyco.cannotcompile(threading.Thread.run)
    since this replaces a new-style class method.
    """
    run_old = threading.Thread.run
    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            type, value, tb = sys.exc_info()
            stack = traceback.extract_tb(tb)
            display_bug_buddy = True
            for (filename, line_number, function_name, text) in stack:
                # Display bug buddy
                sys.excepthook(type, value, tb)
            else:
                # Display normal stack trace
                _excepthook_save(type, value, tb)
    threading.Thread.run = run

_excepthook_save = sys.excepthook
sys.excepthook = _info
install_thread_excepthook()
