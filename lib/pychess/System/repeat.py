# -*- coding: UTF-8 -*-
from pychess.System.ThreadPool import pool
def repeat (func, *args, **kwargs):
    """ Repeats a function in a new thread until it returns False """
    def run ():
        while func(*args, **kwargs):
            pass
    pool.start(run)
