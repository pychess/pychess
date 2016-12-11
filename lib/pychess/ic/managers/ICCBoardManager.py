from __future__ import print_function

import threading

from gi.repository import GObject

from pychess.Utils.const import FEN_START, WHITE, reprResult
from pychess.ic.FICSObjects import FICSGame, FICSBoard, FICSPlayer
from pychess.ic.managers.BoardManager import BoardManager, parse_reason
from pychess.ic import IC_POS_OBSERVING, GAME_TYPES, IC_STATUS_PLAYING, IC_POS_EXAMINATING
from pychess.ic.icc import DG_POSITION_BEGIN, DG_SEND_MOVES, DG_MOVE_ALGEBRAIC, DG_MOVE_SMITH, \
    DG_MOVE_TIME, DG_MOVE_CLOCK, DG_MY_GAME_STARTED, DG_MY_GAME_ENDED, DG_STARTED_OBSERVING, \
    DG_MY_GAME_RESULT, DG_STOP_OBSERVING, DG_IS_VARIATION, DG_ISOLATED_BOARD, CN_SPGN, DG_BACKWARD


class ICCBoardManager(BoardManager):

    queued_send_moves = {}

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_dg_line(DG_MY_GAME_STARTED, self.on_icc_my_game_started)
        self.connection.expect_dg_line(DG_STARTED_OBSERVING, self.on_icc_started_observing)
        self.connection.expect_dg_line(DG_STOP_OBSERVING, self.on_icc_stop_observing)
        self.connection.expect_dg_line(DG_MY_GAME_RESULT, self.on_icc_my_game_result)
        self.connection.expect_dg_line(DG_MY_GAME_ENDED, self.on_icc_my_game_ended)

        self.connection.expect_dg_line(DG_POSITION_BEGIN, self.on_icc_position_begin)
        self.connection.expect_dg_line(DG_SEND_MOVES, self.on_icc_send_moves)
        self.connection.expect_dg_line(DG_ISOLATED_BOARD, self.on_icc_isolated_board)
        self.connection.expect_dg_line(DG_BACKWARD, self.on_icc_backward)

        self.connection.expect_cn_line(CN_SPGN, self.on_icc_spgn)

        self.queuedEmits = {}
        self.gamemodelStartedEvents = {}
        self.theGameImPlaying = None
        self.my_game_info = None
        self.gamesImObserving = {}

        # on observe game start, it stores number of moves we expect
        self.moves_to_go = None

        self.connection.client.run_command("set-2 %s 1" % DG_MY_GAME_STARTED)
        self.connection.client.run_command("set-2 %s 1" % DG_STARTED_OBSERVING)
        self.connection.client.run_command("set-2 %s 1" % DG_STOP_OBSERVING)
        self.connection.client.run_command("set-2 %s 1" % DG_MY_GAME_RESULT)
        self.connection.client.run_command("set-2 %s 1" % DG_MY_GAME_ENDED)

        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_ALGEBRAIC)
        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_SMITH)
        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_TIME)
        self.connection.client.run_command("set-2 %s 1" % DG_MOVE_CLOCK)
        self.connection.client.run_command("set-2 %s 1" % DG_POSITION_BEGIN)
        self.connection.client.run_command("set-2 %s 0" % DG_IS_VARIATION)

        self.connection.client.run_command("set-2 %s 1" % DG_SEND_MOVES)
        self.connection.client.run_command("set-2 %s 1" % DG_ISOLATED_BOARD)
        self.connection.client.run_command("set-2 %s 1" % DG_BACKWARD)
        self.connection.client.run_command("set style 13")

        # don't unobserve games when we start a new game, or new observe
        self.connection.client.run_command("set unobserve 0")
        self.connection.lvm.autoFlagNotify()

    def on_icc_spgn(self, data):
        if self.connection.query_game is None:
            return

        game = self.connection.query_game
        game.board = FICSBoard(0, 0, pgn=data)
        game = self.connection.games.get(game)

        self.emit("archiveGamePreview", game)

    def on_icc_isolated_board(self, data):
        print(data)

    def on_icc_backward(self, data):
        # gamenumber backup-count
        gameno, backup_count = data.split()
        gameno = int(gameno)
        backup_count = int(backup_count)

        game = self.connection.games.get_game_by_gameno(gameno)

        if game == self.theGameImPlaying:
            curcol, ply, wms, bms = self.my_game_info
            for i in range(backup_count):
                ply -= 1
                curcol = 1 - curcol
            self.my_game_info = (curcol, ply, wms, bms)

            self.emit("exGameBackward", gameno, backup_count)

    def on_icc_my_game_started(self, data):
        # gamenumber whitename blackname wild-number rating-type rated
        # white-initial white-increment black-initial black-increment
        # played-game {ex-string} white-rating black-rating game-id
        # white-titles black-titles irregular-legality irregular-semantics
        # uses-plunkers fancy-timecontrol promote-to-king
        # 685 Salsicha MaxiBomb 0 Blitz 1 3 0 3 0 1 {} 2147 2197 1729752694 {} {} 0 0 0 {} 0
        # 259 Rikikilord ARMH 0 Blitz 1 2 12 2 12 0 {Ex: Rikikilord 0} 1532 1406 1729752286 {} {} 0 0 0 {} 0
        gameno, wname, bname, wild, rtype, rated, wmin, winc, bmin, binc, played_game, rest = data.split(" ", 11)

        parts = rest.split("}", 1)[1].split()
        wrating = int(parts[0])
        brating = int(parts[1])

        gameno = int(gameno)
        wplayer = self.connection.players.get(wname)
        bplayer = self.connection.players.get(bname)
        game_type = GAME_TYPES[rtype.lower()]

        for player, rating in ((wplayer, wrating), (bplayer, brating)):
            if player.ratings[game_type.rating_type] != rating:
                player.ratings[game_type.rating_type] = rating
                player.emit("ratings_changed", game_type.rating_type, player)

        wms = bms = int(wmin) * 60 * 1000 + int(winc) * 1000
        # TODO: maybe use DG_POSITION_BEGIN2 and DG_PAST_MOVE ?
        fen = FEN_START

        game = FICSGame(wplayer,
                        bplayer,
                        gameno=gameno,
                        rated=rated == "1",
                        game_type=game_type,
                        minutes=int(wmin),
                        inc=int(winc),
                        board=FICSBoard(wms,
                                        bms,
                                        fen=fen))

        if self.connection.examined_game is not None:
            pgnHead = [
                ("Event", "ICC examined game"), ("Site", "chessclub.com"),
                ("White", wname), ("Black", bname), ("Result", "*"),
                ("SetUp", "1"), ("FEN", fen)
            ]
            pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n*\n"

            game.relation = IC_POS_EXAMINATING
            game.game_type = GAME_TYPES["examined"]
            game.board.pgn = pgn

        game = self.connection.games.get(game)

        for player in (wplayer, bplayer):
            if player.status != IC_STATUS_PLAYING:
                player.status = IC_STATUS_PLAYING
            if player.game != game:
                player.game = game

        self.theGameImPlaying = game
        self.my_game_info = (WHITE, 0, wms, bms)
        self.gamemodelStartedEvents[gameno] = threading.Event()
        self.connection.client.run_command("follow")

        if self.connection.examined_game is not None:
            self.emit("exGameCreated", game)
        else:
            self.emit("playGameCreated", game)

    def on_icc_started_observing(self, data):
        gameno, wname, bname, wild, rtype, rated, wmin, winc, bmin, binc, played_game, rest = data.split(" ", 11)

        parts = rest.split("}", 1)[1].split()
        wrating = int(parts[0])
        brating = int(parts[1])

        gameno = int(gameno)
        wplayer = self.connection.players.get(wname)
        bplayer = self.connection.players.get(bname)
        game_type = GAME_TYPES[rtype.lower()]

        for player, rating in ((wplayer, wrating), (bplayer, brating)):
            if player.ratings[game_type.rating_type] != rating:
                player.ratings[game_type.rating_type] = rating
                player.emit("ratings_changed", game_type.rating_type, player)

        relation = IC_POS_OBSERVING
        wms = bms = int(wmin) * 60 * 1000 + int(winc) * 1000

        game = FICSGame(wplayer,
                        bplayer,
                        gameno=gameno,
                        rated=rated == "1",
                        game_type=game_type,
                        minutes=int(wmin),
                        inc=int(winc),
                        relation=relation)

        game = self.connection.games.get(game, emit=False)

        self.gamesImObserving[game] = (WHITE, 0, wms, bms)
        self.queued_send_moves[game.gameno] = []
        self.queuedEmits[game.gameno] = []
        self.gamemodelStartedEvents[game.gameno] = threading.Event()

    def on_icc_stop_observing(self, data):
        gameno = int(data.split()[0])
        try:
            del self.gamemodelStartedEvents[gameno]
            game = self.connection.games.get_game_by_gameno(gameno)
        except KeyError:
            return
        self.emit("obsGameUnobserved", game)

    def on_icc_my_game_ended(self, data):
        gameno = data.split()[0]
        print("my_game_ended", gameno)

    def on_icc_my_game_result(self, data):
        # gamenumber become-examined game_result_code score_string2 description-string ECO
        # 1242 1 Res 1-0 {Black resigns} {D89}
        parts = data.split(" ", 4)
        gameno, ex, result_code, result, rest = parts
        gameno = int(gameno)
        comment, rest = rest[2:].split("}", 1)

        game = self.connection.games.get_game_by_gameno(gameno)
        wname = game.wplayer.name
        bname = game.bplayer.name

        result, reason = parse_reason(
            reprResult.index(result),
            comment,
            wname=wname)

        try:
            wplayer = self.connection.players.get(wname)
            wplayer.restore_previous_status()
            # no status update will be sent by
            # FICS if the player doesn't become available, so we restore
            # previous status first (not necessarily true, but the best guess)
        except KeyError:
            print("%s not in self.connections.players - creating" % wname)
            wplayer = FICSPlayer(wname)

        try:
            bplayer = self.connection.players.get(bname)
            bplayer.restore_previous_status()
        except KeyError:
            print("%s not in self.connections.players - creating" % bname)
            bplayer = FICSPlayer(bname)

        game = FICSGame(wplayer,
                        bplayer,
                        gameno=int(gameno),
                        result=result,
                        reason=reason)
        if wplayer.game is not None:
            game.rated = wplayer.game.rated
        game = self.connection.games.get(game, emit=False)
        self.connection.games.game_ended(game)
        # Do this last to give anybody connected to the game's signals a chance
        # to disconnect from them first
        wplayer.game = None
        bplayer.game = None

    def on_icc_position_begin(self, data):
        # gamenumber {initial-FEN} nmoves-to-follow
        gameno, right_part = data.split("{")
        gameno = int(gameno)

        game = self.connection.games.get_game_by_gameno(gameno)

        if game == self.theGameImPlaying:
            curcol, ply, wms, bms = self.my_game_info
            self.emit("boardUpdate", gameno, 0, WHITE, None, FEN_START,
                      game.wplayer.name, game.bplayer.name, wms, bms)
        else:
            fen, moves_to_go = right_part.split("}")
            self.moves_to_go = int(moves_to_go)
            curcol, ply, wms, bms = self.gamesImObserving[game]
            # TODO: get ply, curcol from fen
            ply = 0
            curcol = WHITE
            self.gamesImObserving[game] = (curcol, ply, wms, bms)

    def on_icc_send_moves(self, data):
        # gamenumber algebraic-move smith-move time clock
        send_moves = data
        gameno, san_move, alg_move, time, clock = send_moves.split()
        gameno = int(gameno)

        game = self.connection.games.get_game_by_gameno(gameno)

        fen = ""

        if game == self.theGameImPlaying:
            curcol, ply, wms, bms = self.my_game_info
        else:
            curcol, ply, wms, bms = self.gamesImObserving[game]

        if curcol == WHITE:
            wms = int(clock) * 1000
        else:
            bms = int(clock) * 1000

        ply += 1
        curcol = 1 - curcol

        if game == self.theGameImPlaying:
            self.my_game_info = (curcol, ply, wms, bms)
        else:
            self.gamesImObserving[game] = (curcol, ply, wms, bms)

        if gameno in self.queued_send_moves:
            self.queued_send_moves[gameno].append(send_moves)
            if len(self.queued_send_moves[gameno]) < self.moves_to_go:
                return

        if self.moves_to_go is None:
            self.emit("boardUpdate", gameno, ply, curcol, san_move, fen,
                      game.wplayer.name, game.bplayer.name, wms, bms)
            self.emit("timesUpdate", gameno, wms, bms)
        else:
            if game.gameno not in self.gamemodelStartedEvents:
                return
            if game.gameno not in self.queuedEmits:
                return

            pgnHead = [
                ("Event", "ICC %s %s game" % (game.display_rated.lower(), game.game_type.fics_name)),
                ("Site", "chessclub.com"),
                ("White", game.wplayer.name),
                ("Black", game.bplayer.name),
                ("Result", "*"),
                ("TimeControl", "%d+%d" % (game.minutes * 60, game.inc)),
            ]
            wrating = game.wplayer.ratings[game.game_type.rating_type]
            brating = game.bplayer.ratings[game.game_type.rating_type]
            if wrating != 0:
                pgnHead += [("WhiteElo", wrating)]
            if brating != 0:
                pgnHead += [("BlackElo", brating)]

            pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n"

            moves = self.queued_send_moves[gameno]
            ply = 0
            for send_moves in moves:
                gameno_, san_move, alg_move, time, clock = send_moves.split()
                if ply % 2 == 0:
                    pgn += "%d. " % (ply // 2 + 1)
                pgn += "%s {[%%emt %s]} " % (san_move, time)
                ply += 1
            pgn += "*\n"
            del self.queued_send_moves[gameno]
            self.moves_to_go = None

            wms = bms = 0
            game = FICSGame(game.wplayer,
                            game.bplayer,
                            game_type=game.game_type,
                            result=game.result,
                            rated=game.rated,
                            minutes=game.minutes,
                            inc=game.inc,
                            board=FICSBoard(wms,
                                            bms,
                                            pgn=pgn))
            in_progress = True
            if in_progress:
                game.gameno = gameno
            else:
                if gameno is not None:
                    game.gameno = gameno
                # game.reason = reason
            game = self.connection.games.get(game, emit=False)

            self.emit("obsGameCreated", game)
            try:
                self.gamemodelStartedEvents[game.gameno].wait()
            except KeyError:
                pass

            for emit in self.queuedEmits[game.gameno]:
                emit()
            del self.queuedEmits[game.gameno]

            curcol, ply, wms, bms = self.gamesImObserving[game]
            self.emit("timesUpdate", game.gameno, wms, bms)
