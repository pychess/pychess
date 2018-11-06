
import asyncio
import itertools
import re

from gi.repository import Gtk, GObject


from pychess.compat import create_task
from pychess.Utils import wait_signal
from pychess.System import conf
from pychess.System.Log import log
from pychess.widgets import mainwindow
from pychess.Utils.Move import Move
from pychess.Utils.Board import Board
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import toSAN, toAN, parseAny
from pychess.Utils.Offer import Offer
from pychess.Utils.const import ANALYZING, INVERSE_ANALYZING, DRAW, WHITEWON, BLACKWON, \
    WON_ADJUDICATION, DRAW_OFFER, ACTION_ERROR_NONE_TO_ACCEPT, CASTLE_KK, WHITE, \
    CASTLE_SAN, FISCHERRANDOMCHESS, BLACK, reprSign, RESIGNATION
from pychess.Utils.logic import validate, getMoveKillingKing
from pychess.Utils.lutils.ldata import MATE_VALUE
from pychess.Utils.lutils.lmove import ParsingError
from pychess.Variants import variants
from pychess.Players.Player import PlayerIsDead, TurnInterrupt, InvalidMove
from .ProtocolEngine import ProtocolEngine, TIME_OUT_SECOND


movere = re.compile(r"""
    (                   # group start
    (?:                 # non grouping parenthesis start
    [PKQRBN]?            # piece
    [a-h]?[1-8]?        # unambiguous column or line
    x?                  # capture
    @?                  # drop
    [a-h][1-8]          # destination square
    =?[QRBN]?           # promotion
    |O\-O(?:\-O)?       # castling
    |0\-0(?:\-0)?       # castling
    )                   # non grouping parenthesis end
    [+#]?               # check/mate
    )                   # group end
    \s*                 # any whitespace
    """, re.VERBOSE)

d_plus_dot_expr = re.compile(r"\d+\.")

anare = re.compile("""
    ^                        # beginning of string
    (\s*                     #
    \d+ [+\-\.]?             # The ply analyzed. Some engines end it with a dot, minus or plus
    \s+)                     #
    (-?Mat\s*\d+ | [+\-\d\.]+) # The score found in centipawns.
                             #   Mat1 is used by gnuchess to specify mate in one.
                             #   otherwise we should support a signed float
    \s+                      #
    ([\d\.]+)                # The time used in centi-seconds
    \s+                      #
    ([\d\.]+)                # Number of nodes visited
    \s+                      #
    (.+)                     # The Principal-Variation. With or without move numbers
    \s*                      #
    $                        # end of string
    """, re.VERBOSE)

# anare = re.compile("\(d+)\.?\s+ (Mat\d+|[-\d\.]+) \s+ \d+\s+\d+\s+((?:%s\s*)+)" % mov)

whitespaces = re.compile(r"\s+")


# There is no way in the CECP protocol to determine if an engine not answering
# the protover=2 handshake with done=1 is old or just very slow. Thus we
# need a timeout after which we conclude the engine is 'protover=1' and will
# never answer.
# XBoard will only give 2 seconds, but as we are quite sure that
# the engines support the protocol, we can add more. We don't add
# infinite time though, just in case.
# The engine can get more time by sending done=0


