
import telnet
from gobject import *

names = "\w+(?:\([A-Z\*]+\))*"

types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "\(([0-9\ \-\+]{4})\)"

import re
matchre = re.compile ("(\w+) %s %s(\w+) %s %s %s (\d+) (\d+)" % \
        (ratings, colors, ratings,rated, types) )

#
# Known offers: abort accept adjourn draw match pause unpause switch takeback
#

class OfferManager (GObject):
    
    __gsignals__ = {
        'onOfferAdd' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,str,str)),
        'onOfferRemove' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'onChallengeAdd' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,object)),
        'onChallengeRemove' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,))
    }
    
    def __init__ (self):
        GObject.__init__(self)
        telnet.expect ( "<p(t|f)> (\d+) w=%s t=(\w+) p=(.+?)\n" % names, self.onOfferAdd)
        telnet.expect ( "<pr> (\d+)\n", self.onOfferRemove)
        self.indexType = {}
        print >> telnet.client, "iset pendinfo 1"
    
    def stop (self):
        print >> telnet.client, "iset pendinfo 0"
    
    def onOfferAdd (self, client, groups):
        tofrom, index, type, parameters = groups
        
        if tofrom == "t":
            # Atm. We don't care about offers sendt by ourselves. This can be
            # implemented later.
            return
        
        if type in ("draw", "abort", "adjourn", "takeback", "match"):
            self.indexType[index] = type
            if type == "match":
                fname, frating, col, tname, trating, rated, type, mins, incr = \
                        matchre.match(parameters).groups()
                
                rating = frating.strip()
                rating = rating.isdigit() and rating or "0"
                rated = rated == "unrated" and "u" or "r"
                match = {"tp": type, "w": fname, "rt": rating,
                         "r": rated, "t": mins, "i": incr}
                self.emit("onChallengeAdd", index, match)
            
            else:
                self.emit("onOfferAdd", index, type, parameters)
            timeout_add(50000, self.decline, index)
        
        elif type in ("switch", "pause", "unpause"):
            print >> client, "decline", index
        
        else:
            print "Warning: Unknown offer type: #", index, type, "whith" + \
                  "parameters:", parameters, ". Declining"
            print >> client, "decline", index
    
    def onOfferRemove (self, client, groups):
        index = groups[0]
        if not index in self.indexType:
            return
        if self.indexType[index] == "match":
            self.emit("onChallengeRemove", index)
        else: self.emit("onOfferRemove", index)
        del self.indexType[index]
    
    def withdraw (self, index):
        # This method is of no use, before <pt> has been implemented.
        # (See onOfferAdd)
        print >> telnet.client, "withdraw", index
    
    def accept (self, index):
        print >> telnet.client, "accept", index
        self.emit("onOfferRemove", index)
    
    def decline (self, index):
        print >> telnet.client, "decline", index
        self.emit("onOfferRemove", index)
