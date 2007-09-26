
import re

from gobject import *

from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.System.Log import log

from ICManager import ICManager
import telnet


names = "\w+(?:\([A-Z\*]+\))*"

types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "\(([0-9\ \-\+]{4})\)"


matchre = re.compile ("(\w+) %s %s(\w+) %s %s %s (\d+) (\d+)" % \
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
}

offerTypeToStr = {}
for k,v in strToOfferType.iteritems():
    offerTypeToStr[v] = k

class OfferManager (ICManager):
    
    __gsignals__ = {
        'onOfferAdd' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,object)),
        'onOfferRemove' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'onChallengeAdd' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,object)),
        'onChallengeRemove' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'onActionError' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,int))
    }
    
    def __init__ (self):
        ICManager.__init__(self)
        telnet.expect ( 
            "<p(t|f)> (\d+) w=%s t=(\w+) p=(.+?)\n" % names, self.onOfferAdd)
        telnet.expect ( "<pr> (\d+)\n", self.onOfferRemove)
        
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
            telnet.expect (ficsstring,
                    lambda c,g: self.emit("onActionError", offer, error))
        
        telnet.expect ("There are (?:(no)|only (\d+) half) moves in your game.", self.notEnoughMovesToUndo)
        
        telnet.expect ("There are no ([^ ]+) offers to (accept).", self.noOffersToAccept)
    
    def start (self):
        self.lastPly = 0
        self.indexType = {}
        print >> telnet.client, "iset pendinfo 1"
    
    def stop (self):
        print >> telnet.client, "iset pendinfo 0"
    
    def noOffersToAccept (self, client, groups):
        offerstr, type = groups
        if type == "accept":
            error = ACTION_ERROR_NONE_TO_ACCEPT
        elif type == "withdraw":
            error = ACTION_ERROR_NONE_TO_WITHDRAW
        elif type == "decline":
            error = ACTION_ERROR_NONE_TO_DECLINE
        offerType = strToOfferType[offerstr]
        self.emit("onActionError", Offer(offerType), error)
    
    def notEnoughMovesToUndo (self, client, groups):
        param = groups[0] != "no" and groups[0] or 0
        offer = Offer(TAKEBACK_OFFER, self.lastPly-param)
        self.emit("onActionError", offer, ACTION_ERROR_TO_LARGE_UNDO)
    
    def onOfferAdd (self, client, groups):
        tofrom, index, type, parameters = groups
        
        if tofrom == "t":
            # IcGameModel keeps track of the offers we've sent ourselves, so we
            # don't need this
            return
        
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
        
        elif type in strToOfferType:
            offerType = strToOfferType[type]
            if offerType == TAKEBACK_OFFER:
                offer = Offer(offerType, int(parameters))
            else: offer = Offer(offerType)
            self.emit("onOfferAdd", index, offer)
        
        else:
            log.error("Unknown offer type: #", index, type, "whith" + \
                      "parameters:", parameters, ". Declining")
            print >> client, "decline", index
    
    def onOfferRemove (self, client, groups):
        index = groups[0]
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
        print >> telnet.client, s
    
    def withdraw (self, type):
        print >> telnet.client, "withdraw t", offerTypeToStr[type]
    
    def accept (self, type):
        print >> telnet.client, "accept t", offerTypeToStr[type]
    
    def decline (self, type):
        print >> telnet.client, "decline t", offerTypeToStr[type]
    
    def acceptIndex (self, index):
        print >> telnet.client, "accept", index
    
    def playIndex (self, index):
        print >> telnet.client, "play", index

om = OfferManager()
