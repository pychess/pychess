from collections import defaultdict

from pychess.compat import Queue
from pychess.Players.Player import Player, PlayerIsDead, TurnInterrupt
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
        self.queue = Queue()
        self.okqueue = Queue()
        self.setName(name)
        self.ichandle = ichandle
        self.icrating = icrating
        self.color = color
        self.gameno = gameno
        self.gamemodel = gamemodel

        # If some times later FICS creates another game with same wplayer,bplayer,gameno
        # this will change to False and boardUpdate messages will be ignored
        self.current = True

        self.connection = connection = self.gamemodel.connection
        self.connections = connections = defaultdict(list)
        connections[connection.bm].append(connection.bm.connect_after(
            "boardUpdate", self.__boardUpdate))
        connections[connection.bm].append(connection.bm.connect_after(
            "playGameCreated", self.__playGameCreated))
        connections[connection.bm].append(connection.bm.connect_after(
            "obsGameCreated", self.__obsGameCreated))
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

    # Handle signals from the connection

    def __playGameCreated(self, bm, ficsgame):
        if self.gamemodel.ficsplayers[0] == ficsgame.wplayer and \
            self.gamemodel.ficsplayers[1] == ficsgame.bplayer and \
                self.gameno == ficsgame.gameno:
            log.debug("ICPlayer.__playGameCreated: gameno reappeared: gameno=%s white=%s black=%s" % (
                ficsgame.gameno, ficsgame.wplayer.name, ficsgame.bplayer.name))
            self.current = False

    def __obsGameCreated(self, bm, ficsgame):
        if self.gamemodel.ficsplayers[0] == ficsgame.wplayer and \
            self.gamemodel.ficsplayers[1] == ficsgame.bplayer and \
                self.gameno == ficsgame.gameno:
            log.debug("ICPlayer.__obsGameCreated: gameno reappeared: gameno=%s white=%s black=%s" % (
                ficsgame.gameno, ficsgame.wplayer.name, ficsgame.bplayer.name))
            self.current = False

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
            self.emit("withdraw", self.offers[offer.index])
            del self.offers[offer.index]

    def __onPrivateMessage(self, cm, name, title, isadmin, text):
        if name == self.ichandle:
            self.emit("offer", Offer(CHAT_ACTION, param=text))

    def __boardUpdate(self, bm, gameno, ply, curcol, lastmove, fen, wname,
                      bname, wms, bms):
        log.debug("ICPlayer.__boardUpdate: id(self)=%d self=%s %s %s %s %d %d %s %s %d %d" % (
            id(self), self, gameno, wname, bname, ply, curcol, lastmove, fen, wms, bms))

        if gameno == self.gameno and len(self.gamemodel.players) >= 2 and self.current:
            # LectureBot allways uses gameno 1 for many games in one lecture
            # and wname == self.gamemodel.players[0].ichandle \
            # and bname == self.gamemodel.players[1].ichandle \
            log.debug("ICPlayer.__boardUpdate: id=%d self=%s gameno=%s: this is my move" % (
                id(self), self, gameno))

            # In some cases (like lost on time) the last move is resent
            if ply <= self.gamemodel.ply:
                return

            if 1 - curcol == self.color and ply == self.gamemodel.ply + 1 and lastmove is not None:
                log.debug("ICPlayer.__boardUpdate: id=%d self=%s ply=%d: \
                          putting move=%s in queue" % (id(self), self, ply, lastmove))
                self.queue.put((ply, lastmove))
                # Ensure the fics thread doesn't continue parsing, before the
                # game/player thread has received the move.
                # Specifically this ensures that we aren't killed due to end of
                # game before our last move is received
                self.okqueue.get(block=True)

    # Ending the game

    def __disconnect(self):
        if self.connections is None:
            return
        for obj in self.connections:
            for handler_id in self.connections[obj]:
                if obj.handler_is_connected(handler_id):
                    obj.disconnect(handler_id)
        self.connections = None

    def end(self, status, reason):
        self.__disconnect()
        self.queue.put("del")

    def kill(self, reason):
        self.__disconnect()
        self.queue.put("del")

    # Send the player move updates

    def makeMove(self, board1, move, board2):
        log.debug("ICPlayer.makemove: id(self)=%d self=%s move=%s board1=%s board2=%s" % (
            id(self), self, move, board1, board2))
        if board2 and not self.gamemodel.isObservationGame():
            # TODO: Will this work if we just always use CASTLE_SAN?
            castle_notation = CASTLE_KK
            if board2.variant == FISCHERRANDOMCHESS:
                castle_notation = CASTLE_SAN
            self.connection.bm.sendMove(toAN(board2, move, castleNotation=castle_notation))

        item = self.queue.get(block=True)
        try:
            if item == "del":
                raise PlayerIsDead
            if item == "int":
                raise TurnInterrupt

            ply, sanmove = item
            if ply < board1.ply:
                # This should only happen in an observed game
                board1 = self.gamemodel.getBoardAtPly(max(ply - 1, 0))
            log.debug("ICPlayer.makemove: id(self)=%d self=%s from queue got: ply=%d sanmove=%s" % (
                id(self), self, ply, sanmove))

            try:
                move = parseSAN(board1, sanmove)
                log.debug("ICPlayer.makemove: id(self)=%d self=%s parsed move=%s" % (
                    id(self), self, move))
            except ParsingError:
                raise
            return move
        finally:
            log.debug("ICPlayer.makemove: id(self)=%d self=%s returning move=%s" % (
                id(self), self, move))
            self.okqueue.put("ok")

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
        # We raise TurnInterruprt in order to let GameModel continue the game
        if movecount % 2 == 1 and gamemodel.curplayer != self:
            self.queue.put("int")

    def resetPosition(self):
        """ Used in observed examined games f.e. when LectureBot starts another example"""
        self.queue.put("int")

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
                    log.debug("ICPlayer.offer: del self.offers[%s] %s" %
                              (index, offer))
                    del self.offers[index]
        self.connection.om.offer(offer, self.gamemodel.ply)

    def offerDeclined(self, offer):
        log.debug("ICPlayer.offerDeclined: sending decline for %s" % offer)
        self.connection.om.decline(offer)

    def offerWithdrawn(self, offer):
        pass

    def offerError(self, offer, error):
        pass

    def observe(self):
        self.connection.client.run_command("observe %s" % self.ichandle)
