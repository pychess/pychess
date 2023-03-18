import asyncio
import collections

from pychess.Utils import wait_signal
from pychess.Utils.Move import parseAny
from pychess.Utils.Board import Board
from pychess.Utils.Move import toAN
from pychess.Utils.logic import validate, getMoveKillingKing, getStatus, legalMoveCount
from pychess.Utils.const import (
    CASTLE_KK,
    ANALYZING,
    WON_ADJUDICATION,
    FISCHERRANDOMCHESS,
    INVERSE_ANALYZING,
    CASTLE_KR,
    NORMALCHESS,
    FEN_START,
    WHITE,
    NORMAL,
    DRAW_OFFER,
    WON_MATE,
    BLACK,
    BLACKWON,
    WHITEWON,
)
from pychess.Utils.lutils.ldata import MATE_VALUE
from pychess.Utils.lutils.lmove import ParsingError
from pychess.System import conf
from pychess.System.Log import log
from pychess.Variants.fischerandom import FischerandomBoard

from .ProtocolEngine import ProtocolEngine, TIME_OUT_SECOND
from pychess.Players.Player import PlayerIsDead, TurnInterrupt, InvalidMove

TYPEDIC = {"check": lambda x: x == "true", "spin": int}
OPTKEYS = ("name", "type", "min", "max", "default", "var")


