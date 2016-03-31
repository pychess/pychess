import re

from gi.repository import GObject

from pychess.Utils.const import DRAW_OFFER, ABORT_OFFER, ADJOURN_OFFER, TAKEBACK_OFFER, \
    PAUSE_OFFER, RESUME_OFFER, SWITCH_OFFER, RESIGNATION, FLAG_CALL, MATCH_OFFER, \
    WHITE, ACTION_ERROR_SWITCH_UNDERWAY, ACTION_ERROR_CLOCK_NOT_STARTED, \
    ACTION_ERROR_CLOCK_NOT_PAUSED, ACTION_ERROR_NONE_TO_ACCEPT, ACTION_ERROR_NONE_TO_WITHDRAW, \
    ACTION_ERROR_NONE_TO_DECLINE, ACTION_ERROR_TOO_LARGE_UNDO, ACTION_ERROR_NOT_OUT_OF_TIME

from pychess.Utils.Offer import Offer
from pychess.System.Log import log
from pychess.ic import GAME_TYPES, VariantGameType
from pychess.ic.FICSObjects import FICSChallenge

names = "\w+(?:\([A-Z\*]+\))*"

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\])?"
ratings = "\(([0-9\ \-\+]{1,4}[E P]?)\)"
loaded_from = "(?: Loaded from (wild[/\w]*))?"
adjourned = "(?: (\(adjourned\)))?"

matchreUntimed = re.compile("(\w+) %s %s ?(\w+) %s %s (untimed)\s*" %
                            (ratings, colors, ratings, rated))
matchre = re.compile(
    "(\w+) %s %s ?(\w+) %s %s (\w+) (\d+) (\d+)%s%s" %
    (ratings, colors, ratings, rated, loaded_from, adjourned))

# <pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) [black] GuestNXMP (----) unrated blitz 2 12
# <pf> 16 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated wild 2 12 Loaded from wild/fr
# <pf> 39 w=GuestDVXV t=match p=GuestDVXV (----) GuestNXMP (----) unrated blitz 2 12 (adjourned)
# <pf> 45 w=GuestGYXR t=match p=GuestGYXR (----) Lobais (----) unrated losers 2 12
# <pf> 45 w=GuestYDDR t=match p=GuestYDDR (----) mgatto (1358) unrated untimed
# <pf> 71 w=joseph t=match p=joseph (1632) mgatto (1742) rated wild 5 1 Loaded from wild/fr (adjourned)
# <pf> 59 w=antiseptic t=match p=antiseptic (1945) mgatto (1729) rated wild 6 1 Loaded from wild/4 (adjourned)
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
for k, v in strToOfferType.items():
    offerTypeToStr[v] = k


