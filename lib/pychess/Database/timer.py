#!/usr/bin/env python
#
# Python Timer Class - Context Manager for Timing Code Blocks
# Corey Goldberg - 2012
#


from __future__ import print_function
from timeit import default_timer


class Timer(object):
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.timer = default_timer
        
    def __enter__(self):
        self.start = self.timer()
        return self
        
    def __exit__(self, *args):
        end = self.timer()
        self.elapsed_secs = end - self.start
        self.elapsed = self.elapsed_secs * 1000 # millisecs
        if self.verbose:
            print('elapsed time: %f ms' % self.elapsed)



if __name__ == '__main__':
    # example:
    # 'HTTP GET' from requests module, inside timer blocks.
    # invoke the Timer context manager using the `with` statement.
    
    import requests
    
    url = 'https://github.com/timeline.json'
    
    # verbose (auto) timer output
    with Timer(verbose=True):
        r = requests.get(url)
    
    # print stored elapsed time in milliseconds
    with Timer() as t:
        r = requests.get(url)
    print('response time (millisecs): %.2f' % t.elapsed)
    
    # print stored elapsed time in seconds
    with Timer() as t:
        r = requests.get(url)
    print('response time (secs): %.3f' % t.elapsed_secs)


# example output:
#
# $ python timer.py
# elapsed time: 652.403831 ms
# response time (millisecs): 635.49
# response time (secs): 0.624
