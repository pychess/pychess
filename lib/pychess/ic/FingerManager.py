
from threading import RLock
from gobject import *

types = "(Blitz|Lightning|Standard)"

class FingerManager (GObject):
    
    __gsignals__ = {
        'fingeringFinished' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object, str, object)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        self.ratings = {}
        self.email = ""
        
        self.lock = RLock()
    
    def finger (self, user):
        self.lock.acquire()
        
        self.connection.expect ( "Email\s*:\s*(\w+@\w+\.\w+)", self.onEmail )
        self.connection.expect ( "Total time online: (?:(\d+) day[s]?)?(?:(\d+) h[a-z\, ]*)?(?:(\d+) m[a-z\, ]*)?(?:(\d+) s[a-z]*)?", self.onTotalTimeOnline )
        self.connection.expect ( "%s\s+(\d+)\s+([\d\.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)" % types, self.onRatingLine)
        
        print >> self.connection.client, "finger %s /sbl r" % user
    
    def onEmail (self, client, groups):
        self.email = groups[0]
    
    def onTotalTimeOnline (self, client, groups):
        self.emit ("fingeringFinished", self.ratings, self.email, groups)
        self.ratings = {}
        self.email = ""
        self.connection.unexpect (self.onEmail)
        self.connection.unexpect (self.onTotalTimeOnline)
        self.lock.release()
    
    def onRatingLine (self, client, groups):
        if not groups: return
        self.ratings[groups[0]] = groups[1:]
