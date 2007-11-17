
from threading import RLock
from gobject import *

types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\-]{1,4})"
names = "(\w+)(?:\((\w+)\))?"
mf = "(?:([mf]{1,2})\s?)?"

class FingerManager (GObject):
    
    __gsignals__ = {
        'fingeringFinished' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object, str, object)),
        'ratingAdjusted' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, str)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        
        self.connection.expect_fromto (self.onFinger,
                "Finger of %s:" % names,
                "Timeseal +: +(On|Off)")
        
        # We don't use this. Rather we use BoardManagers "gameEnded", after
        # which we do a refinger. This is to ensure not only rating, but also
        # wins/looses/draws are updated
        #self.connection.expect(self.onRatingAdjust,
        #        "%s rating adjustment: (\d+) --> (\d+)" % types
        # Notice if you uncomment this: The expression has to be compiled with
        # re.IGNORECASE, or the first letter of 'type' must be capital
    
    def onFinger (self, matchlist):
        name, title = matchlist[0].groups()
        timeseal = matchlist[-1].groups()[0]
        
        email = ""
        ratings = {}
        timeonline = ""
        for line in [l for l in matchlist[1:-1] if l]:
            parts = [p for p in line.split(" ") if p]
            
            if parts[0] in ("Blitz", "Lightning", "Standard"):
                ratings[parts[0]] = parts[1:]
            
            elif parts[0] == "Email":
                email = parts[-1]
            
            elif parts[:3] == ["Total", "time", "online:"]:
                timeonline = " ".join(parts[3:])
            
            # Use this to get a "Member since" value
            # % of life online:  0.1  (since Sat Feb 21, 10:29 PST 2004)
            # elif parts[:4] == ["%", "of", "life", "online"]:
        
        self.emit ("fingeringFinished", ratings, email, timeonline)
    
    def onRatingAdjust (self, match):
        # Notice: This is only recived for us, not for other persons we finger
        type, old, new = match.groups()
        self.emit("ratingAdjusted", type, new)
    
    def finger (self, user):
        print >> self.connection.client, "finger %s /sbl r" % user
