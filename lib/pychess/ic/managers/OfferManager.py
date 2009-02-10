
import re

from gobject import *

from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.System.Log import log
from pychess.ic.managers.GameListManager import convertName

names = "\w+(?:\([A-Z\*]+\))*"

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\])?"
ratings = "\(([0-9\ \-\+]{4})\)"

matchre = re.compile ("(\w+) %s %s ?(\w+) %s %s (\w+) (\d+) (\d+)\s*(.*)" % \
                                  (ratings, colors, ratings, rated) )

#<pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) [black] GuestNXMP (----) unrated blitz 2 12
#<pf> 16 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated wild 2 12 Loaded from wild/fr
#<pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated blitz 2 12 (adjourned)
#<pf> 45 w=GuestGYXR t=match p=GuestGYXR (----) Lobais (----) unrated losers 2 12

#
# Known offers: abort accept adjourn draw match pause unpause switch takeback
#

unsupportedtypes = ("wild/0", "wild/1", "bughouse", "crazyhouse", "suicide")

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
                "There are (?:(no)|only (\d+) half) moves in your game\.")
        
        self.connection.expect_line (self.noOffersToAccept,
                "There are no ([^ ]+) offers to (accept).")
        
        self.lastPly = 0
        self.indexType = {}
        
        self.connection.lvm.setVariable("formula", "!suicide & !crazyhouse & !bughouse")
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
        param = match.groups()[0] or match.groups()[1]
        if param == "no": param = 0
        else: param = int(param)
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
            fname, frating, col, tname, trating, rated, type_short, mins, incr, type = \
                    matchre.match(parameters).groups()
            
            if not type or "adjourned" in type:
                type = type_short
            
            if type.split()[-1] in unsupportedtypes:
                self.declineIndex(index)
            
            else:
                rating = frating.strip()
                rating = rating.isdigit() and rating or "0"
                rated = rated == "unrated" and "u" or "r"
                match = {"tp": convertName(type), "w": fname, "rt": rating,
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
    
    ###
    
    def challenge (self, playerName, startmin, incsec, rated, color=None):
        rchar = rated and "r" or "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        print >> self.connection.client, "match %s %d %d %s %s" % \
                (playerName, startmin, incsec, rchar, cchar)
    
    def offerRematch (self):
        print >> self.connection.client, "rematch"
    
    def offer (self, offer, ply):
        self.lastPly = ply
        s = offerTypeToStr[offer.offerType]
        if offer.offerType == TAKEBACK_OFFER:
            s += " " + str(ply-offer.param)
        print >> self.connection.client, s
    
    ###
    
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
