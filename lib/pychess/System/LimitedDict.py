
from UserDict import UserDict

class LimitedDict (UserDict):
    def __init__ (self, maxSize):
        UserDict.__init__(self)
        assert maxSize > 0
        self.maxSize = maxSize
        self.krono = []
        
    def __setitem__ (self, key, item):
        if not key in self:
            if len(self) >= self.maxSize:
                del self[self.krono[0]]
                del self.krono[0]
        self.data[key] = item
        self.krono.append(key)
