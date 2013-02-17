import re
from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.Utils.const import *
from pychess.Utils.Offer import Offer
from pychess.System.Log import log
from pychess.ic import *

names = "\w+(?:\([A-Z\*]+\))*"

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\])?"
ratings = "\(([0-9\ \-\+]{4}[E P]?)\)"
loaded_from = "(?: Loaded from (wild.*))?"
adjourned = "(?: (\(adjourned\)))?"

matchreUntimed = re.compile ("(\w+) %s %s ?(\w+) %s %s (untimed)\s*" % \
                                  (ratings, colors, ratings, rated) )
matchre = re.compile(
    "(\w+) %s %s ?(\w+) %s %s (\w+) (\d+) (\d+)%s%s" % \
    (ratings, colors, ratings, rated, loaded_from, adjourned))

#<pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) [black] GuestNXMP (----) unrated blitz 2 12
#<pf> 16 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated wild 2 12 Loaded from wild/fr
#<pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated blitz 2 12 (adjourned)
#<pf> 45 w=GuestGYXR t=match p=GuestGYXR (----) Lobais (----) unrated losers 2 12
#<pf> 45 w=GuestYDDR t=match p=GuestYDDR (----) mgatto (1358) unrated untimed
#<pf> 71 w=joseph t=match p=joseph (1632) mgatto (1742) rated wild 5 1 Loaded from wild/fr (adjourned)
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
        log.debug("OfferManager.onOfferDeclined: match.string=%s\n" % match.string)
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
        log.debug("OfferManager.onOfferAdd: match.string=%s\n" % match.string)
        tofrom, index, offertype, parameters = match.groups()

        if tofrom == "t":
            # ICGameModel keeps track of the offers we've sent ourselves, so we
            # don't need this
            return
        if offertype not in strToOfferType:
            log.warn("OfferManager.onOfferAdd: Declining unknown offer type: " + \
                "offertype=%s parameters=%s index=%s\n" % (offertype, parameters, index))
            print >> self.connection.client, "decline", index
        offertype = strToOfferType[offertype]
        if offertype == TAKEBACK_OFFER:
            offer = Offer(offertype, param=int(parameters), index=int(index))
        else:
            offer = Offer(offertype, index=int(index))
        self.offers[offer.index] = offer
        
        if offer.type == MATCH_OFFER:
            is_adjourned = False
            if matchreUntimed.match(parameters) != None:
                fname, frating, col, tname, trating, rated, type = \
                    matchreUntimed.match(parameters).groups()
                mins = "0"
                incr = "0"
                gametype = GAME_TYPES["untimed"]
            else:
                fname, frating, col, tname, trating, rated, gametype, mins, \
                    incr, wildtype, adjourned = matchre.match(parameters).groups()
                if (wildtype and "adjourned" in wildtype) or \
                        (adjourned and "adjourned" in adjourned):
                    is_adjourned = True
                if wildtype and "wild" in wildtype:
                    gametype = wildtype
                    
                try:
                    gametype = GAME_TYPES[gametype]
                except KeyError:
                    log.warn("OfferManager.onOfferAdd: auto-declining " + \
                        "unknown offer type: '%s'\n" % gametype)
                    self.decline(offer)
                    del self.offers[offer.index]
                    return
            
            # TODO: get the ficsplayer and update their rating to this one
            # rather than emitting it in match 
            rating = frating.strip()
            rating = rating.isdigit() and rating or "0"
            rated = rated == "unrated" and "u" or "r"
            match = {"gametype": gametype, "w": fname, "rt": rating,
                "r": rated, "t": mins, "i": incr, "is_adjourned": is_adjourned}
            self.emit("onChallengeAdd", index, match)
        
        else:
            log.debug("OfferManager.onOfferAdd: emitting onOfferAdd: %s\n" % offer)
            self.emit("onOfferAdd", offer)
    
    def onOfferRemove (self, match):
        log.debug("OfferManager.onOfferRemove: match.string=%s\n" % match.string)
        index = int(match.groups()[0])
        if not index in self.offers:
            return
        if self.offers[index].type == MATCH_OFFER:
            self.emit("onChallengeRemove", index)
        else:
            self.emit("onOfferRemove", self.offers[index])
        del self.offers[index]
    
    ###
    
    def challenge (self, playerName, game_type, startmin, incsec, rated, color=None):
        log.debug("OfferManager.challenge: %s %s %s %s %s %s\n" % \
            (playerName, game_type, startmin, incsec, rated, color))
        rchar = rated and "r" or "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        s = "match %s %d %d %s %s" % \
            (playerName, startmin, incsec, rchar, cchar)
        if isinstance(game_type, VariantGameType):
            s += " " + game_type.seek_text
        print s
        print >> self.connection.client, s
    
    def offer (self, offer, curply):
        log.debug("OfferManager.offer: curply=%s %s\n" % (curply, offer))
        self.lastPly = curply
        s = offerTypeToStr[offer.type]
        if offer.type == TAKEBACK_OFFER:
            s += " " + str(curply - offer.param)
        print >> self.connection.client, s
    
    ###
    
    def withdraw (self, offer):
        log.debug("OfferManager.withdraw: %s\n" % offer)
        print >> self.connection.client, "withdraw t", offerTypeToStr[offer.type]
    
    def accept (self, offer):
        log.debug("OfferManager.accept: %s\n" % offer)
        if offer.index != None:
            self.acceptIndex(offer.index)
        else:
            print >> self.connection.client, "accept t", offerTypeToStr[offer.type]
    
    def decline (self, offer):
        log.debug("OfferManager.decline: %s\n" % offer)
        if offer.index != None:
            self.declineIndex(offer.index)
        else:
            print >> self.connection.client, "decline t", offerTypeToStr[offer.type]
    
    def acceptIndex (self, index):
        log.debug("OfferManager.acceptIndex: index=%s\n" % index)
        print >> self.connection.client, "accept", index
    
    def declineIndex (self, index):
        log.debug("OfferManager.declineIndex: index=%s\n" % index)
        print >> self.connection.client, "decline", index
    
    def playIndex (self, index):
        log.debug("OfferManager.playIndex: index=%s\n" % index)
        print >> self.connection.client, "play", index