class OfferManager(GObject.GObject):

    __gsignals__ = {
        'onOfferAdd': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'onOfferRemove': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'onOfferDeclined': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'onChallengeAdd': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'onChallengeRemove': (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        'onActionError': (GObject.SignalFlags.RUN_FIRST, None, (object, int)),
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)

        self.connection = connection

        self.connection.expect_line(
            self.onOfferAdd, "<p(t|f)> (\d+) w=%s t=(\w+) p=(.+)" % names)
        self.connection.expect_line(self.onOfferRemove, "<pr> (\d+)")

        for ficsstring, offer, error in (
            ("You cannot switch sides once a game is underway.",
             Offer(SWITCH_OFFER), ACTION_ERROR_SWITCH_UNDERWAY),
            ("Opponent is not out of time.", Offer(FLAG_CALL),
             ACTION_ERROR_NOT_OUT_OF_TIME), ("The clock is not ticking yet.",
                                             Offer(PAUSE_OFFER),
                                             ACTION_ERROR_CLOCK_NOT_STARTED),
            ("The clock is not ticking.", Offer(FLAG_CALL),
             ACTION_ERROR_CLOCK_NOT_STARTED), ("The clock is not paused.",
                                               Offer(RESUME_OFFER),
                                               ACTION_ERROR_CLOCK_NOT_PAUSED)):
            self.connection.expect_line(
                lambda match: self.emit("onActionError", offer, error),
                ficsstring)

        self.connection.expect_line(
            self.notEnoughMovesToUndo,
            "There are (?:(no)|only (\d+) half) moves in your game\.")

        self.connection.expect_line(self.noOffersToAccept,
                                    "There are no ([^ ]+) offers to (accept).")

        self.connection.expect_line(
            self.onOfferDeclined,
            "\w+ declines the (draw|takeback|pause|unpause|abort|adjourn) request\.")

        self.lastPly = 0
        self.offers = {}

        self.connection.client.run_command("iset pendinfo 1")

    def onOfferDeclined(self, match):
        log.debug("OfferManager.onOfferDeclined: match.string=%s" %
                  match.string)
        type = match.groups()[0]
        offer = Offer(strToOfferType[type])
        self.emit("onOfferDeclined", offer)

    def noOffersToAccept(self, match):
        offertype, request = match.groups()
        if request == "accept":
            error = ACTION_ERROR_NONE_TO_ACCEPT
        elif request == "withdraw":
            error = ACTION_ERROR_NONE_TO_WITHDRAW
        elif request == "decline":
            error = ACTION_ERROR_NONE_TO_DECLINE
        offer = Offer(strToOfferType[offertype])
        self.emit("onActionError", offer, error)

    def notEnoughMovesToUndo(self, match):
        ply = match.groups()[0] or match.groups()[1]
        if ply == "no":
            ply = 0
        else:
            ply = int(ply)
        offer = Offer(TAKEBACK_OFFER, param=self.lastPly - ply)
        self.emit("onActionError", offer, ACTION_ERROR_TOO_LARGE_UNDO)

    def onOfferAdd(self, match):
        log.debug("OfferManager.onOfferAdd: match.string=%s" % match.string)

        tofrom, index, offertype, parameters = match.groups()
        index = int(index)

        if tofrom == "t":
            # ICGameModel keeps track of the offers we've sent ourselves, so we
            # don't need this
            return
        if offertype not in strToOfferType:
            log.warning("OfferManager.onOfferAdd: Declining unknown offer type: " +
                        "offertype=%s parameters=%s index=%d" % (offertype, parameters, index))
            self.connection.client.run_command("decline %d" % index)
            return
        offertype = strToOfferType[offertype]
        if offertype == TAKEBACK_OFFER:
            offer = Offer(offertype, param=int(parameters), index=index)
        else:
            offer = Offer(offertype, index=index)
        self.offers[offer.index] = offer

        if offer.type == MATCH_OFFER:
            is_adjourned = False
            if matchreUntimed.match(parameters) is not None:
                fname, frating, col, tname, trating, rated, type = \
                    matchreUntimed.match(parameters).groups()
                mins = 0
                incr = 0
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
                    log.warning("OfferManager.onOfferAdd: auto-declining " +
                                "unknown offer type: '%s'\n" % gametype)
                    self.decline(offer)
                    del self.offers[offer.index]
                    return

            player = self.connection.players.get(fname)
            rating = frating.strip()
            rating = int(rating) if rating.isdigit() else 0
            if gametype.rating_type in player.ratings and \
                    player.ratings[gametype.rating_type] != rating:
                player.ratings[gametype.rating_type] = rating
                player.emit("ratings_changed", gametype.rating_type, player)
            rated = rated != "unrated"
            challenge = FICSChallenge(index,
                                      player,
                                      int(mins),
                                      int(incr),
                                      rated,
                                      col,
                                      gametype,
                                      adjourned=is_adjourned)
            self.emit("onChallengeAdd", challenge)

        else:
            log.debug("OfferManager.onOfferAdd: emitting onOfferAdd: %s" %
                      offer)
            self.emit("onOfferAdd", offer)

    def onOfferRemove(self, match):
        log.debug("OfferManager.onOfferRemove: match.string=%s" % match.string)
        index = int(match.groups()[0])
        if index not in self.offers:
            return
        if self.offers[index].type == MATCH_OFFER:
            self.emit("onChallengeRemove", index)
        else:
            self.emit("onOfferRemove", self.offers[index])
        del self.offers[index]

    ###

    def challenge(self,
                  player_name,
                  game_type,
                  startmin,
                  incsec,
                  rated,
                  color=None):
        log.debug("OfferManager.challenge: %s %s %s %s %s %s" %
                  (player_name, game_type, startmin, incsec, rated, color))
        rchar = rated and "r" or "u"
        if color is not None:
            cchar = color == WHITE and "w" or "b"
        else:
            cchar = ""
        s = "match %s %d %d %s %s" % \
            (player_name, startmin, incsec, rchar, cchar)
        if isinstance(game_type, VariantGameType):
            s += " " + game_type.seek_text
        self.connection.client.run_command(s)

    def offer(self, offer, curply):
        log.debug("OfferManager.offer: curply=%s %s" % (curply, offer))
        self.lastPly = curply
        s = offerTypeToStr[offer.type]
        if offer.type == TAKEBACK_OFFER:
            s += " " + str(curply - offer.param)
        self.connection.client.run_command(s)

    ###

    def withdraw(self, offer):
        log.debug("OfferManager.withdraw: %s" % offer)
        self.connection.client.run_command("withdraw t %s" %
                                           offerTypeToStr[offer.type])

    def accept(self, offer):
        log.debug("OfferManager.accept: %s" % offer)
        if offer.index is not None:
            self.acceptIndex(offer.index)
        else:
            self.connection.client.run_command("accept t %s" %
                                               offerTypeToStr[offer.type])

    def decline(self, offer):
        log.debug("OfferManager.decline: %s" % offer)
        if offer.index is not None:
            self.declineIndex(offer.index)
        else:
            self.connection.client.run_command("decline t %s" %
                                               offerTypeToStr[offer.type])

    def acceptIndex(self, index):
        log.debug("OfferManager.acceptIndex: index=%s" % index)
        self.connection.client.run_command("accept %s" % index)

    def declineIndex(self, index):
        log.debug("OfferManager.declineIndex: index=%s" % index)
        self.connection.client.run_command("decline %s" % index)

    def playIndex(self, index):
        log.debug("OfferManager.playIndex: index=%s" % index)
        self.connection.client.run_command("play %s" % index)
