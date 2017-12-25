from gi.repository import GObject

from pychess.Utils.const import OFFERS, DRAW_OFFER, ABORT_OFFER, ADJOURN_OFFER, TAKEBACK_OFFER

from pychess.Utils.Offer import Offer
from pychess.System.Log import log
from pychess.ic.managers.OfferManager import OfferManager, offerTypeToStr
from pychess.ic.icc import DG_OFFERS_IN_MY_GAME, DG_MATCH, DG_MATCH_REMOVED


class ICCOfferManager(OfferManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_dg_line(DG_OFFERS_IN_MY_GAME, self.on_icc_offers_in_my_game)
        self.connection.expect_dg_line(DG_MATCH, self.on_icc_match)
        self.connection.expect_dg_line(DG_MATCH_REMOVED, self.on_icc_match_removed)

        self.connection.client.run_command("set-2 %s 1" % DG_OFFERS_IN_MY_GAME)
        self.connection.client.run_command("set-2 %s 1" % DG_MATCH)
        self.connection.client.run_command("set-2 %s 1" % DG_MATCH_REMOVED)

        self.lastPly = 0
        self.offers = {}

    def on_icc_offers_in_my_game(self, data):
        log.debug("DG_OFFERS_IN_MY_GAME %s" % data)
        # gamenumber wdraw bdraw wadjourn badjourn wabort babort wtakeback btakeback
        gamenumber, wdraw, bdraw, wadjourn, badjourn, wabort, babort, wtakeback, btakeback = map(int, data.split())

        if wdraw or bdraw:
            offertype = DRAW_OFFER
        elif wadjourn or badjourn:
            offertype = ADJOURN_OFFER
        elif wabort or babort:
            offertype = ABORT_OFFER
        elif wtakeback or btakeback:
            offertype = TAKEBACK_OFFER
        else:
            log.debug("ICCOfferManager.on_icc_offers_in_my_game: unknown offer data: %s" % data)
            return

        index = gamenumber * 100000 + OFFERS.index(offertype)
        if offertype == TAKEBACK_OFFER:
            parameters = wtakeback if wtakeback else btakeback
            offer = Offer(offertype, param=parameters, index=index)
        else:
            offer = Offer(offertype, index=index)
        self.offers[offer.index] = offer

        log.debug("ICCOfferManager.on_icc_offers_in_my_game: emitting onOfferAdd: %s" % offer)
        self.emit("onOfferAdd", offer)

    def on_icc_match(self, data):
        # challenger-name challenger-rating challenger-titles
        # receiver-name   receiver-rating   receiver-titles
        # wild-number rating-type is-it-rated is-it-adjourned
        # challenger-time-control receiver-time-control
        # challenger-color-request [assess-loss assess-draw assess-win]
        # fancy-time-control
        log.debug("DG_MATCH %s" % data)

    def on_icc_match_removed(self, data):
        # challenger-name receiver-name ^Y{Explanation string^Y}
        log.debug("DG_MATCH_REMOVED %s" % data)

    def accept(self, offer):
        log.debug("OfferManager.accept: %s" % offer)
        self.connection.client.run_command("%s" % offerTypeToStr[offer.type])

    def decline(self, offer):
        log.debug("OfferManager.decline: %s" % offer)
        self.connection.client.run_command("decline %s" % offerTypeToStr[offer.type])
