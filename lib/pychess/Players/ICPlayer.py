import asyncio
from collections import defaultdict

from pychess.Players.Player import Player, PlayerIsDead, PassInterrupt, TurnInterrupt, GameEnded
from pychess.Utils.Move import parseSAN, toAN
from pychess.Utils.lutils.lmove import ParsingError
from pychess.Utils.Offer import Offer
from pychess.Utils.const import REMOTE, UNFINISHED_STATES, CHAT_ACTION, CASTLE_KK, \
    FISCHERRANDOMCHESS, CASTLE_SAN, TAKEBACK_OFFER
from pychess.System.Log import log


class ICPlayer(Player):
    __type__ = REMOTE

    def __init__(self,
                 gamemodel,
                 ichandle,
                 gameno,
                 color,
                 name,
                 icrating=None):
        Player.__init__(self)
        self.offers = {}
        self.setName(name)
        self.ichandle = ichandle
        self.icrating = icrating
        self.color = color
        self.gameno = gameno
        self.gamemodel = gamemodel
        self.pass_interrupt = False
        self.turn_interrupt = False

        self.connection = connection = self.gamemodel.connection

        self.connections = connections = defaultdict(list)
        connections[connection.om].append(connection.om.connect(
            "onOfferAdd", self.__onOfferAdd))
        connections[connection.om].append(connection.om.connect(
            "onOfferRemove", self.__onOfferRemove))
        connections[connection.om].append(connection.om.connect(
            "onOfferDeclined", self.__onOfferDeclined))
        connections[connection.cm].append(connection.cm.connect(
            "privateMessage", self.__onPrivateMessage))

        self.cid = self.gamemodel.connect_after("game_terminated", self.on_game_terminated)

    def on_game_terminated(self, model):
        self.gamemodel.disconnect(self.cid)

    def getICHandle(self):
        return self.name

    @property
    def time(self):
        return self.gamemodel.timemodel.getPlayerTime(self.color)

    @property
    def move_queue(self):
        return self.gamemodel.ficsgame.move_queue

    # Handle signals from the connection

    def __onOfferAdd(self, om, offer):
        if self.gamemodel.status in UNFINISHED_STATES and not self.gamemodel.isObservationGame(
        ):
            log.debug("ICPlayer.__onOfferAdd: emitting offer: self.gameno=%s self.name=%s %s" % (
                self.gameno, self.name, offer))
            self.offers[offer.index] = offer
            self.emit("offer", offer)

    def __onOfferDeclined(self, om, offer):
        for offer_ in list(self.gamemodel.offers.keys()):
            if offer.type == offer_.type:
                offer.param = offer_.param
        log.debug("ICPlayer.__onOfferDeclined: emitting decline for %s" %
                  offer)
        self.emit("decline", offer)

    def __onOfferRemove(self, om, offer):
        if offer.index in self.offers:
            log.debug("ICPlayer.__onOfferRemove: emitting withdraw: \
                      self.gameno=%s self.name=%s %s" % (self.gameno, self.name, offer))
            # self.emit("withdraw", self.offers[offer.index])
            del self.offers[offer.index]

    def __onPrivateMessage(self, cm, name, title, isadmin, text):
        if name == self.ichandle:
            self.emit("offer", Offer(CHAT_ACTION, param=text))

    def __disconnect(self):
        log.debug("ICPlayer.__disconnect: %s" % self.name)
        if self.connections is None:
            return
        for obj in self.connections:
            for handler_id in self.connections[obj]:
                if obj.handler_is_connected(handler_id):
                    obj.disconnect(handler_id)
        self.connections = None

    def end(self, status=None, reason=None):
        log.debug("ICPlayer.end: %s" % self.name)
        self.__disconnect()
        self.move_queue.put_nowait("end")

    def kill(self, reason):
        self.__disconnect()
        self.move_queue.put_nowait("del")

    # Send the player move updates

    @asyncio.coroutine
    def makeMove(self, board1, move, board2):
        log.debug("ICPlayer.makemove: id(self)=%d self=%s move=%s board1=%s board2=%s" % (
            id(self), self, move, board1, board2))
        if board2 and not self.gamemodel.isObservationGame():
            # TODO: Will this work if we just always use CASTLE_SAN?
            castle_notation = CASTLE_KK
            if board2.variant == FISCHERRANDOMCHESS:
                castle_notation = CASTLE_SAN
            self.connection.bm.sendMove(toAN(board2, move, castleNotation=castle_notation))
            # wait for fics to send back our move we made
            item = yield from self.move_queue.get()
            log.debug("ICPlayer.makeMove: fics sent back the move we made")

        item = yield from self.move_queue.get()
        try:
            if item == "end":
                log.debug("ICPlayer.makeMove got: end")
                raise GameEnded
            elif item == "del":
                log.debug("ICPlayer.makeMove got: del")
                raise PlayerIsDead
            elif item == "stm":
                log.debug("ICPlayer.makeMove got: stm")
                self.turn_interrupt = False
                raise TurnInterrupt
            elif item == "fen":
                log.debug("ICPlayer.makeMove got: fen")
                self.turn_interrupt = False
                raise TurnInterrupt
            elif item == "pass":
                log.debug("ICPlayer.makeMove got: pass")
                self.pass_interrupt = False
                raise PassInterrupt

            gameno, ply, curcol, lastmove, fen, wname, bname, wms, bms = item
            log.debug("ICPlayer.makeMove got: %s %s %s %s" % (gameno, ply, curcol, lastmove))
            self.gamemodel.update_board(gameno, ply, curcol, lastmove, fen, wname, bname, wms, bms)

            if self.turn_interrupt:
                self.turn_interrupt = False
                raise TurnInterrupt

            if self.pass_interrupt:
                self.pass_interrupt = False
                raise PassInterrupt

            if ply < board1.ply:
                # This should only happen in an observed game
                board1 = self.gamemodel.getBoardAtPly(max(ply - 1, 0))
            log.debug("ICPlayer.makemove: id(self)=%d self=%s from queue got: ply=%d sanmove=%s" % (
                id(self), self, ply, lastmove))

            try:
                move = parseSAN(board1, lastmove)
                log.debug("ICPlayer.makemove: id(self)=%d self=%s parsed move=%s" % (
                    id(self), self, move))
            except ParsingError:
                raise
            return move
        finally:
            log.debug("ICPlayer.makemove: id(self)=%d self=%s returning move=%s" % (id(self), self, move))

    # Interacting with the player

    def pause(self):
        pass

    def resume(self):
        pass

    def setBoard(self, fen):
        # setBoard will currently only be called for ServerPlayer when starting
        # to observe some game. In this case FICS already knows how the board
        # should look, and we don't need to set anything
        pass

    def playerUndoMoves(self, movecount, gamemodel):
        log.debug("ICPlayer.playerUndoMoves: id(self)=%d self=%s, undoing movecount=%d" % (
            id(self), self, movecount))
        # If current player has changed so that it is no longer us to move,
        # We raise TurnInterrupt in order to let GameModel continue the game
        if movecount % 2 == 1 and gamemodel.curplayer != self:
            log.debug("ICPlayer.playerUndoMoves: set self.turn_interrupt = True %s" % self.name)
            if self.connection.ICC:
                self.move_queue.put_nowait("stm")
            else:
                self.turn_interrupt = True
        if movecount % 2 == 0 and gamemodel.curplayer == self:
            log.debug("ICPlayer.playerUndoMoves: set self.pass_interrupt = True %s" % self.name)
            if self.connection.ICC:
                self.move_queue.put_nowait("pass")
            else:
                self.pass_interrupt = True

    def resetPosition(self):
        """ Used in observed examined games f.e. when LectureBot starts another example"""
        self.turn_interrupt = True

    def putMessage(self, text):
        self.connection.cm.tellPlayer(self.ichandle, text)

    # Offer handling

    def offerRematch(self):
        if self.gamemodel.timed:
            minimum = int(self.gamemodel.timemodel.intervals[0][0]) / 60
            inc = self.gamemodel.timemodel.gain
        else:
            minimum = 0
            inc = 0
        self.connection.om.challenge(self.ichandle,
                                     self.gamemodel.ficsgame.game_type, minimum,
                                     inc, self.gamemodel.ficsgame.rated)

    def offer(self, offer):
        log.debug("ICPlayer.offer: self=%s %s" % (repr(self), offer))
        if offer.type == TAKEBACK_OFFER:
            # only 1 outstanding takeback offer allowed on FICS, so remove any of ours
            for index in list(self.offers.keys()):
                if self.offers[index].type == TAKEBACK_OFFER:
                    log.debug("ICPlayer.offer: del self.offers[%s] %s" % (index, offer))
                    del self.offers[index]
        self.connection.om.offer(offer)

    def offerDeclined(self, offer):
        log.debug("ICPlayer.offerDeclined: sending decline for %s" % offer)
        self.connection.om.decline(offer)

    def offerWithdrawn(self, offer):
        pass

    def offerError(self, offer, error):
        pass

    def observe(self):
        self.connection.client.run_command("observe %s" % self.ichandle)
