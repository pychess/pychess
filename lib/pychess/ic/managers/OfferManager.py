
import re

from gobject import *

from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.System.Log import log

names = "\w+(?:\([A-Z\*]+\))*"

types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "\(([0-9\ \-\+]{4})\)"


matchre = re.compile ("(\w+) %s %s(\w+) %s %s %s (\d+) (\d+)\s*(\(adjourned\))?" % \
        (ratings, colors, ratings,rated, types) )

#
# Known offers: abort accept adjourn draw match pause unpause switch takeback
#

strToOfferType = {
    "draw": DRAW_OFFER,
    "abort": ABORT_OFFER,
    "adjourn": ADJOURN_OFFER,
    "takeback": TAKEBACK_OFFER,
    "pause": PAUSE_OFFER,
    "unpause": RESUME_OFFER,
    "switch": SWITCH_OFFER,
    "resign": RESIGNATION,
    "flag": FLAG_CALL,
    "match": MATCH_OFFER
}

offerTypeToStr = {}
for k,v in strToOfferType.iteritems():
    offerTypeToStr[v] = k

class OfferManager (GObject):
    
    __gsignals__ = {
        'onOfferAdd' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,object)),
        'onOfferRemove' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'onChallengeAdd' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,object)),
        'onChallengeRemove' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'onActionError' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,int))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect_line (self.onOfferAdd,
                "<p(t|f)> (\d+) w=%s t=(\w+) p=(.+)" % names)
        self.connection.expect_line (self.onOfferRemove, "<pr> (\d+)")
        
        for ficsstring, offer, error in (
                ("You cannot switch sides once a game is underway.", 
                        Offer(SWITCH_OFFER), ACTION_ERROR_SWITCH_UNDERWAY),
                ("Opponent is not out of time.",
                        Offer(FLAG_CALL), ACTION_ERROR_NOT_OUT_OF_TIME),
                ("The clock is not ticking yet.",
                        Offer(PAUSE_OFFER), ACTION_ERROR_CLOCK_NOT_STARTED),
                ("The clock is not ticking.",
                        Offer(FLAG_CALL), ACTION_ERROR_CLOCK_NOT_STARTED),
                ("The clock is not paused.",
                        Offer(RESUME_OFFER), ACTION_ERROR_CLOCK_NOT_PAUSED)):
            self.connection.expect_line (
                    lambda match: self.emit("onActionError", offer, error),
                    ficsstring)
        
        self.connection.expect_line (self.notEnoughMovesToUndo,
                "There are (?:(no)|only (\d+) half) moves in your game.")
        
        self.connection.expect_line (self.noOffersToAccept,
                "There are no ([^ ]+) offers to (accept).")
        
        self.lastPly = 0
        self.indexType = {}
        
        self.connection.lvm.setVariable("pendinfo", True)
    
    def noOffersToAccept (self, match):
        offerstr, type = match.groups()
        if type == "accept":
            error = ACTION_ERROR_NONE_TO_ACCEPT
        elif type == "withdraw":
            error = ACTION_ERROR_NONE_TO_WITHDRAW
        elif type == "decline":
            error = ACTION_ERROR_NONE_TO_DECLINE
        offerType = strToOfferType[offerstr]
        self.emit("onActionError", Offer(offerType), error)
    
    def notEnoughMovesToUndo (self, match):
        param = match.groups()[0] != "no" and groups[0] or 0
        offer = Offer(TAKEBACK_OFFER, self.lastPly-param)
        self.emit("onActionError", offer, ACTION_ERROR_TOO_LARGE_UNDO)
    
    def onOfferAdd (self, match):
        tofrom, index, offertype, parameters = match.groups()
        
        if tofrom == "t":
            # IcGameModel keeps track of the offers we've sent ourselves, so we
            # don't need this
            return
        
        self.indexType[index] = offertype
        if offertype == "match":
            fname, frating, col, tname, trating, rated, type, mins, incr, ad = \
                    matchre.match(parameters).groups()
            
            rating = frating.strip()
            rating = rating.isdigit() and rating or "0"
            rated = rated == "unrated" and "u" or "r"
            match = {"tp": type, "w": fname, "rt": rating,
                        "r": rated, "t": mins, "i": incr}
            self.emit("onChallengeAdd", index, match)
        
        elif offertype in strToOfferType:
            offerType = strToOfferType[offertype]
            if offerType == TAKEBACK_OFFER:
                offer = Offer(offerType, int(parameters))
            else: offer = Offer(offerType)
            self.emit("onOfferAdd", index, offer)
        
        else:
            log.error("Unknown offer type: #", index, offertype, "whith" + \
                      "parameters:", parameters, ". Declining")
            print >> client, "decline", index
    
    def onOfferRemove (self, match):
        index = match.groups()[0]
        if not index in self.indexType:
            return
        if self.indexType[index] == "match":
            self.emit("onChallengeRemove", index)
        else: self.emit("onOfferRemove", index)
        del self.indexType[index]
    
    def offer (self, offer, ply):
        self.lastPly = ply
        s = offerTypeToStr[offer.offerType]
        if offer.offerType == TAKEBACK_OFFER:
            s += " " + str(ply-offer.param)
        print >> self.connection.client, s
    
    def withdraw (self, type):
        print >> self.connection.client, "withdraw t", offerTypeToStr[type]
    
    def accept (self, type):
        print >> self.connection.client, "accept t", offerTypeToStr[type]
    
    def decline (self, type):
        print >> self.connection.client, "decline t", offerTypeToStr[type]
    
    def acceptIndex (self, index):
        print >> self.connection.client, "accept", index
    
    def declineIndex (self, index):
        print >> self.connection.client, "decline", index
    
    def playIndex (self, index):
        print >> self.connection.client, "play", index
