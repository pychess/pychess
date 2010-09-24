
import re

from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.System.Log import log
from pychess.ic.managers.GameListManager import convertName
from GameListManager import variantToSeek, unsupportedWilds

names = "\w+(?:\([A-Z\*]+\))*"

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\])?"
ratings = "\(([0-9\ \-\+]{4})\)"

matchreUntimed = re.compile ("(\w+) %s %s ?(\w+) %s %s (untimed)\s*" % \
                                  (ratings, colors, ratings, rated) )
matchre = re.compile ("(\w+) %s %s ?(\w+) %s %s (\w+) (\d+) (\d+)\s*(.*)" % \
                                  (ratings, colors, ratings, rated) )

#<pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) [black] GuestNXMP (----) unrated blitz 2 12
#<pf> 16 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated wild 2 12 Loaded from wild/fr
#<pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated blitz 2 12 (adjourned)
#<pf> 45 w=GuestGYXR t=match p=GuestGYXR (----) Lobais (----) unrated losers 2 12
#<pf> 45 w=GuestYDDR t=match p=GuestYDDR (----) mgatto (1358) unrated untimed

#
# Known offers: abort accept adjourn draw match pause unpause switch takeback
#

unsupportedtypes = (unsupportedWilds.keys())

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
        'onOfferAdd' : (SIGNAL_RUN_FIRST, None, (object,)),
        'onOfferRemove' : (SIGNAL_RUN_FIRST, None, (object,)),
        'onOfferDeclined' : (SIGNAL_RUN_FIRST, None, (object,)),
        'onChallengeAdd' : (SIGNAL_RUN_FIRST, None, (str, object)),
        'onChallengeRemove' : (SIGNAL_RUN_FIRST, None, (str,)),
        'onActionError' : (SIGNAL_RUN_FIRST, None, (object, int)),
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
        
        self.connection.expect_line (self.onOfferDeclined,
            "\w+ declines the (draw|takeback|pause|unpause|abort|adjourn) request\.")
        
        self.lastPly = 0
        self.offers = {}
        
        self.connection.lvm.setVariable("formula", "!suicide & !crazyhouse & !bughouse & !atomic")
        self.connection.lvm.setVariable("pendinfo", True)
    
    def onOfferDeclined (self, match):
        type = match.groups()[0]
        offer = Offer(strToOfferType[type])
        self.emit("onOfferDeclined", offer)
    
    def noOffersToAccept (self, match):
        offertype, request = match.groups()
        if request == "accept":
            error = ACTION_ERROR_NONE_TO_ACCEPT
        elif request == "withdraw":
            error = ACTION_ERROR_NONE_TO_WITHDRAW
        elif request == "decline":
            error = ACTION_ERROR_NONE_TO_DECLINE
        offer = Offer(strToOfferType[offertype])
        self.emit("onActionError", offer, error)
    
    def notEnoughMovesToUndo (self, match):
        ply = match.groups()[0] or match.groups()[1]
        if ply == "no": ply = 0
        else: ply = int(ply)
        offer = Offer(TAKEBACK_OFFER, param=self.lastPly-ply)
        self.emit("onActionError", offer, ACTION_ERROR_TOO_LARGE_UNDO)
    
    def onOfferAdd (self, match):
        tofrom, index, offertype, parameters = match.groups()
        if tofrom == "t":
            # ICGameModel keeps track of the offers we've sent ourselves, so we
            # don't need this
            return
        if offertype not in strToOfferType:
            log.error("Declining unknown offer type: offertype=%s parameters=%s index=%s" % \
                (offertype, parameters, index))
            print >> self.connection.client, "decline", index
        offertype = strToOfferType[offertype]
        if offertype == TAKEBACK_OFFER:
            offer = Offer(offertype, param=int(parameters), index=int(index))
        else:
            offer = Offer(offertype, index=int(index))
        self.offers[offer.index] = offer
        
        if offer.type == MATCH_OFFER:
            if matchreUntimed.match(parameters) != None:
                fname, frating, col, tname, trating, rated, type = \
                    matchreUntimed.match(parameters).groups()
                mins = "0"
                incr = "0"
            else:
                fname, frating, col, tname, trating, rated, type_short, mins, incr, type = \
                    matchre.match(parameters).groups()
                if not type or "adjourned" in type:
                    type = type_short
            
            if type.split()[-1] in unsupportedtypes:
                self.decline(offer)
            else:
                rating = frating.strip()
                rating = rating.isdigit() and rating or "0"
                rated = rated == "unrated" and "u" or "r"
                match = {"tp": convertName(type), "w": fname, "rt": rating,
                         "r": rated, "t": mins, "i": incr}
                self.emit("onChallengeAdd", index, match)
        
        else:
            log.debug("OfferManager.onOfferAdd(): emitting offer=%s\n" % offer)
            self.emit("onOfferAdd", offer)
    
    def onOfferRemove (self, match):
        log.debug("OfferManager.onOfferRemove(): match.string=%s\n" % match.string)
        index = int(match.groups()[0])
        if not index in self.offers:
            return
        if self.offers[index].type == MATCH_OFFER:
            self.emit("onChallengeRemove", index)
        else:
            self.emit("onOfferRemove", self.offers[index])
        del self.offers[index]
    
    ###
    
    def challenge (self, playerName, startmin, incsec, rated, color=None, variant=NORMALCHESS):
        rchar = rated and "r" or "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        print >> self.connection.client, "match %s %d %d %s %s %s" % \
                (playerName, startmin, incsec, rchar, cchar, variantToSeek[variant])
    
    def offer (self, offer, ply):
        self.lastPly = ply
        s = offerTypeToStr[offer.type]
        if offer.type == TAKEBACK_OFFER:
            s += " " + str(ply - offer.param)
        print >> self.connection.client, s
    
    ###
    
    def withdraw (self, offer):
        print >> self.connection.client, "withdraw t", offerTypeToStr[offer.type]
    
    def accept (self, offer):
        if offer.index != None:
            self.acceptIndex(offer.index)
        else:
            print >> self.connection.client, "accept t", offerTypeToStr[offer.type]
    
    def decline (self, offer):
        if offer.index != None:
            self.declineIndex(offer.index)
        else:
            print >> self.connection.client, "decline t", offerTypeToStr[offer.type]
    
    def acceptIndex (self, index):
        print >> self.connection.client, "accept", index
    
    def declineIndex (self, index):
        print >> self.connection.client, "decline", index
    
    def playIndex (self, index):
        print >> self.connection.client, "play", index
    
    def abort (self):
        print >> self.connection.client, "abort"
    
    def adjourn (self):
        print >> self.connection.client, "adjourn"