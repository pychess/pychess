# -*- coding: UTF-8 -*-

import time
from threading import Thread
from pychess.System import fident


def repeat(func, *args, **kwargs):
    """ Repeats a function in a new thread until it returns False """

    def run():
        while func(*args, **kwargs):
            pass

    thread = Thread(target=run, name=fident(func))
    thread.daemon = True
    thread.start()


def repeat_sleep(func, sleeptime, recur=False):
    """
    Runs func in a thread and repeats it approximately each sleeptime [s]
    until func returns False. Notice that we sleep first, then run. Not the
    other way around. If repeat_sleep is called with recur=True, each call
    will be called with the return value of last call as argument. The
    argument has to be optional, as it wont be used first time, and it has
    to be non-None.
    """

    def run():
        last = time.time()
        val = None
        while True:
            time.sleep(time.time() - last + sleeptime)
            if not time:
                # If python has been shutdown while we were sleeping, the
                # imported modules will be None
                return
            last = time.time()
            if recur and val:
                val = func(val)
            else:
                val = func()
            if not val:
                break

    thread = Thread(target=run, name=fident(func))
    thread.daemon = True
    thread.start()