class UCIEngine(ProtocolEngine):
    def __init__(self, subprocess, color, protover, md5):
        ProtocolEngine.__init__(self, subprocess, color, protover, md5)

        self.ids = {}
        self.options = {}
        self.optionsToBeSent = {}

        self.wtime = 60000
        self.btime = 60000
        self.incr = 0
        self.moves = 0
        self.timeHandicap = 1

        self.ponderOn = False
        self.pondermove = None
        self.ignoreNext = False
        self.waitingForMove = False
        self.needBestmove = False
        self.bestmove_event = asyncio.Event()
        self.readyForStop = (
            False  # keeps track of whether we already sent a 'stop' command
        )
        self.multipvSetting = 1  # MultiPV option sent to the engine
        self.multipvExpected = (
            1  # Number of PVs expected (limited by number of legal moves)
        )
        self.commands = collections.deque()

        self.gameBoard = Board(setup=True)  # board at the end of all moves played
        self.board = Board(setup=True)  # board to send the engine
        self.uciPosition = "startpos"
        self.uciPositionListsMoves = False
        self.analysis = [None]
        self.analysis_depth = None

        self.queue = asyncio.Queue()
        self.parse_line_task = asyncio.create_task(self.parseLine(self.engine))
        self.died_cid = self.engine.connect(
            "died", lambda e: self.queue.put_nowait("die")
        )
        self.invalid_move = None

        self.cids = [
            self.connect_after("readyForOptions", self.__onReadyForOptions),
            self.connect_after("readyForMoves", self.__onReadyForMoves),
        ]

    # Starting the game

    def prestart(self):
        print("uci", file=self.engine)

    def start(self, event, is_dead):
        asyncio.create_task(self.__startBlocking(event, is_dead))

    async def __startBlocking(self, event, is_dead):
        try:
            return_value = await asyncio.wait_for(self.queue.get(), TIME_OUT_SECOND)
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
        analyze_mode = self.mode in (ANALYZING, INVERSE_ANALYZING)
        if analyze_mode:
            if self.hasOption("Ponder"):
                self.setOption("Ponder", False)
            if self.hasOption("UCI_LimitStrength"):
                self.setOption("UCI_LimitStrength", False)
        if self.hasOption("UCI_AnalyseMode"):
            self.setOption("UCI_AnalyseMode", analyze_mode)

        for option, value in self.optionsToBeSent.items():
            if option == "MultiPV" and not analyze_mode:
                continue
            if isinstance(value, bool):
                value = str(value).lower()
            print(
                f"setoption name {option} value {str(value)}",
                file=self.engine,
            )

        print("isready", file=self.engine)

    def __onReadyForMoves(self, self_):
        self.readyMoves = True
        self.queue.put_nowait("ready")
        self._newGame()

        if self.isAnalyzing():
            self._searchNow()

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
        self.gameBoard = None

        if self.connected:
            # UCI doens't care about reason, so we just kill
            if reason == WON_ADJUDICATION:
                self.queue.put_nowait("invalid")
            self.kill(reason)

    def kill(self, reason):
        """Kills the engine, starting with the 'stop' and 'quit' commands, then
        trying sigterm and eventually sigkill.
        Returns the exitcode, or if engine have already been killed, the
        method returns None"""
        if self.connected:
            self.connected = False
            try:
                try:
                    print("stop", file=self.engine)
                    print("quit", file=self.engine)
                    self.queue.put_nowait("del")
                    self.engine.terminate()

                except OSError as e:
                    # No need to raise on a hang up error, as the engine is dead
                    # anyways
                    if e.errno == 32:
                        log.warning("Hung up Error", extra={"task": self.defname})
                        return e.errno
                    else:
                        raise

            finally:
                # Clear the analyzed data, if any
                self.emit("analyze", [])

    # Send the player move updates

    def _moveToUCI(self, board, move):
        castle_notation = CASTLE_KK
        if board.variant == FISCHERRANDOMCHESS:
            castle_notation = CASTLE_KR
        return toAN(board, move, short=True, castleNotation=castle_notation)

    def _recordMove(self, board1, move, board2):
        if self.gameBoard == board1:
            return
        if not board2:
            if board1.variant == NORMALCHESS and board1.asFen() == FEN_START:
                self.uciPosition = "startpos"
            else:
                self.uciPosition = "fen " + board1.asFen()
            self.uciPositionListsMoves = False
        if move:
            if not self.uciPositionListsMoves:
                self.uciPosition += " moves"
                self.uciPositionListsMoves = True
            self.uciPosition += " " + self._moveToUCI(board2, move)

        self.board = self.gameBoard = board1
        if self.mode == INVERSE_ANALYZING:
            self.board = self.gameBoard.switchColor()

    def _recordMoveList(self, model, ply=None):
        self._recordMove(model.boards[0], None, None)
        if ply is None:
            ply = model.ply
        for board1, move, board2 in zip(
            model.boards[1 : ply + 1], model.moves, model.boards[0:ply]
        ):
            self._recordMove(board1, move, board2)

    def set_board(self, board):
        self._recordMove(board, None, None)

    def setBoard(self, board, search=True):
        log.debug("setBoardAtPly: board=%s" % board, extra={"task": self.defname})
        if not self.readyMoves:
            return

        async def coro():
            if self.needBestmove:
                self.bestmove_event.clear()
                print("stop", file=self.engine)
                await self.bestmove_event.wait()

            self._recordMove(board, None, None)
            if search:
                self._searchNow()

        asyncio.create_task(coro())

    def putMove(self, board1, move, board2):
        log.debug(
            "putMove: board1={} move={} board2={} self.board={}".format(
                board1, move, board2, self.board
            ),
            extra={"task": self.defname},
        )
        if not self.readyMoves:
            return

        async def coro():
            if self.needBestmove:
                self.bestmove_event.clear()
                print("stop", file=self.engine)
                await self.bestmove_event.wait()

            self._recordMove(board1, move, board2)
            if not self.analyzing_paused:
                self._searchNow()

        asyncio.create_task(coro())

    async def makeMove(self, board1, move, board2):
        log.debug(
            "makeMove: move={} self.pondermove={} board1={} board2={} self.board={}".format(
                move, self.pondermove, board1, board2, self.board
            ),
            extra={"task": self.defname},
        )
        assert self.readyMoves

        self._recordMove(board1, move, board2)
        self.waitingForMove = True
        ponderhit = False

        if board2 and self.pondermove and move == self.pondermove:
            ponderhit = True
        elif board2 and self.pondermove:
            self.ignoreNext = True
            print("stop", file=self.engine)

        self._searchNow(ponderhit=ponderhit)

        # Parse outputs
        try:
            return_queue = await self.queue.get()
            if return_queue == "invalid":
                raise InvalidMove
            if return_queue == "del" or return_queue == "die":
                raise PlayerIsDead
            if return_queue == "int":
                self.pondermove = None
                self.ignoreNext = True
                self.needBestmove = True
                self.hurry()
                raise TurnInterrupt
            return return_queue
        finally:
            self.waitingForMove = False

    def updateTime(self, secs, opsecs):
        if self.color == WHITE:
            self.wtime = int(secs * 1000 * self.timeHandicap)
            self.btime = int(opsecs * 1000)
        else:
            self.btime = int(secs * 1000 * self.timeHandicap)
            self.wtime = int(opsecs * 1000)

    # Standard options

    def setOptionAnalyzing(self, mode):
        self.mode = mode
        if self.mode == INVERSE_ANALYZING:
            self.board = self.gameBoard.switchColor()

    def setOptionInitialBoard(self, model):
        log.debug(
            f"setOptionInitialBoard: self={self}, model={model}",
            extra={"task": self.defname},
        )
        self._recordMoveList(model)

    def setOptionVariant(self, variant):
        if variant == FischerandomBoard:
            assert self.hasOption("UCI_Chess960")
            self.setOption("UCI_Chess960", True)
        elif self.hasOption("UCI_Variant") and not variant.standard_rules:
            self.setOption("UCI_Variant", variant.cecp_name)

    def setOptionTime(self, secs, gain, moves):
        self.wtime = int(max(secs * 1000 * self.timeHandicap, 1))
        self.btime = int(max(secs * 1000 * self.timeHandicap, 1))
        self.incr = int(gain * 1000 * self.timeHandicap)
        self.moves = moves

    def setOptionStrength(self, strength, forcePonderOff):
        self.strength = strength

        # Restriction by embedded ELO evaluation (Stockfish, Arasan, Rybka, CT800, Spike...)
        if self.hasOption("UCI_LimitStrength") and strength <= 18:
            self.setOption("UCI_LimitStrength", True)
            if self.hasOption("UCI_Elo"):
                try:
                    minElo = int(self.options["UCI_Elo"]["min"])
                except Exception:
                    minElo = 1000
                try:
                    maxElo = int(self.options["UCI_Elo"]["max"])
                except Exception:
                    maxElo = 2800
                self.setOption(
                    "UCI_Elo", int(minElo + strength * (maxElo - minElo) / 20)
                )

        # Restriction by unofficial option "Skill Level" (Stockfish, anticrux...)
        if self.hasOption("Skill Level"):
            self.setOption("Skill Level", strength)

        # Restriction by available time
        if (
            not self.hasOption("UCI_Elo") and not self.hasOption("Skill Level")
        ) or strength <= 19:
            self.timeHandicap = t_hcap = 0.01 * 10 ** (strength / 10.0)
            self.wtime = int(max(self.wtime * t_hcap, 1))
            self.btime = int(max(self.btime * t_hcap, 1))
            self.incr = int(self.incr * t_hcap)

        # Amplification with pondering
        if self.hasOption("Ponder"):
            self.setOption("Ponder", strength >= 19 and not forcePonderOff)

        # Amplification by endgame database
        if self.hasOption("GaviotaTbPath") and strength == 20:
            self.setOption("GaviotaTbPath", conf.get("egtb_path"))

    # Interacting with the player

    def pause(self):
        log.debug("pause: self=%s" % self, extra={"task": self.defname})
        if self.isAnalyzing():
            print("stop", file=self.engine)
            self.readyForStop = False
            self.analyzing_paused = True
        else:
            self.engine.pause()
        return

    def resume(self):
        log.debug("resume: self=%s" % self, extra={"task": self.defname})
        if self.isAnalyzing():
            self._searchNow()
            self.analyzing_paused = False
        else:
            self.engine.resume()
        return

    def hurry(self):
        log.debug(
            "hurry: self.waitingForMove={} self.readyForStop={}".format(
                self.waitingForMove, self.readyForStop
            ),
            extra={"task": self.defname},
        )
        # sending this more than once per move will crash most engines
        # so we need to send only the first one, and then ignore every "hurry" request
        # after that until there is another outstanding "position..go"
        if self.waitingForMove and self.readyForStop:
            print("stop", file=self.engine)
            self.readyForStop = False

    def playerUndoMoves(self, moves, gamemodel):
        log.debug(
            "playerUndoMoves: moves={} \
                  gamemodel.ply={} \
                  gamemodel.boards[-1]={} \
                  self.board={}".format(
                moves, gamemodel.ply, gamemodel.boards[-1], self.board
            ),
            extra={"task": self.defname},
        )

        self._recordMoveList(gamemodel)

        if (gamemodel.curplayer != self and moves % 2 == 1) or (
            gamemodel.curplayer == self and moves % 2 == 0
        ):
            # Interrupt if we were searching but should no longer do so, or
            # if it is was our move before undo and it is still our move after undo
            # since we need to send the engine the new FEN in makeMove()
            log.debug(
                "playerUndoMoves: putting 'int' into self.queue=%s" % self.queue,
                extra={"task": self.defname},
            )
            self.queue.put_nowait("int")

    def spectatorUndoMoves(self, moves, gamemodel):
        if self.analyzing_paused:
            return

        log.debug(
            "spectatorUndoMoves: moves={} \
                  gamemodel.ply={} \
                  gamemodel.boards[-1]={} \
                  self.board={}".format(
                moves, gamemodel.ply, gamemodel.boards[-1], self.board
            ),
            extra={"task": self.defname},
        )

        self._recordMoveList(gamemodel)

        if self.readyMoves:
            self._searchNow()

    # Offer handling

    def offer(self, offer):
        if offer.type == DRAW_OFFER:
            self.emit("decline", offer)
        else:
            self.emit("accept", offer)

    # Option handling

    def setOption(self, key, value):
        """Set an option, which will be sent to the engine, after the
        'readyForOptions' signal has passed.
        If you want to know the possible options, you should go to
        engineDiscoverer or use the hasOption method
        while you are in your 'readyForOptions' signal handler"""
        if self.readyMoves:
            log.warning(
                "Options set after 'readyok' are not sent to the engine",
                extra={"task": self.defname},
            )
        self.optionsToBeSent[key] = value
        self.ponderOn = key == "Ponder" and value is True
        if key == "MultiPV":
            self.multipvSetting = int(value)

    def hasOption(self, key):
        return key in self.options

    # Internal

    def _newGame(self):
        print("ucinewgame", file=self.engine)

    def _searchNow(self, ponderhit=False):
        log.debug(
            "_searchNow: self.needBestmove={} ponderhit={} self.board={}".format(
                self.needBestmove, ponderhit, self.board
            ),
            extra={"task": self.defname},
        )

        commands = []

        if ponderhit:
            commands.append("ponderhit")

        elif self.mode == NORMAL:
            commands.append("position %s" % self.uciPosition)
            if self.strength <= 3:
                commands.append("go depth %d" % self.strength)
            else:
                if self.moves > 0:
                    commands.append(
                        "go wtime %d winc %d btime %d binc %d movestogo %s"
                        % (self.wtime, self.incr, self.btime, self.incr, self.moves)
                    )
                else:
                    commands.append(
                        "go wtime %d winc %d btime %d binc %d"
                        % (self.wtime, self.incr, self.btime, self.incr)
                    )

        else:
            print("stop", file=self.engine)

            if self.mode == INVERSE_ANALYZING:
                if self.board.board.opIsChecked():
                    # Many engines don't like positions able to take down enemy
                    # king. Therefore we just return the "kill king" move
                    # automaticaly
                    self.emit(
                        "analyze",
                        [
                            (
                                self.board.ply,
                                [toAN(self.board, getMoveKillingKing(self.board))],
                                MATE_VALUE - 1,
                                "1",
                                "",
                            )
                        ],
                    )
                    return
                commands.append("position fen %s" % self.board.asFen())
            else:
                commands.append("position %s" % self.uciPosition)

            if self.analysis_depth is not None:
                commands.append("go depth %s" % self.analysis_depth)
            else:
                if not conf.get("infinite_depth"):
                    commands.append("go depth %s" % conf.get("max_depth_spin"))
                else:
                    commands.append("go infinite")
                if not conf.get("infinite_analysis"):
                    loop = asyncio.get_event_loop()
                    loop.call_later(
                        conf.get("max_analysis_spin"),
                        lambda: print("stop", file=self.engine),
                    )

        if self.hasOption("MultiPV") and self.multipvSetting > 1:
            self.multipvExpected = min(self.multipvSetting, legalMoveCount(self.board))
        else:
            self.multipvExpected = 1
        self.analysis = [None] * self.multipvExpected

        if self.needBestmove:
            self.commands.append(commands)
            log.debug(
                "_searchNow: self.needBestmove==True, appended to self.commands=%s"
                % self.commands,
                extra={"task": self.defname},
            )
        else:
            for command in commands:
                print(command, file=self.engine)
            if getStatus(self.board)[1] != WON_MATE:  # XXX This looks fishy.
                self.needBestmove = True
                self.readyForStop = True

    def _startPonder(self):
        uciPos = self.uciPosition
        if not self.uciPositionListsMoves:
            uciPos += " moves"
        print(
            "position",
            uciPos,
            self._moveToUCI(self.board, self.pondermove),
            file=self.engine,
        )
        print(
            "go ponder wtime",
            self.wtime,
            "winc",
            self.incr,
            "btime",
            self.btime,
            "binc",
            self.incr,
            file=self.engine,
        )

    # Parsing from engine

    async def parseLine(self, proc):
        while True:
            line = await wait_signal(proc, "line")
            if not line:
                break
            else:
                line = line[1]
                parts = line.split()
                if not parts:
                    continue
                # Initializing
                if parts[0] == "id":
                    if parts[1] == "name":
                        self.ids[parts[1]] = " ".join(parts[2:])
                        self.setName(self.ids["name"])
                    continue

                if parts[0] == "uciok":
                    self.emit("readyForOptions")
                    continue

                if parts[0] == "readyok":
                    self.emit("readyForMoves")
                    continue

                # Options parsing
                if parts[0] == "option":
                    dic = {}
                    last = 1
                    varlist = []
                    for i in range(2, len(parts) + 1):
                        if i == len(parts) or parts[i] in OPTKEYS:
                            key = parts[last]
                            value = " ".join(parts[last + 1 : i])
                            if "type" in dic and dic["type"] in TYPEDIC:
                                value = TYPEDIC[dic["type"]](value)

                            if key == "var":
                                varlist.append(value)
                            elif key == "type" and value == "string":
                                dic[key] = "text"
                            else:
                                dic[key] = value

                            last = i
                    if varlist:
                        dic["choices"] = varlist

                    if "name" in dic:
                        self.options[dic["name"]] = dic
                    continue

                # A Move
                if self.mode == NORMAL and parts[0] == "bestmove":
                    self.needBestmove = False
                    self.bestmove_event.set()
                    self.__sendQueuedGo()

                    if self.ignoreNext:
                        log.debug(
                            "__parseLine: line='%s' self.ignoreNext==True, returning"
                            % line.strip(),
                            extra={"task": self.defname},
                        )
                        self.ignoreNext = False
                        self.readyForStop = True
                        continue

                    movestr = parts[1]
                    if not self.waitingForMove:
                        log.warning(
                            "__parseLine: self.waitingForMove==False, ignoring move=%s"
                            % movestr,
                            extra={"task": self.defname},
                        )
                        self.pondermove = None
                        continue
                    self.waitingForMove = False

                    try:
                        move = parseAny(self.board, movestr)
                    except ParsingError:
                        self.invalid_move = movestr
                        log.info(
                            "__parseLine: ParsingError engine move: %s %s"
                            % (movestr, self.board),
                            extra={"task": self.defname},
                        )
                        self.end(
                            WHITEWON if self.board.color == BLACK else BLACKWON,
                            WON_ADJUDICATION,
                        )
                        continue

                    if not validate(self.board, move):
                        # This is critical. To avoid game stalls, we need to resign on
                        # behalf of the engine.
                        log.error(
                            "__parseLine: move={} didn't validate, putting 'del' \
                                  in returnQueue. self.board={}".format(
                                repr(move), self.board
                            ),
                            extra={"task": self.defname},
                        )
                        self.invalid_move = movestr
                        self.end(
                            WHITEWON if self.board.color == BLACK else BLACKWON,
                            WON_ADJUDICATION,
                        )
                        continue

                    self._recordMove(self.board.move(move), move, self.board)
                    log.debug(
                        "__parseLine: applied move={} to self.board={}".format(
                            move, self.board
                        ),
                        extra={"task": self.defname},
                    )

                    if self.ponderOn:
                        self.pondermove = None
                        # An engine may send an empty ponder line, simply to clear.
                        if len(parts) == 4:
                            # Engines don't always check for everything in their
                            # ponders. Hence we need to validate.
                            # But in some cases, what they send may not even be
                            # correct AN - specially in the case of promotion.
                            try:
                                pondermove = parseAny(self.board, parts[3])
                            except ParsingError:
                                pass
                            else:
                                if validate(self.board, pondermove):
                                    self.pondermove = pondermove
                                    self._startPonder()

                    self.queue.put_nowait(move)
                    log.debug(
                        "__parseLine: put move={} into self.queue={}".format(
                            move, self.queue
                        ),
                        extra={"task": self.defname},
                    )
                    continue

                # An Analysis
                if self.mode != NORMAL and parts[0] == "info" and "pv" in parts:
                    multipv = 1
                    if "multipv" in parts:
                        multipv = int(parts[parts.index("multipv") + 1])
                    scoretype = parts[parts.index("score") + 1]
                    if scoretype in ("lowerbound", "upperbound"):
                        score = None
                    else:
                        score = int(parts[parts.index("score") + 2])
                        if scoretype == "mate":
                            #                    print >> self.engine, "stop"
                            if score != 0:
                                sign = score / abs(score)
                                score = sign * (MATE_VALUE - abs(score))

                    movstrs = parts[parts.index("pv") + 1 :]

                    if "depth" in parts:
                        depth = parts[parts.index("depth") + 1]
                    else:
                        depth = ""

                    if "nps" in parts:
                        nps = parts[parts.index("nps") + 1]
                    else:
                        nps = ""

                    if multipv <= len(self.analysis):
                        self.analysis[multipv - 1] = (
                            self.board.ply,
                            movstrs,
                            score,
                            depth,
                            nps,
                        )
                    self.emit("analyze", self.analysis)
                    continue

                # An Analyzer bestmove
                if self.mode != NORMAL and parts[0] == "bestmove":
                    log.debug(
                        "__parseLine: processing analyzer bestmove='%s'" % line.strip(),
                        extra={"task": self.defname},
                    )
                    self.needBestmove = False
                    self.bestmove_event.set()
                    if parts[1] == "(none)":
                        self.emit("analyze", [])
                    else:
                        self.__sendQueuedGo(sendlast=True)
                    continue

                # Stockfish complaining it received a 'stop' without a corresponding 'position..go'
                if line.strip() == "Unknown command: stop":
                    log.debug(
                        "__parseLine: processing '%s'" % line.strip(),
                        extra={"task": self.defname},
                    )
                    self.ignoreNext = False
                    self.needBestmove = False
                    self.readyForStop = False
                    self.__sendQueuedGo()
                    continue

                # * score
                # * cp <x>
                #    the score from the engine's point of view in centipawns.
                # * mate <y>
                #    mate in y moves, not plies.
                #    If the engine is getting mated use negative values for y.
                # * lowerbound
                #  the score is just a lower bound.
                # * upperbound
                #   the score is just an upper bound.

    def __sendQueuedGo(self, sendlast=False):
        """Sends the next position...go or ponderhit command set which was queued (if any).

        sendlast -- If True, send the last position-go queued rather than the first,
        and discard the others (intended for analyzers)
        """
        if len(self.commands) > 0:
            if sendlast:
                commands = self.commands.pop()
                self.commands.clear()
            else:
                commands = self.commands.popleft()

            for command in commands:
                print(command, file=self.engine)
            self.needBestmove = True
            self.readyForStop = True
            log.debug(
                "__sendQueuedGo: sent queued go=%s" % commands,
                extra={"task": self.defname},
            )

    #    Info

    def getAnalysisLines(self):
        try:
            return int(self.optionsToBeSent["MultiPV"])
        except (KeyError, ValueError):
            return 1  # Engine does not support the MultiPV option

    def minAnalysisLines(self):
        try:
            return int(self.options["MultiPV"]["min"])
        except (KeyError, ValueError):
            return 1  # Engine does not support the MultiPV option

    def maxAnalysisLines(self):
        try:
            return int(self.options["MultiPV"]["max"])
        except (KeyError, ValueError):
            return 1  # Engine does not support the MultiPV option

    def requestMultiPV(self, n):
        n = min(n, self.maxAnalysisLines())
        n = max(n, self.minAnalysisLines())
        if n != self.multipvSetting:
            self.multipvSetting = n
            print("stop", file=self.engine)
            print("setoption name MultiPV value %s" % n, file=self.engine)
            self._searchNow()
        return n

    def __repr__(self):
        if self.name:
            return self.name
        if "name" in self.ids:
            return self.ids["name"]
        return ", ".join(self.defname)
