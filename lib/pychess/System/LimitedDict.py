""" This is a dictionary, that supports a max of items.
    This is good for the transportation table, as some old entries might not
    be useable any more, as the position has totally changed """

from UserDict import UserDict
from threading import Lock

class LimitedDict (UserDict):
    def __init__ (self, maxSize):
        UserDict.__init__(self)
        assert maxSize > 0
        self.maxSize = maxSize
        self.krono = []
        self.lock = Lock()
        
    def __setitem__ (self, key, item):
        self.lock.acquire()
        try:
            if not key in self:
                if len(self) >= self.maxSize:
                    try:
                        del self[self.krono[0]]
                    except KeyError: pass # Overwritten
                    del self.krono[0]
            self.data[key] = item
            self.krono.append(key)
        finally:
            self.lock.release()
