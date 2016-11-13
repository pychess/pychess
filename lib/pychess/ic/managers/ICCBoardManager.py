from __future__ import print_function

import threading

from gi.repository import GObject

from pychess.ic.FICSObjects import FICSGame, FICSBoard
from pychess.ic.managers.BoardManager import BoardManager
from pychess.ic import IC_POS_OBSERVING_EXAMINATION, IC_POS_OBSERVING, GAME_TYPES
from pychess.ic.icc import DG_POSITION_BEGIN, DG_SEND_MOVES, DG_MOVE_ALGEBRAIC, DG_MOVE_SMITH, \
    DG_MOVE_TIME, DG_MOVE_CLOCK, DG_MY_GAME_STARTED, DG_MY_GAME_ENDED, DG_STARTED_OBSERVING, DG_STOP_OBSERVING


class ICCBoardManager(BoardManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_line(self.on_icc_my_game_started, "%s (.+)" % DG_MY_GAME_STARTED)
        self.connection.expect_line(self.on_icc_started_observing, "%s (.+)" % DG_STARTED_OBSERVING)
        self.connection.expect_line(self.on_icc_stop_observing, "%s (.+)" % DG_STOP_OBSERVING)
        self.connection.expect_line(self.on_icc_my_game_ended, "%s (.+)" % DG_MY_GAME_ENDED)

        self.connection.expect_line(self.on_icc_position_begin, "%s (.+)" % DG_POSITION_BEGIN)
        self.connection.expect_line(self.on_icc_send_moves, "%s (.+)" % DG_SEND_MOVES)

        self.queuedEmits = {}
        self.gamemodelStartedEvents = {}
        self.theGameImPlaying = None
        self.gamesImObserving = {}

        self.connection.client.run_command("set-2 %s 1" % DG_MY_GAME_STARTED)
        self.connection.client.run_command("set-2 %s 1" % DG_STARTED_OBSERVING)
        self.connection.client.run_command("set-2 %s 1" % DG_STOP_OBSERVING)
        self.connection.client.run_command("set-2 %s 1" % DG_MY_GAME_ENDED)

        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_ALGEBRAIC)
        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_SMITH)
        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_TIME)
        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_CLOCK)
        self.connection.client.run_command("set-2 %s 1" % DG_POSITION_BEGIN)
        self.connection.client.run_command("set-2 %s 1" % DG_SEND_MOVES)
        self.connection.client.run_command("set style 13")

        # don't unobserve games when we start a new game
        self.connection.client.run_command("set unobserve 3")
        self.connection.lvm.autoFlagNotify()

    def on_icc_my_game_started(self, match):
        # gamenumber whitename blackname wild-number rating-type rated
        # white-initial white-increment black-initial black-increment
        # played-game {ex-string} white-rating black-rating game-id
        # white-titles black-titles irregular-legality irregular-semantics
        # uses-plunkers fancy-timecontrol promote-to-king
        # 685 Salsicha MaxiBomb 0 Blitz 1 3 0 3 0 1 {} 2147 2197 1729752694 {} {} 0 0 0 {} 0
        # 259 Rikikilord ARMH 0 Blitz 1 2 12 2 12 0 {Ex: Rikikilord 0} 1532 1406 1729752286 {} {} 0 0 0 {} 0
        parts = match.groups()[0].split()[0]
        print("send_moves", parts)

    on_icc_my_game_started.BLKCMD = DG_MY_GAME_STARTED

    def on_icc_started_observing(self, match):
        gameno, wname, bname, wild, rtype, rated, wmin, winc, bmin, binc, played_game, rest = match.groups()[0].split(" ", 11)

        gameno = int(gameno)
        wplayer = self.connection.players.get(wname)
        bplayer = self.connection.players.get(bname)
        # TODO: create ICC_GAME_TYPES; ICC game type letters can differ
        game_type = GAME_TYPES[rtype.lower()]
        relation = IC_POS_OBSERVING_EXAMINATION if played_game == "0" else IC_POS_OBSERVING
        wms = bms = int(wmin) * 60 * 100

        game = FICSGame(wplayer,
                        bplayer,
                        gameno=gameno,
                        rated=rated == "1",
                        game_type=game_type,
                        minutes=int(wmin),
                        inc=int(winc),
                        relation=relation,
                        board=FICSBoard(wms,
                                        bms))

        game = self.connection.games.get(game, emit=False)

        self.gamesImObserving[game] = 0, 0

        self.gamemodelStartedEvents[game.gameno] = threading.Event()
        self.emit("obsGameCreated", game)
        # self.gamemodelStartedEvents[game.gameno].wait()

    on_icc_started_observing.BLKCMD = DG_STARTED_OBSERVING

    def on_icc_stop_observing(self, match):
        gameno = match.groups()[0].split()[0]
        print("stop_observing", gameno)

    on_icc_stop_observing.BLKCMD = DG_STOP_OBSERVING

    def on_icc_my_game_ended(self, match):
        parts = match.groups()[0].split()[0]
        print("send_moves", parts)

    on_icc_my_game_ended.BLKCMD = DG_MY_GAME_ENDED

    def on_icc_position_begin(self, match):
        parts = match.groups()[0].split()[0]
        print("send_moves", parts)

    on_icc_position_begin.BLKCMD = DG_POSITION_BEGIN

    def on_icc_send_moves(self, match):
        parts = match.groups()[0].split()[0]
        print("send_moves", parts)

    on_icc_send_moves.BLKCMD = DG_SEND_MOVES
