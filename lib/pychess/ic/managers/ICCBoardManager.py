from __future__ import print_function

import threading

from gi.repository import GObject

from pychess.Utils.const import WHITE
from pychess.ic.FICSObjects import FICSGame, FICSBoard
from pychess.ic.managers.BoardManager import BoardManager
from pychess.ic import IC_POS_OBSERVING_EXAMINATION, IC_POS_OBSERVING, GAME_TYPES
from pychess.ic.icc import DG_POSITION_BEGIN, DG_SEND_MOVES, DG_MOVE_ALGEBRAIC, DG_MOVE_SMITH, \
    DG_MOVE_TIME, DG_MOVE_CLOCK, DG_MY_GAME_STARTED, DG_MY_GAME_ENDED, DG_STARTED_OBSERVING, \
    DG_STOP_OBSERVING, DG_IS_VARIATION


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
        self.connection.client.run_command("set-2 %s 0" % DG_IS_VARIATION)

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

        pgnHead = [
            ("Event", "ICC %s %s game" % (rated, game_type.fics_name)),
            ("Site", "chessclub.com"), ("White", wname), ("Black", bname),
            ("Result", "*"),
        ]
        pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n*\n"

        game = FICSGame(wplayer,
                        bplayer,
                        gameno=gameno,
                        rated=rated == "1",
                        game_type=game_type,
                        minutes=int(wmin),
                        inc=int(winc),
                        relation=relation,
                        board=FICSBoard(wms,
                                        bms,
                                        pgn=pgn))

        game = self.connection.games.get(game, emit=False)

        self.gamesImObserving[game] = wms, bms
        # self.queuedStyle12s[game.gameno] = []
        self.queuedEmits[game.gameno] = []
        self.gamemodelStartedEvents[game.gameno] = threading.Event()

    on_icc_started_observing.BLKCMD = DG_STARTED_OBSERVING

    def on_icc_stop_observing(self, match):
        gameno = match.groups()[0].split()[0]
        print("stop_observing", gameno)

    on_icc_stop_observing.BLKCMD = DG_STOP_OBSERVING

    def on_icc_my_game_ended(self, match):
        parts = match.groups()[0].split()[0]
        print("my_game_ended", parts)

    on_icc_my_game_ended.BLKCMD = DG_MY_GAME_ENDED

    def on_icc_position_begin(self, match):
        # gamenumber {initial-FEN} nmoves-to-follow
        gameno, right_part = match.groups()[0].split("{")
        fen, moves_to_go = right_part.split("}")
        gameno = int(gameno)
        self.moves_to_go = int(moves_to_go)
        # TODO: get ply, curcol from fen
        self.ply = 0
        self.curcol = WHITE

        game = self.connection.games.get_game_by_gameno(gameno)
        if game.gameno not in self.gamemodelStartedEvents:
            return
        if game.gameno not in self.queuedEmits:
            return

        self.emit("obsGameCreated", game)
        try:
            self.gamemodelStartedEvents[game.gameno].wait()
        except KeyError:
            pass

        for emit in self.queuedEmits[game.gameno]:
            emit()
        del self.queuedEmits[game.gameno]

        wms, bms = self.gamesImObserving[game]
        self.emit("timesUpdate", game.gameno, wms, bms)

    on_icc_position_begin.BLKCMD = DG_POSITION_BEGIN

    def on_icc_send_moves(self, match):
        # gamenumber algebraic-move smith-move time clock
        gameno, san_move, alg_move, time, clock = match.groups()[0].split()
        gameno = int(gameno)
        game = self.connection.games.get_game_by_gameno(gameno)
        fen = ""

        wms, bms = self.gamesImObserving[game]
        if self.curcol == WHITE:
            wms = int(clock) * 60 * 100
        else:
            bms = int(clock) * 60 * 100
        self.gamesImObserving[game] = (wms, bms)

        self.moves_to_go -= 1
        self.ply += 1
        self.curcol = 1 - self.curcol

        self.emit("boardUpdate", gameno, self.ply, self.curcol, san_move, fen,
                  game.wplayer.name, game.bplayer.name, wms, bms)

    on_icc_send_moves.BLKCMD = DG_SEND_MOVES
