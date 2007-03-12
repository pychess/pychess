
import telnet
from gobject import *
from threading import RLock

types = "(Blitz|Lightning|Standard)"

class FingerManager (GObject):
    
    __gsignals__ = {
        'fingeringFinished' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object, str, object)),
    }
    
    def __init__ (self):
        GObject.__init__(self)
        
        self.ratings = {}
        self.email = ""
        
        self.lock = RLock()
    
    def finger (self, user):
        self.lock.acquire()
        
        telnet.expect ( "Email\s*:\s*(\w+@\w+\.\w+)", self.onEmail )
        telnet.expect ( "Total time online: (?:(\d+) day[s]?)?(?:(\d+) h[a-z\, ]*)?(?:(\d+) m[a-z\, ]*)?(?:(\d+) s[a-z]*)?", self.onTotalTimeOnline )
        telnet.expect ( "%s\s+(\d+)\s+([\d\.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)" % types, self.onRatingLine)
        
        print >> telnet.client, "finger %s /sbl r" % user
    
    def onEmail (self, client, groups):
        self.email = groups[0]
    
    def onTotalTimeOnline (self, client, groups):
        self.emit ("fingeringFinished", self.ratings, self.email, groups)
        self.ratings = {}
        self.email = ""
        telnet.unexpect (self.onEmail)
        telnet.unexpect (self.onTotalTimeOnline)
        self.lock.release()
    
    def onRatingLine (self, client, groups):
        self.ratings[groups[0]] = groups[1:]
