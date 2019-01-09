import asyncio
import os
import sys
import pstats
import inspect
import cProfile
import ssl
import tempfile
from timeit import default_timer
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from pychess import MSYS2

# TODO: this hack only needed until we can figure out
# what ssl cert files needed to copied in setup.py
# when cx_freezee bdist_msi command is used
if MSYS2:
    ssl._create_default_https_context = ssl._create_unverified_context


@asyncio.coroutine
def download_file_async(url, progressbar=None):
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, download_file, url)
    temp_file = yield from future
    return temp_file


def download_file(url, progressbar=None):
    temp_file = None
    try:
        if progressbar is not None:
            from gi.repository import GLib
            GLib.idle_add(progressbar.set_text, "Downloading %s ..." % url)
        else:
            print("Downloading %s ..." % url)
        f = urlopen(url)

        temp_file = os.path.join(tempfile.gettempdir(), os.path.basename(url))
        with open(temp_file, "wb") as local_file:
            local_file.write(f.read())

    except HTTPError as e:
        print("HTTP Error:", e.code, url)

    except URLError as e:
        print("URL Error:", e.reason, url)

    return temp_file


def fident(f):
    '''
    Get an identifier for a function or method
    '''
    joinchar = '.'
    if hasattr(f, 'im_class'):
        fparent = f.im_class.__name__
    else:
        joinchar = ':'
        fparent = f.__module__.split('.')[-1]

    # sometimes inspect.getsourcelines() segfaults on windows
    if getattr(sys, 'frozen', False) or sys.platform == "win32":
        lineno = 0
    else:
        lineno = inspect.getsourcelines(f)[1]

    fullname = joinchar.join((fparent, f.__name__))
    return ':'.join((fullname, str(lineno)))


def get_threadname(thread_namer):
    if isinstance(thread_namer, str):
        return thread_namer
    else:
        return fident(thread_namer)


# https://gist.github.com/techtonik/2151727
def caller_name(skip=2):
    """Get a name of a caller in the format module.class.method

       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

       An empty string is returned if skipped levels exceed stack height
    """
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    # TODO(techtonik): consider using __main__
    if module:
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append(codename)   # function or a method
    del parentframe
    return ".".join(name)


def profile_me(fn):
    def profiled_fn(*args, **kwargs):
        prof = cProfile.Profile()
        ret = prof.runcall(fn, *args, **kwargs)
        ps = pstats.Stats(prof)
        ps.sort_stats('cumulative')
        ps.print_stats(60)
        return ret
    return profiled_fn


# Python Timer Class - Context Manager for Timing Code Blocks
# Corey Goldberg - 2012
class Timer:
    def __init__(self, text):
        self.text = text
        self.timer = default_timer

    def __enter__(self):
        self.start = self.timer()
        return self

    def __exit__(self, *args):
        end = self.timer()
        self.elapsed_secs = end - self.start
        self.elapsed = self.elapsed_secs * 1000  # millisecs
        print('---- elapsed time: %f ms - %s' % (self.elapsed, self.text))