class CECPEngine(ProtocolEngine):
    def __init__(self, subprocess, color, protover, md5):
        ProtocolEngine.__init__(self, subprocess, color, protover, md5)

        self.features = {
            "ping": 0,
            "setboard": 0,
            "playother": 0,
            "san": 0,
            "usermove": 0,
            "time": 1,
            "draw": 1,
            "sigint": 0,
            "sigterm": 0,
            "reuse": 0,
            "analyze": 0,
            "myname": ', '.join(self.defname),
            "variants": None,
            "colors": 1,
            "ics": 0,
            "name": 0,
            "pause": 0,
            "nps": 0,
            "debug": 0,
            "memory": 0,
            "smp": 0,
            "egt": '',
            "option": '',
            "exclude": 0,
            "done": None,
        }

        self.supported_features = [
            "ping", "setboard", "san", "usermove", "time", "draw", "sigint",
            "analyze", "myname", "variants", "colors", "pause", "done", "egt",
            "debug", "smp", "memory", "option"
        ]

        self.options = {}
        self.options["Ponder"] = {"name": "Ponder",
                                  "type": "check",
                                  "default": False}

        self.name = None

        self.board = Board(setup=True)

        # if self.engineIsInNotPlaying == True, engine is in "force" mode,
        # i.e. not thinking or playing, but still verifying move legality
        self.engineIsInNotPlaying = False
        self.engineIsAnalyzing = False
        self.movenext = False
        self.waitingForMove = False
        self.readyForMoveNowCommand = False
        self.timeHandicap = 1

        self.lastping = 0
        self.lastpong = 0

        self.queue = asyncio.Queue()
        self.parse_line_task = create_task(self.parseLine(self.engine))
        self.died_cid = self.engine.connect("died", lambda e: self.queue.put_nowait("die"))
        self.invalid_move = None

        self.optionQueue = []
        self.undoQueue = []
        self.ready_moves_event = asyncio.Event()

        self.cids = [
            self.connect_after("readyForOptions", self.__onReadyForOptions),
            self.connect_after("readyForMoves", self.__onReadyForMoves),
        ]

    # Starting the game

    def prestart(self):
        print("xboard", file=self.engine)
        if self.protover == 1:
            # start a new game (CECPv1 engines):
            print("new", file=self.engine)

            # we are now ready for options:
            self.emit("readyForOptions")
        elif self.protover == 2:
            # start advanced protocol initialisation:
            print("protover 2", file=self.engine)

            # we don't start a new game for CECPv2 here,
            # we will do it after feature accept/reject is completed.

    def start(self, event, is_dead):
        create_task(self.__startBlocking(event, is_dead))

    @asyncio.coroutine
    def __startBlocking(self, event, is_dead):
        if self.protover == 1:
            self.emit("readyForMoves")
            return_value = "ready"

        if self.protover == 2:
            try:
                return_value = yield from asyncio.wait_for(self.queue.get(), TIME_OUT_SECOND)
                if return_value == "not ready":
                    return_value = yield from asyncio.wait_for(self.queue.get(), TIME_OUT_SECOND)
                    # Gaviota sends done=0 after "xboard" and after "protover 2" too
                    if return_value == "not ready":
                        return_value = yield from asyncio.wait_for(self.queue.get(), TIME_OUT_SECOND)
            except asyncio.TimeoutError:
                log.warning("Got timeout error", extra={"task": self.defname})
                is_dead.add(True)
            except Exception:
                log.warning("Unknown error", extra={"task": self.defname})
                is_dead.add(True)
            else:
                if return_value == "die":
                    is_dead.add(True)
                assert return_value == "ready" or return_value == "del"

        if event is not None:
            event.set()

    def __onReadyForOptions(self, self_):
        # We always want post turned on so the Engine Output sidebar can
        # show those things  -Jonas Thiem
        print("post", file=self.engine)

        for command in self.optionQueue:
            print(command, file=self.engine)

    def __onReadyForMoves(self, self_):
        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            # workaround for crafty not sending analysis after it has found a mating line
            # http://code.google.com/p/pychess/issues/detail?id=515
            if "crafty" in self.features["myname"].lower():
                print("noise 0", file=self.engine)

            self.__sendAnalyze(self.mode == INVERSE_ANALYZING)
        self.ready_moves_event.set()
        self.readyMoves = True

    # Ending the game

    def end(self, status, reason):
        self.parse_line_task.cancel()
        if self.engine.handler_is_connected(self.died_cid):
            self.engine.disconnect(self.died_cid)
        if self.handler_is_connected(self.analyze_cid):
            self.disconnect(self.analyze_cid)
        for cid in self.cids:
            if self.handler_is_connected(cid):
                self.disconnect(cid)
        self.board = None

        if self.connected:
            # We currently can't fillout the comment "field" as the repr strings
            # for reasons and statuses lies in Main.py
            # Creating Status and Reason class would solve this
            if status == DRAW:
                print("result 1/2-1/2 {?}", file=self.engine)
            elif status == WHITEWON:
                print("result 1-0 {?}", file=self.engine)
            elif status == BLACKWON:
                print("result 0-1 {?}", file=self.engine)
            else:
                print("result * {?}", file=self.engine)

            if reason == WON_ADJUDICATION:
                self.queue.put_nowait("invalid")

                # Make sure the engine exits and do some cleaning
            self.kill(reason)

    def kill(self, reason):
        """ Kills the engine, starting with the 'quit' command, then sigterm and
            eventually sigkill.
            Returns the exitcode, or if engine have already been killed, returns
            None """
        if self.connected:
            self.connected = False
            try:
                try:
                    print("quit", file=self.engine)
                    self.queue.put_nowait("del")
                    self.engine.terminate()

                except OSError as err:
                    # No need to raise on a hang up error, as the engine is dead
                    # anyways
                    if err.errno == 32:
                        log.warning("Hung up Error", extra={"task": self.defname})
                        return err.errno
                    else:
                        raise

            finally:
                # Clear the analyzed data, if any
                self.emit("analyze", [])

    # Send the player move updates

    def set_board(self, board):
        self.setBoardList([board], [])

    def setBoard(self, board, search=True):
        def coro():
            if self.engineIsAnalyzing:
                self.__stop_analyze()
                yield from asyncio.sleep(0.1)

            self.setBoardList([board], [])
            if search:
                self.__sendAnalyze(self.mode == INVERSE_ANALYZING)
        create_task(coro())

    def putMove(self, board1, move, board2):
        """ Sends the engine the last move made (for spectator engines).
            @param board1: The current board
            @param move: The last move made
            @param board2: The board before the last move was made
        """
        def coro():
            if self.engineIsAnalyzing:
                self.__stop_analyze()
                yield from asyncio.sleep(0.1)

            self.setBoardList([board1], [])
            if not self.analyzing_paused:
                self.__sendAnalyze(self.mode == INVERSE_ANALYZING)
        create_task(coro())

    @asyncio.coroutine
    def makeMove(self, board1, move, board2):
        """ Gets a move from the engine (for player engines).
            @param board1: The current board
            @param move: The last move made
            @param board2: The board before the last move was made
            @return: The move the engine decided to make
        """
        log.debug("makeMove: move=%s self.movenext=%s board1=%s board2=%s self.board=%s" % (
            move, self.movenext, board1, board2, self.board), extra={"task": self.defname})
        assert self.readyMoves

        if self.board == board1 or not board2 or self.movenext:
            self.board = board1
            self.__tellEngineToPlayCurrentColorAndMakeMove()
            self.movenext = False
        else:
            self.board = board1
            self.__usermove(board2, move)

            if self.engineIsInNotPlaying:
                self.__tellEngineToPlayCurrentColorAndMakeMove()

        self.waitingForMove = True
        self.readyForMoveNowCommand = True

        # Parse outputs
        status = yield from self.queue.get()
        if status == "not ready":
            log.warning(
                "Engine seems to be protover=2, but is treated as protover=1",
                extra={"task": self.defname})
            status = yield from self.queue.get()
        if status == "ready":
            status = yield from self.queue.get()
        if status == "invalid":
            raise InvalidMove
        if status == "del" or status == "die":
            raise PlayerIsDead("Killed by foreign forces")
        if status == "int":
            raise TurnInterrupt

        self.waitingForMove = False
        self.readyForMoveNowCommand = False
        assert isinstance(status, Move), status
        return status

    def updateTime(self, secs, opsecs):
        if self.features["time"]:
            print("time %s" % int(secs * 100 * self.timeHandicap),
                  file=self.engine)
            print("otim %s" % int(opsecs * 100), file=self.engine)

    # Standard options

    def setOptionAnalyzing(self, mode):
        self.mode = mode

    def setOptionInitialBoard(self, model):
        @asyncio.coroutine
        def coro():
            yield from self.ready_moves_event.wait()
            # We don't use the optionQueue here, as set board prints a whole lot of
            # stuff. Instead we just call it.
            self.setBoardList(model.boards[:], model.moves[:])
        create_task(coro())

    def setBoardList(self, boards, moves):
        # Notice: If this method is to be called while playing, the engine will
        # need 'new' and an arrangement similar to that of 'pause' to avoid
        # the current thought move to appear
        if self.mode not in (ANALYZING, INVERSE_ANALYZING):
            self.__tellEngineToStopPlayingCurrentColor()

        self.__setBoard(boards[0])

        self.board = boards[-1]
        for board, move in zip(boards[:-1], moves):
            self.__usermove(board, move)

        if self.mode in (ANALYZING, INVERSE_ANALYZING):
            self.board = boards[-1]
        if self.mode == INVERSE_ANALYZING:
            self.board = self.board.switchColor()

        # The called of setBoardList will have to repost/analyze the
        # analyzer engines at this point.

    def setOptionVariant(self, variant):
        if self.features["variants"] is None:
            log.warning("setOptionVariant: engine doesn't support variants",
                        extra={"task": self.defname})
            return

        if variant in variants.values() and not variant.standard_rules:
            assert variant.cecp_name in self.features["variants"], \
                "%s doesn't support %s variant" % (self, variant.cecp_name)
            self.optionQueue.append("variant %s" % variant.cecp_name)

    #    Strength system                               #
    #          Strength  Depth  Ponder  Time handicap  #
    #          1         1      o       1,258%         #
    #          2         2      o       1,584%         #
    #          3         3      o       1.995%         #
    #                                                  #
    #         19         o      x       79,43%         #
    #         20         o      x       o              #

    def setOptionStrength(self, strength, forcePonderOff):
        self.strength = strength

        if strength <= 19:
            self.__setTimeHandicap(0.01 * 10 ** (strength / 10.))

        if strength <= 18:
            self.__setDepth(strength)

        # Crafty ofers 100 skill levels
        if "crafty" in self.features["myname"].lower() and strength <= 19:
            self.optionQueue.append("skill %s" % strength * 5)

        self.__setPonder(strength >= 19 and not forcePonderOff)

        if strength == 20:
            if "gaviota" in self.features["egt"]:
                self.optionQueue.append("egtpath gaviota %s" % conf.get("egtb_path"))
        else:
            self.optionQueue.append("random")

    def __setDepth(self, depth):
        self.optionQueue.append("sd %d" % depth)

    def __setTimeHandicap(self, timeHandicap):
        self.timeHandicap = timeHandicap

    def __setPonder(self, ponder):
        if ponder:
            self.optionQueue.append("hard")
        else:
            self.optionQueue.append("hard")
            self.optionQueue.append("easy")

    def setOptionTime(self, secs, gain, moves):
        # Notice: In CECP we apply time handicap in updateTime, not in
        #         setOptionTime.

        minutes = int(secs / 60)
        secs = int(secs % 60)
        mins = str(minutes)
        if secs:
            mins += ":" + str(secs)

        self.optionQueue.append("level %s %s %d" % (moves, mins, gain))

    # Option handling

    def setOption(self, key, value):
        """ Set an option, which will be sent to the engine, after the
            'readyForOptions' signal has passed.
            If you want to know the possible options, you should go to
            engineDiscoverer or use the hasOption method
            while you are in your 'readyForOptions' signal handler """
        if self.readyMoves:
            log.warning(
                "Options set after 'readyok' are not sent to the engine",
                extra={"task": self.defname})
        if key == "cores":
            self.optionQueue.append("cores %s" % value)
        elif key == "memory":
            self.optionQueue.append("memory %s" % value)
        elif key.lower() == "ponder":
            self.__setPonder(value == 1)
        else:
            self.optionQueue.append("option %s=%s" % (key, value))

    # Interacting with the player

    def pause(self):
        """ Pauses engine using the "pause" command if available. Otherwise put
            engine in force mode. By the specs the engine shouldn't ponder in
            force mode, but some of them do so anyways. """

        log.debug("pause: self=%s" % self, extra={"task": self.defname})
        if self.isAnalyzing():
            self.__stop_analyze()
            self.analyzing_paused = True
        else:
            self.engine.pause()
        return

    def resume(self):
        log.debug("resume: self=%s" % self, extra={"task": self.defname})
        if self.isAnalyzing():
            self.__sendAnalyze(self.mode == INVERSE_ANALYZING)
            self.analyzing_paused = False
        else:
            self.engine.resume()
        return

    def hurry(self):
        log.debug("hurry: self.waitingForMove=%s self.readyForMoveNowCommand=%s" % (
            self.waitingForMove, self.readyForMoveNowCommand), extra={"task": self.defname})
        if self.waitingForMove and self.readyForMoveNowCommand:
            self.__tellEngineToMoveNow()
            self.readyForMoveNowCommand = False

    def spectatorUndoMoves(self, moves, gamemodel):
        if self.analyzing_paused:
            return

        log.debug("spectatorUndoMoves: moves=%s gamemodel.ply=%s gamemodel.boards[-1]=%s self.board=%s" % (
            moves, gamemodel.ply, gamemodel.boards[-1], self.board), extra={"task": self.defname})

        for i in range(moves):
            print("undo", file=self.engine)

        self.board = gamemodel.boards[-1]

    def playerUndoMoves(self, moves, gamemodel):
        log.debug("CECPEngine.playerUndoMoves: moves=%s self=%s gamemodel.curplayer=%s" %
                  (moves, self, gamemodel.curplayer), extra={"task": self.defname})

        self.board = gamemodel.boards[-1]

        self.__tellEngineToStopPlayingCurrentColor()

        for i in range(moves):
            print("undo", file=self.engine)

        if gamemodel.curplayer != self and moves % 2 == 1 or \
                (gamemodel.curplayer == self and moves % 2 == 0):
            # Interrupt if we were searching, but should no longer do so
            log.debug("CECPEngine.playerUndoMoves: putting TurnInterrupt into self.move_queue %s" % self.name, extra={"task": self.defname})
            self.queue.put_nowait("int")

    # Offer handling

    def offer(self, offer):
        if offer.type == DRAW_OFFER:
            if self.features["draw"]:
                print("draw", file=self.engine)
        else:
            self.emit("accept", offer)

    def offerError(self, offer, error):
        if self.features["draw"]:
            # We don't keep track if engine draws are offers or accepts. We just
            # Always assume they are accepts, and if they are not, we get this
            # error and emit offer instead
            if offer.type == DRAW_OFFER and error == ACTION_ERROR_NONE_TO_ACCEPT:
                self.emit("offer", Offer(DRAW_OFFER))

    # Internal

    def __usermove(self, board, move):
        if self.features["usermove"]:
            self.engine.write("usermove ")

        if self.features["san"]:
            print(toSAN(board, move), file=self.engine)
        else:
            castle_notation = CASTLE_KK
            if board.variant == FISCHERRANDOMCHESS:
                castle_notation = CASTLE_SAN
            print(
                toAN(board,
                     move,
                     short=True,
                     castleNotation=castle_notation),
                file=self.engine)

    def __tellEngineToMoveNow(self):
        if self.features["sigint"]:
            self.engine.sigint()
        print("?", file=self.engine)

    def __tellEngineToStopPlayingCurrentColor(self):
        print("force", file=self.engine)
        self.engineIsInNotPlaying = True

    def __tellEngineToPlayCurrentColorAndMakeMove(self):
        self.__printColor()
        print("go", file=self.engine)
        self.engineIsInNotPlaying = False

    def __stop_analyze(self):
        if self.engineIsAnalyzing:
            print("exit", file=self.engine)
            # Some engines (crafty, gnuchess) doesn't respond to exit command
            # we try to force them to stop with an empty board fen
            print("setboard 8/8/8/8/8/8/8/8 w - - 0 1", file=self.engine)
            self.engineIsAnalyzing = False

    def __sendAnalyze(self, inverse=False):
        if inverse and self.board.board.opIsChecked():
            # Many engines don't like positions able to take down enemy
            # king. Therefore we just return the "kill king" move
            # automaticaly
            self.emit("analyze", [(self.board.ply, [toAN(
                self.board, getMoveKillingKing(self.board))], MATE_VALUE - 1, "1", "")])
            return

        print("post", file=self.engine)
        print("analyze", file=self.engine)
        self.engineIsAnalyzing = True

        if not conf.get("infinite_analysis"):
            loop = asyncio.get_event_loop()
            loop.call_later(conf.get("max_analysis_spin"), self.__stop_analyze)

    def __printColor(self):
        if self.features["colors"]:  # or self.mode == INVERSE_ANALYZING:
            if self.board.color == WHITE:
                print("white", file=self.engine)
            else:
                print("black", file=self.engine)

    def __setBoard(self, board):
        if self.features["setboard"]:
            self.__tellEngineToStopPlayingCurrentColor()
            fen = board.asFen(enable_bfen=False)
            if self.mode == INVERSE_ANALYZING:
                fen_arr = fen.split()
                if not self.board.board.opIsChecked():
                    if fen_arr[1] == "b":
                        fen_arr[1] = "w"
                    else:
                        fen_arr[1] = "b"
                fen = " ".join(fen_arr)
            print("setboard %s" % fen, file=self.engine)
        else:
            # Kludge to set black to move, avoiding the troublesome and now
            # deprecated "black" command. - Equal to the one xboard uses
            self.__tellEngineToStopPlayingCurrentColor()
            if board.color == BLACK:
                print("a2a3", file=self.engine)
            print("edit", file=self.engine)
            print("#", file=self.engine)
            for color in WHITE, BLACK:
                for y_loc, row in enumerate(board.data):
                    for x_loc, piece in row.items():
                        if not piece or piece.color != color:
                            continue
                        sign = reprSign[piece.sign]
                        cord = repr(Cord(x_loc, y_loc))
                        print(sign + cord, file=self.engine)
                print("c", file=self.engine)
            print(".", file=self.engine)

    # Parsing

    @asyncio.coroutine
    def parseLine(self, proc):
        while True:
            line = yield from wait_signal(proc, 'line')
            if not line:
                break
            else:
                line = line[1]
                if line[0:1] == "#":
                    # Debug line which we shall ignore as specified in CECPv2 specs
                    continue

        #        log.debug("__parseLine: line=\"%s\"" % line.strip(), extra={"task":self.defname})
                parts = whitespaces.split(line.strip())
                if parts[0] == "pong":
                    self.lastpong = int(parts[1])
                    continue

                # Illegal Move
                if parts[0].lower().find("illegal") >= 0:
                    log.warning("__parseLine: illegal move: line=\"%s\", board=%s" % (
                        line.strip(), self.board), extra={"task": self.defname})
                    if parts[-2] == "sd" and parts[-1].isdigit():
                        print("depth", parts[-1], file=self.engine)
                    continue

                # A Move (Perhaps)
                if self.board:
                    if parts[0] == "move":
                        movestr = parts[1]
                    # Old Variation
                    elif d_plus_dot_expr.match(parts[0]) and parts[1] == "...":
                        movestr = parts[2]
                    else:
                        movestr = False

                    if movestr:
                        self.waitingForMove = False
                        self.readyForMoveNowCommand = False
                        if self.engineIsInNotPlaying:
                            # If engine was set in pause just before the engine sent its
                            # move, we ignore it. However the engine has to know that we
                            # ignored it, and thus we step it one back
                            log.info("__parseLine: Discarding engine's move: %s" %
                                     movestr,
                                     extra={"task": self.defname})
                            print("undo", file=self.engine)
                            continue
                        else:
                            try:
                                move = parseAny(self.board, movestr)
                            except ParsingError:
                                self.invalid_move = movestr
                                log.info(
                                    "__parseLine: ParsingError engine move: %s %s"
                                    % (movestr, self.board),
                                    extra={"task": self.defname})
                                self.end(WHITEWON if self.board.color == BLACK else
                                         BLACKWON, WON_ADJUDICATION)
                                continue

                            if validate(self.board, move):
                                self.board = None
                                self.queue.put_nowait(move)
                                continue
                            else:
                                self.invalid_move = movestr
                                log.info(
                                    "__parseLine: can't validate engine move: %s %s"
                                    % (movestr, self.board),
                                    extra={"task": self.defname})
                                self.end(WHITEWON if self.board.color == BLACK else
                                         BLACKWON, WON_ADJUDICATION)
                                continue

                # Analyzing
                if self.engineIsInNotPlaying:
                    if parts[:4] == ["0", "0", "0", "0"]:
                        # Crafty doesn't analyze until it is out of book
                        print("book off", file=self.engine)
                        continue

                    match = anare.match(line)
                    if match:
                        depth, score, time, nodes, moves = match.groups()

                        if "mat" in score.lower() or "#" in moves:
                            # Will look either like -Mat 3 or Mat3
                            scoreval = MATE_VALUE
                            if score.startswith('-'):
                                scoreval = -scoreval
                        else:
                            scoreval = int(score)

                        nps = str(int(int(nodes) / (int(time) / 100))) if int(time) > 0 else ""

                        mvstrs = movere.findall(moves)
                        if mvstrs:
                            self.emit("analyze", [(self.board.ply, mvstrs, scoreval, depth.strip(), nps)])

                        continue

                # Offers draw
                if parts[0:2] == ["offer", "draw"]:
                    self.emit("accept", Offer(DRAW_OFFER))
                    continue

                # Resigns
                if parts[0] == "resign" or \
                        (parts[0] == "tellics" and parts[1] == "resign"):  # buggy crafty

                    # Previously: if "resign" in parts,
                    # however, this is too generic, since "hint", "bk",
                    # "feature option=.." and possibly other, future CECPv2
                    # commands can validly contain the word "resign" without this
                    # being an intentional resign offer.

                    self.emit("offer", Offer(RESIGNATION))
                    continue

                # if parts[0].lower() == "error":
                #    continue

                # Tell User Error
                if parts[0] == "tellusererror":
                    # We don't want to see our stop analyzer hack as an error message
                    if "8/8/8/8/8/8/8/8" in "".join(parts[1:]):
                        continue
                    # Create a non-modal non-blocking message dialog with the error:
                    dlg = Gtk.MessageDialog(mainwindow(),
                                            flags=0,
                                            type=Gtk.MessageType.WARNING,
                                            buttons=Gtk.ButtonsType.CLOSE,
                                            message_format=None)

                    # Use the engine name if already known, otherwise the defname:
                    displayname = self.name
                    if not displayname:
                        displayname = self.defname

                    # Compose the dialog text:
                    dlg.set_markup(GObject.markup_escape_text(_(
                        "The engine %s reports an error:") % displayname) + "\n\n" +
                        GObject.markup_escape_text(" ".join(parts[1:])))

                    # handle response signal so the "Close" button works:
                    dlg.connect("response", lambda dlg, x: dlg.destroy())

                    dlg.show_all()
                    continue

                # Tell Somebody
                if parts[0][:4] == "tell" and \
                        parts[0][4:] in ("others", "all", "ics", "icsnoalias"):

                    log.info("Ignoring tell %s: %s" %
                             (parts[0][4:], " ".join(parts[1:])))
                    continue

                if "feature" in parts:
                    # Some engines send features after done=1, so we will iterate after done=1 too
                    done1 = False
                    # We skip parts before 'feature', as some engines give us lines like
                    # White (1) : feature setboard=1 analyze...e="GNU Chess 5.07" done=1
                    parts = parts[parts.index("feature"):]
                    for i, pair in enumerate(parts[1:]):

                        # As "parts" is split with no thoughs on quotes or double quotes
                        # we need to do some extra handling.

                        if pair.find("=") < 0:
                            continue
                        key, value = pair.split("=", 1)

                        if key not in self.features:
                            continue

                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]

                        # If our pair was unfinished, like myname="GNU, we search the
                        # rest of the pairs for a quotating mark.
                        elif value[0] == '"':
                            rest = value[1:] + " " + " ".join(parts[2 + i:])
                            j = rest.find('"')
                            if j == -1:
                                log.warning("Missing endquotation in %s feature",
                                            extra={"task": self.defname})
                                value = rest
                            else:
                                value = rest[:j]

                        elif value.isdigit():
                            value = int(value)

                        if key in self.supported_features:
                            print("accepted %s" % key, file=self.engine)
                        else:
                            print("rejected %s" % key, file=self.engine)

                        if key == "done":
                            if value == 1:
                                done1 = True
                                continue
                            elif value == 0:
                                log.info("Adds %d seconds timeout" % TIME_OUT_SECOND,
                                         extra={"task": self.defname})
                                # This'll buy you some more time
                                self.queue.put_nowait("not ready")
                                break

                        if key == "smp" and value == 1:
                            self.options["cores"] = {"name": "cores",
                                                     "type": "spin",
                                                     "default": 1,
                                                     "min": 1,
                                                     "max": 64}
                        elif key == "memory" and value == 1:
                            self.options["memory"] = {"name": "memory",
                                                      "type": "spin",
                                                      "default": 32,
                                                      "min": 1,
                                                      "max": 4096}
                        elif key == "option" and key != "done":
                            option = self.__parse_option(value)
                            self.options[option["name"]] = option
                        else:
                            self.features[key] = value

                        if key == "myname" and not self.name:
                            self.setName(value)

                    if done1:
                        # Start a new game before using the engine:
                        # (CECPv2 engines)
                        print("new", file=self.engine)

                        # We are now ready for play:
                        self.emit("readyForOptions")
                        self.emit("readyForMoves")
                        self.queue.put_nowait("ready")

                # A hack to get better names in protover 1.
                # Unfortunately it wont work for now, as we don't read any lines from
                # protover 1 engines. When should we stop?
                if self.protover == 1:
                    if self.defname[0] in ''.join(parts):
                        basis = self.defname[0]
                        name = ' '.join(itertools.dropwhile(
                            lambda part: basis not in part, parts))
                        self.features['myname'] = name
                        if not self.name:
                            self.setName(name)

    def __parse_option(self, option):
        if " -check " in option:
            name, value = option.split(" -check ")
            return {"type": "check", "name": name, "default": bool(int(value))}
        elif " -spin " in option:
            name, value = option.split(" -spin ")
            defv, minv, maxv = value.split()
            return {"type": "spin",
                    "name": name,
                    "default": int(defv),
                    "min": int(minv),
                    "max": int(maxv)}
        elif " -slider " in option:
            name, value = option.split(" -slider ")
            defv, minv, maxv = value.split()
            return {"type": "spin",
                    "name": name,
                    "default": int(defv),
                    "min": int(minv),
                    "max": int(maxv)}
        elif " -string " in option:
            name, value = option.split(" -string ")
            return {"type": "text", "name": name, "default": value}
        elif " -file " in option:
            name, value = option.split(" -file ")
            return {"type": "text", "name": name, "default": value}
        elif " -path " in option:
            name, value = option.split(" -path ")
            return {"type": "text", "name": name, "default": value}
        elif " -combo " in option:
            name, value = option.split(" -combo ")
            choices = list(map(str.strip, value.split("///")))
            default = ""
            for choice in choices:
                if choice.startswith("*"):
                    index = choices.index(choice)
                    default = choice[1:]
                    choices[index] = default
                    break
            return {"type": "combo",
                    "name": name,
                    "default": default,
                    "choices": choices}
        elif " -button" in option:
            pos = option.find(" -button")
            return {"type": "button", "name": option[:pos]}
        elif " -save" in option:
            pos = option.find(" -save")
            return {"type": "button", "name": option[:pos]}
        elif " -reset" in option:
            pos = option.find(" -reset")
            return {"type": "button", "name": option[:pos]}

    # Info

    def canAnalyze(self):
        assert self.ready, "Still waiting for done=1"
        return self.features["analyze"]

    def getAnalysisLines(self):
        return 1

    def minAnalysisLines(self):
        return 1

    def maxAnalysisLines(self):
        return 1

    def requestMultiPV(self, setting):
        return 1

    def __repr__(self):
        if self.name:
            return self.name
        return self.features["myname"]
