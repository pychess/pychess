import asyncio
import collections
import datetime
import random
import traceback
from queue import Queue
from io import StringIO

from gi.repository import GObject

from pychess.compat import create_task
from pychess.Savers.ChessFile import LoadingError
from pychess.Players.Player import PlayerIsDead, PassInterrupt, TurnInterrupt, InvalidMove, GameEnded
from pychess.System import conf
from pychess.System.protoopen import protoopen, protosave
from pychess.System.Log import log
from pychess.Utils.book import getOpenings
from pychess.Utils.Move import Move
from pychess.Utils.eco import get_eco
from pychess.Utils.Offer import Offer
from pychess.Utils.TimeModel import TimeModel
from pychess.Savers import html, txt
from pychess.Variants.normal import NormalBoard

from .logic import getStatus, isClaimableDraw, playerHasMatingMaterial
from .const import WAITING_TO_START, UNKNOWN_REASON, WHITE, ARTIFICIAL, RUNNING, \
    FLAG_CALL, BLACK, KILLED, ANALYZING, LOCAL, REMOTE, PAUSED, HURRY_ACTION, \
    CHAT_ACTION, RESIGNATION, BLACKWON, WHITEWON, DRAW_CALLFLAG, WON_RESIGN, DRAW, \
    WON_CALLFLAG, DRAW_WHITEINSUFFICIENTANDBLACKTIME, DRAW_OFFER, TAKEBACK_OFFER, \
    DRAW_BLACKINSUFFICIENTANDWHITETIME, ACTION_ERROR_NOT_OUT_OF_TIME, OFFERS, \
    ACTION_ERROR_TOO_LARGE_UNDO, ACTION_ERROR_NONE_TO_WITHDRAW, DRAW_AGREE, \
    ACTION_ERROR_NONE_TO_DECLINE, ADJOURN_OFFER, ADJOURNED, ABORT_OFFER, ABORTED, \
    ADJOURNED_AGREEMENT, PAUSE_OFFER, RESUME_OFFER, ACTION_ERROR_NONE_TO_ACCEPT, \
    ABORTED_AGREEMENT, WHITE_ENGINE_DIED, BLACK_ENGINE_DIED, WON_ADJUDICATION, \
    UNDOABLE_STATES, DRAW_REPITITION, UNDOABLE_REASONS, UNFINISHED_STATES, \
    DRAW_50MOVES, HINT


class GameModel(GObject.GObject):
    """ GameModel contains all available data on a chessgame.
        It also has the task of controlling players actions and moves """

    __gsignals__ = {
        # game_started is emitted when control is given to the players for the
        # first time. Notice this is after players.start has been called.
        "game_started": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # game_changed is emitted when a move has been made.
        "game_changed": (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        # moves_undoig is emitted when a undoMoves call has been accepted, but
        # before any work has been done to execute it.
        "moves_undoing": (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        # moves_undone is emitted after n moves have been undone in the
        # gamemodel and the players.
        "moves_undone": (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        # variation_undoig is emitted when a undo_in_variation call has been started, but
        # before any work has been done to execute it.
        "variation_undoing": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # variation_undone is emitted after 1 move have been undone in the
        # boardview shown variation
        "variation_undone": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # game_unended is emitted if moves have been undone, such that the game
        # which had previously ended, is now again active.
        "game_unended": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # game_loading is emitted if the GameModel is about to load in a chess
        # game from a file.
        "game_loading": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        # game_loaded is emitted after the chessformat handler has loaded in
        # all the moves from a file to the game model.
        "game_loaded": (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        # game_saved is emitted in the end of model.save()
        "game_saved": (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        # game_ended is emitted if the models state has been changed to an
        # "ended state"
        "game_ended": (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        # game_terminated is emitted if the game was terminated. That is all
        # players and clocks were stopped, and it is no longer possible to
        # resume the game, even by undo.
        "game_terminated": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # game_paused is emitted if the game was successfully paused.
        "game_paused": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # game_paused is emitted if the game was successfully resumed from a
        # pause.
        "game_resumed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # action_error is currently only emitted by ICGameModel, in the case
        # the "web model" didn't accept the action you were trying to do.
        "action_error": (GObject.SignalFlags.RUN_FIRST, None, (object, int)),
        # players_changed is emitted if the players list was changed.
        "players_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "analyzer_added": (GObject.SignalFlags.RUN_FIRST, None, (object, str)),
        "analyzer_removed": (GObject.SignalFlags.RUN_FIRST, None,
                             (object, str)),
        "analyzer_paused": (GObject.SignalFlags.RUN_FIRST, None,
                            (object, str)),
        "analyzer_resumed": (GObject.SignalFlags.RUN_FIRST, None,
                             (object, str)),
        # opening_changed is emitted if the move changed the opening.
        "opening_changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # variation_added is emitted if a variation was added.
        "variation_added": (GObject.SignalFlags.RUN_FIRST, None,
                            (object, object)),
        # variation_extended is emitted if a new move was added to a variation.
        "variation_extended": (GObject.SignalFlags.RUN_FIRST, None,
                               (object, object)),
        # scores_changed is emitted if the analyzing scores was changed.
        "analysis_changed": (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        # analysis_finished is emitted if the game analyzing finished stepping on all moves.
        "analysis_finished": (GObject.SignalFlags.RUN_FIRST, None, ()),
        # FICS games can get kibitz/whisper messages
        "message_received": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        # FICS games can have observers
        "observers_received": (GObject.SignalFlags.RUN_FIRST, None, (str, )),
    }

    def __init__(self, timemodel=None, variant=NormalBoard):
        GObject.GObject.__init__(self)
        self.daemon = True
        self.variant = variant
        self.boards = [variant(setup=True)]

        self.moves = []
        self.scores = {}
        self.spy_scores = {}
        self.players = []

        self.gameno = None
        self.variations = [self.boards]

        self.terminated = False
        self.status = WAITING_TO_START
        self.reason = UNKNOWN_REASON
        self.curColor = WHITE

        if timemodel is None:
            self.timemodel = TimeModel()
        else:
            self.timemodel = timemodel
        self.timemodel.gamemodel = self

        self.connections = collections.defaultdict(list)  # mainly for IC subclasses
        self.analyzer_cids = {}
        self.examined = False

        now = datetime.datetime.now()
        self.tags = collections.defaultdict(str)
        self.tags["Event"] = _("Local Event")
        self.tags["Site"] = _("Local Site")
        self.tags["Date"] = "%04d.%02d.%02d" % (now.year, now.month, now.day)
        self.tags["Round"] = "1"

        self.endstatus = None
        self.zero_reached_cid = None

        self.timed = self.timemodel.minutes != 0 or self.timemodel.gain != 0
        if self.timed:
            self.zero_reached_cid = self.timemodel.connect('zero_reached', self.zero_reached)
            if self.timemodel.moves == 0:
                self.tags["TimeControl"] = "%d%s%d" % (self.timemodel.minutes * 60, "+" if self.timemodel.gain >= 0 else "-", abs(self.timemodel.gain))
            else:
                self.tags["TimeControl"] = "%d/%d" % (self.timemodel.moves, self.timemodel.minutes * 60)
            # Notice: tags["WhiteClock"] and tags["BlackClock"] are never set
            # on the gamemodel, but simply written or read during saving/
            # loading from pgn. If you want to know the time left for a player,
            # check the time model.

        # Keeps track of offers, so that accepts can be spotted
        self.offers = {}

        # True if the game has been changed since last save
        self.needsSave = False

        # The uri the current game was loaded from, or None if not a loaded game
        self.uri = None

        # Link to additiona info
        self.info = None

        self.spectators = {}

        self.undoQueue = Queue()

        # learn_type set by LearnModel.set_learn_data()
        self.offline_lecture = False
        self.puzzle_game = False
        self.lesson_game = False
        self.end_game = False
        self.solved = False

    @property
    def practice_game(self):
        return self.puzzle_game or self.end_game

    @property
    def starting_color(self):
        return BLACK if "FEN" in self.tags and self.tags["FEN"].split()[1] == "b" else WHITE

    @property
    def orientation(self):
        if "Orientation" in self.tags:
            return BLACK if self.tags["Orintation"].lower() == "black" else WHITE
        else:
            return self.starting_color

    def zero_reached(self, timemodel, color):
        if conf.get('autoCallFlag'):
            if self.status == RUNNING and timemodel.getPlayerTime(color) <= 0:
                log.info(
                    'Automatically sending flag call on behalf of player %s.' %
                    self.players[1 - color].name)
                self.players[1 - color].emit("offer", Offer(FLAG_CALL))

    def __repr__(self):
        string = "<GameModel at %s" % id(self)
        string += " (ply=%s" % self.ply
        if len(self.moves) > 0:
            string += ", move=%s" % self.moves[-1]
        string += ", variant=%s" % self.variant.name.encode('utf-8')
        string += ", status=%s, reason=%s" % (str(self.status), str(self.reason))
        string += ", players=%s" % str(self.players)
        string += ", tags=%s" % str(self.tags)
        if len(self.boards) > 0:
            string += "\nboard=%s" % self.boards[-1]
        return string + ")>"

    @property
    def display_text(self):
        if self.variant == NormalBoard and not self.timed:
            return "[ " + _("Untimed") + " ]"
        else:
            text = "[ "
            if self.variant != NormalBoard:
                text += self.variant.name + " "
            if self.timed:
                text += self.timemodel.display_text + " "
            return text + "]"

    def setPlayers(self, players):
        log.debug("GameModel.setPlayers: starting")
        assert self.status == WAITING_TO_START
        self.players = players
        for player in self.players:
            self.connections[player].append(player.connect("offer",
                                                           self.offerReceived))
            self.connections[player].append(player.connect(
                "withdraw", self.withdrawReceived))
            self.connections[player].append(player.connect(
                "decline", self.declineReceived))
            self.connections[player].append(player.connect(
                "accept", self.acceptReceived))
        self.tags["White"] = str(self.players[WHITE])
        self.tags["Black"] = str(self.players[BLACK])
        log.debug("GameModel.setPlayers: -> emit players_changed")
        self.emit("players_changed")
        log.debug("GameModel.setPlayers: <- emit players_changed")
        log.debug("GameModel.setPlayers: returning")

    def color(self, player):
        if player is self.players[0]:
            return WHITE
        else:
            return BLACK

    @asyncio.coroutine
    def start_analyzer(self, analyzer_type, force_engine=None):
        # Don't start regular analyzers
        if (self.practice_game or self.lesson_game) and force_engine is None and not self.solved:
            return

        # prevent starting new analyzers again and again
        # when fics lecture reuses the same gamemodel
        if analyzer_type in self.spectators:
            return

        from pychess.Players.engineNest import init_engine
        analyzer = yield from init_engine(analyzer_type, self, force_engine=force_engine)
        if analyzer is None:
            return

        analyzer.setOptionInitialBoard(self)
        # Enable to find alternate hint in learn perspective puzzles
        if force_engine is not None:
            analyzer.setOption("MultiPV", 3)
            analyzer.analysis_depth = 20

        self.spectators[analyzer_type] = analyzer
        self.emit("analyzer_added", analyzer, analyzer_type)
        self.analyzer_cids[analyzer_type] = analyzer.connect("analyze", self.on_analyze)

    def remove_analyzer(self, analyzer_type):
        try:
            analyzer = self.spectators[analyzer_type]
        except KeyError:
            return

        analyzer.disconnect(self.analyzer_cids[analyzer_type])
        analyzer.end(KILLED, UNKNOWN_REASON)
        self.emit("analyzer_removed", analyzer, analyzer_type)
        del self.spectators[analyzer_type]

    def resume_analyzer(self, analyzer_type):
        try:
            analyzer = self.spectators[analyzer_type]
        except KeyError:
            return

        analyzer.resume()
        self.emit("analyzer_resumed", analyzer, analyzer_type)

    def pause_analyzer(self, analyzer_type):
        try:
            analyzer = self.spectators[analyzer_type]
        except KeyError:
            return

        analyzer.pause()
        self.emit("analyzer_paused", analyzer, analyzer_type)

    @asyncio.coroutine
    def restart_analyzer(self, analyzer_type):
        self.remove_analyzer(analyzer_type)
        yield from self.start_analyzer(analyzer_type)

    def on_analyze(self, analyzer, analysis):
        if analysis and (self.practice_game or self.lesson_game):
            for i, anal in enumerate(analysis):
                if anal is not None:
                    ply, pv, score, depth, nps = anal
                    if len(pv) > 0:
                        if ply not in self.hints:
                            self.hints[ply] = []

                        if len(self.hints[ply]) < i + 1:
                            self.hints[ply].append((pv[0], score))
                        else:
                            self.hints[ply][i] = (pv[0], score)
        if analysis and analysis[0] is not None:
            ply, pv, score, depth, nps = analysis[0]
            if score is not None and depth:
                if analyzer.mode == ANALYZING:
                    if (ply not in self.scores) or (int(self.scores[ply][2]) <= int(depth)):
                        self.scores[ply] = (pv, score, depth)
                        self.emit("analysis_changed", ply)
                else:
                    if (ply not in self.spy_scores) or (int(self.spy_scores[ply][2]) <= int(depth)):
                        self.spy_scores[ply] = (pv, score, depth)

    def setOpening(self, ply=None):
        if ply is None:
            ply = self.ply
        if ply > 40:
            return

        if ply > 0:
            opening = get_eco(self.getBoardAtPly(ply).board.hash)
        else:
            opening = None
        if opening is not None:
            self.tags["ECO"] = opening[0]
            self.tags["Opening"] = opening[1]
            self.tags["Variation"] = opening[2]
            self.emit("opening_changed")

    # Board stuff

    def _get_ply(self):
        return self.boards[-1].ply

    ply = property(_get_ply)

    def _get_lowest_ply(self):
        return self.boards[0].ply

    lowply = property(_get_lowest_ply)

    def _get_curplayer(self):
        try:
            return self.players[self.getBoardAtPly(self.ply).color]
        except IndexError:
            log.error("%s %s" %
                      (self.players, self.getBoardAtPly(self.ply).color))
            raise

    curplayer = property(_get_curplayer)

    def _get_waitingplayer(self):
        try:
            return self.players[1 - self.getBoardAtPly(self.ply).color]
        except IndexError:
            log.error("%s %s" %
                      (self.players, 1 - self.getBoardAtPly(self.ply).color))
            raise

    waitingplayer = property(_get_waitingplayer)

    def _plyToIndex(self, ply):
        index = ply - self.lowply
        if index < 0:
            raise IndexError("%s < %s\n" % (ply, self.lowply))
        return index

    def getBoardAtPly(self, ply, variation=0):
        try:
            return self.variations[variation][self._plyToIndex(ply)]
        except IndexError:
            log.error("%d\t%d\t%d\t%d\t%d" % (self.lowply, ply, self.ply,
                                              variation, len(self.variations)))
            raise

    def getMoveAtPly(self, ply, variation=0):
        try:
            return Move(self.variations[variation][self._plyToIndex(ply) +
                                                   1].board.lastMove)
        except IndexError:
            log.error("%d\t%d\t%d\t%d\t%d" % (self.lowply, ply, self.ply,
                                              variation, len(self.variations)))
            raise

    def hasLocalPlayer(self):
        if self.players[0].__type__ == LOCAL or self.players[
                1].__type__ == LOCAL:
            return True
        else:
            return False

    def hasEnginePlayer(self):
        if self.players[0].__type__ == ARTIFICIAL or self.players[
                1].__type__ == ARTIFICIAL:
            return True
        else:
            return False

    def isLocalGame(self):
        if self.players[0].__type__ != REMOTE and self.players[
                1].__type__ != REMOTE:
            return True
        else:
            return False

    def isObservationGame(self):
        return not self.hasLocalPlayer()

    def isEngine2EngineGame(self):
        if len(self.players) == 2 and self.players[0].__type__ == ARTIFICIAL and self.players[1].__type__ == ARTIFICIAL:
            return True
        else:
            return False

    def isPlayingICSGame(self):
        if self.players and self.status in (WAITING_TO_START, PAUSED, RUNNING):
            if (self.players[0].__type__ == LOCAL and self.players[1].__type__ == REMOTE) or \
               (self.players[1].__type__ == LOCAL and self.players[0].__type__ == REMOTE) or \
               ((self.offline_lecture or self.practice_game or self.lesson_game) and not self.solved) or \
               (self.players[1].__type__ == REMOTE and self.players[0].__type__ == REMOTE and
                    self.examined and (
                    self.players[0].name == "puzzlebot" or self.players[1].name == "puzzlebot") or
                    self.players[0].name == "endgamebot" or self.players[1].name == "endgamebot"):
                return True
        return False

    def isLoadedGame(self):
        return self.gameno is not None

    # Offer management

    def offerReceived(self, player, offer):
        log.debug("GameModel.offerReceived: offerer=%s %s" %
                  (repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        elif player == self.players[BLACK]:
            opPlayer = self.players[WHITE]
        else:
            # Player comments echoed to opponent if the player started a conversation
            # with you prior to observing a game the player is in #1113
            return

        if offer.type == HURRY_ACTION:
            opPlayer.hurry()

        elif offer.type == CHAT_ACTION:
            # print("GameModel.offerreceived(player, offer)", player.name, offer.param)
            opPlayer.putMessage(offer.param)

        elif offer.type == RESIGNATION:
            if player == self.players[WHITE]:
                self.end(BLACKWON, WON_RESIGN)
            else:
                self.end(WHITEWON, WON_RESIGN)

        elif offer.type == FLAG_CALL:
            assert self.timed
            if self.timemodel.getPlayerTime(1 - player.color) <= 0:
                if self.timemodel.getPlayerTime(player.color) <= 0:
                    self.end(DRAW, DRAW_CALLFLAG)
                elif not playerHasMatingMaterial(self.boards[-1],
                                                 player.color):
                    if player.color == WHITE:
                        self.end(DRAW, DRAW_WHITEINSUFFICIENTANDBLACKTIME)
                    else:
                        self.end(DRAW, DRAW_BLACKINSUFFICIENTANDWHITETIME)
                else:
                    if player == self.players[WHITE]:
                        self.end(WHITEWON, WON_CALLFLAG)
                    else:
                        self.end(BLACKWON, WON_CALLFLAG)
            else:
                player.offerError(offer, ACTION_ERROR_NOT_OUT_OF_TIME)

        elif offer.type == DRAW_OFFER and isClaimableDraw(self.boards[-1]):
            reason = getStatus(self.boards[-1])[1]
            self.end(DRAW, reason)

        elif offer.type == TAKEBACK_OFFER and offer.param < self.lowply:
            player.offerError(offer, ACTION_ERROR_TOO_LARGE_UNDO)

        elif offer.type in OFFERS:
            if offer not in self.offers:
                log.debug("GameModel.offerReceived: doing %s.offer(%s)" % (
                    repr(opPlayer), offer))
                self.offers[offer] = player
                opPlayer.offer(offer)
            # If we updated an older offer, we want to delete the old one
            keys = self.offers.keys()
            for offer_ in keys:
                if offer.type == offer_.type and offer != offer_:
                    del self.offers[offer_]

    def withdrawReceived(self, player, offer):
        log.debug("GameModel.withdrawReceived: withdrawer=%s %s" % (
            repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else:
            opPlayer = self.players[WHITE]

        if offer in self.offers and self.offers[offer] == player:
            del self.offers[offer]
            opPlayer.offerWithdrawn(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_WITHDRAW)

    def declineReceived(self, player, offer):
        log.debug("GameModel.declineReceived: decliner=%s %s" % (
                  repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else:
            opPlayer = self.players[WHITE]

        if offer in self.offers and self.offers[offer] == opPlayer:
            del self.offers[offer]
            log.debug("GameModel.declineReceived: declining %s" % offer)
            opPlayer.offerDeclined(offer)
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_DECLINE)

    def acceptReceived(self, player, offer):
        log.debug("GameModel.acceptReceived: accepter=%s %s" % (
                  repr(player), offer))
        if player == self.players[WHITE]:
            opPlayer = self.players[BLACK]
        else:
            opPlayer = self.players[WHITE]

        if offer in self.offers and self.offers[offer] == opPlayer:
            if offer.type == DRAW_OFFER:
                self.end(DRAW, DRAW_AGREE)
            elif offer.type == TAKEBACK_OFFER:
                log.debug("GameModel.acceptReceived: undoMoves(%s)" % offer.param)
                self.undoMoves(offer.param)
            elif offer.type == ADJOURN_OFFER:
                self.end(ADJOURNED, ADJOURNED_AGREEMENT)
            elif offer.type == ABORT_OFFER:
                self.end(ABORTED, ABORTED_AGREEMENT)
            elif offer.type == PAUSE_OFFER:
                self.pause()
            elif offer.type == RESUME_OFFER:
                self.resume()
            del self.offers[offer]
        else:
            player.offerError(offer, ACTION_ERROR_NONE_TO_ACCEPT)

    # Data stuff

    def loadAndStart(self, uri, loader, gameno, position, first_time=True):
        if first_time:
            assert self.status == WAITING_TO_START

        uriIsFile = not isinstance(uri, str)
        if not uriIsFile:
            chessfile = loader.load(protoopen(uri))
        else:
            chessfile = loader.load(uri)

        self.gameno = gameno
        self.emit("game_loading", uri)
        try:
            chessfile.loadToModel(gameno, -1, self)
        # Postpone error raising to make games loadable to the point of the
        # error
        except LoadingError as e:
            error = e
        else:
            error = None
        if self.players:
            self.players[WHITE].setName(self.tags["White"])
            self.players[BLACK].setName(self.tags["Black"])
        self.emit("game_loaded", uri)

        self.needsSave = False
        if not uriIsFile:
            self.uri = uri
        else:
            self.uri = None

        # Even if the game "starts ended", the players should still be moved
        # to the last position, so analysis is correct, and a possible "undo"
        # will work as expected.
        for spectator in self.spectators.values():
            spectator.setOptionInitialBoard(self)
        for player in self.players:
            player.setOptionInitialBoard(self)
        if self.timed:
            self.timemodel.setMovingColor(self.boards[-1].color)

        if first_time:
            if self.status == RUNNING:
                if self.timed:
                    self.timemodel.start()

            # Store end status from Result tag
            if self.status in (DRAW, WHITEWON, BLACKWON):
                self.endstatus = self.status
            self.status = WAITING_TO_START
            self.start()

        if error:
            raise error

    def save(self, uri, saver, append, position=None, flip=False):
        if saver in (html, txt):
            fileobj = open(uri, "a" if append else "w", encoding="utf-8", newline="")
            self.uri = uri
        elif isinstance(uri, str):
            fileobj = protosave(uri, append)
            self.uri = uri
        else:
            fileobj = uri
            self.uri = None
        saver.save(fileobj, self, position, flip)
        self.needsSave = False
        self.emit("game_saved", uri)

    def get_book_move(self):
        openings = getOpenings(self.boards[-1].board)
        openings.sort(key=lambda t: t[1], reverse=True)
        if not openings:
            return None

        total_weights = 0
        for move, weight, learn in openings:
            total_weights += weight

        if total_weights < 1:
            return None

        choice = random.randint(0, total_weights - 1)

        current_sum = 0
        for move, weight, learn in openings:
            current_sum += weight
            if current_sum > choice:
                return Move(move)

    # Run stuff

    def start(self):
        @asyncio.coroutine
        def coro():
            log.debug("GameModel.run: Starting. self=%s" % self)
            # Avoid racecondition when self.start is called while we are in
            # self.end
            if self.status != WAITING_TO_START:
                return

            if not self.isLocalGame():
                self.timemodel.handle_gain = False

            self.status = RUNNING

            for player in self.players + list(self.spectators.values()):
                event = asyncio.Event()
                is_dead = set()
                player.start(event, is_dead)

                yield from event.wait()

                if is_dead:
                    if player in self.players[WHITE]:
                        self.kill(WHITE_ENGINE_DIED)
                        break
                    elif player in self.players[BLACK]:
                        self.kill(BLACK_ENGINE_DIED)
                        break

            log.debug("GameModel.run: emitting 'game_started' self=%s" % self)
            self.emit("game_started")

            # Let GameModel end() itself on games started with loadAndStart()
            if not self.lesson_game:
                self.checkStatus()

            if self.isEngine2EngineGame() and self.timed:
                self.timemodel.start()
                self.timemodel.started = True

            self.curColor = self.boards[-1].color

            book_depth_max = conf.get("book_depth_max")

            while self.status in (PAUSED, RUNNING, DRAW, WHITEWON, BLACKWON):
                curPlayer = self.players[self.curColor]
                if self.timed:
                    log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: updating %s's time" % (
                        id(self), str(self.players), str(self.ply), str(curPlayer)))
                    curPlayer.updateTime(
                        self.timemodel.getPlayerTime(self.curColor),
                        self.timemodel.getPlayerTime(1 - self.curColor))
                try:
                    log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: calling %s.makeMove()" % (
                        id(self), str(self.players), self.ply, str(curPlayer)))

                    move = None
                    if curPlayer.__type__ == ARTIFICIAL and book_depth_max > 0 and self.ply <= book_depth_max:
                        move = self.get_book_move()
                        log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: got move=%s from book" % (
                            id(self), str(self.players), self.ply, move))
                        if move is not None:
                            curPlayer.set_board(self.boards[-1].move(move))
                    if move is None:
                        if self.ply > self.lowply:
                            move = yield from curPlayer.makeMove(self.boards[-1], self.moves[-1], self.boards[-2])
                        else:
                            move = yield from curPlayer.makeMove(self.boards[-1], None, None)
                        log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: got move=%s from %s" % (
                            id(self), str(self.players), self.ply, move, str(curPlayer)))
                except PlayerIsDead as e:
                    if self.status in (WAITING_TO_START, PAUSED, RUNNING):
                        stringio = StringIO()
                        traceback.print_exc(file=stringio)
                        error = stringio.getvalue()
                        log.error(
                            "GameModel.run: A Player died: player=%s error=%s\n%s"
                            % (curPlayer, error, e))
                        if self.curColor == WHITE:
                            self.kill(WHITE_ENGINE_DIED)
                        else:
                            self.kill(BLACK_ENGINE_DIED)
                    break
                except InvalidMove as e:
                    stringio = StringIO()
                    traceback.print_exc(file=stringio)
                    error = stringio.getvalue()
                    log.error(
                        "GameModel.run: InvalidMove by player=%s error=%s\n%s"
                        % (curPlayer, error, e))
                    if self.curColor == WHITE:
                        self.end(BLACKWON, WON_ADJUDICATION)
                    else:
                        self.end(WHITEWON, WON_ADJUDICATION)
                    break
                except PassInterrupt:
                    log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: PassInterrupt" % (
                        id(self), str(self.players), self.ply))
                    continue
                except TurnInterrupt:
                    log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: TurnInterrupt" % (
                        id(self), str(self.players), self.ply))
                    self.curColor = self.boards[-1].color
                    continue
                except GameEnded:
                    log.debug("GameModel.run: got GameEnded exception")
                    break

                assert isinstance(move, Move), "%s" % repr(move)
                log.debug("GameModel.run: id=%s, players=%s, self.ply=%s: applying move=%s" % (
                    id(self), str(self.players), self.ply, str(move)))
                self.needsSave = True
                newBoard = self.boards[-1].move(move)
                newBoard.board.prev = self.boards[-1].board

                # newBoard.printPieces()
                # Variation on next move can exist from the hint panel...
                if self.boards[-1].board.next is not None:
                    newBoard.board.children = self.boards[
                        -1].board.next.children

                self.boards = self.variations[0]
                self.boards[-1].board.next = newBoard.board
                self.boards.append(newBoard)
                self.moves.append(move)

                if self.timed:
                    self.timemodel.tap()

                if not self.terminated:
                    self.emit("game_changed", self.ply)

                for spectator in self.spectators.values():
                    if spectator.board == self.boards[-2]:
                        spectator.putMove(self.boards[-1], self.moves[-1],
                                          self.boards[-2])

                if self.puzzle_game and len(self.moves) % 2 == 1:
                    status, reason = getStatus(self.boards[-1])
                    self.failed_playing_best = self.check_failed_playing_best(status)
                    if self.failed_playing_best:
                        # print("failed_playing_best() == True -> yield from asyncio.sleep(1.5) ")
                        # It may happen that analysis had no time to fill hints with best moves
                        # so we give him another chance with some additional time to think on it
                        self.spectators[HINT].setBoard(self.boards[-2])
                        # TODO: wait for an event (analyzer PV reaching 18 ply)
                        # instead of hard coded sleep time
                        yield from asyncio.sleep(1.5)
                        self.failed_playing_best = self.check_failed_playing_best(status)

                self.checkStatus()

                self.setOpening()

                self.curColor = 1 - self.curColor

            self.checkStatus()

        create_task(coro())

    def checkStatus(self):
        """ Updates self.status so it fits with what getStatus(boards[-1])
            would return. That is, if the game is e.g. check mated this will
            call mode.end(), or if moves have been undone from an otherwise
            ended position, this will call __resume and emit game_unended. """
        log.debug("GameModel.checkStatus:")

        # call flag by engine
        if self.isEngine2EngineGame() and self.status in UNDOABLE_STATES:
            return

        status, reason = getStatus(self.boards[-1])

        if self.practice_game and (len(self.moves) % 2 == 1 or status in UNDOABLE_STATES):
            self.check_goal(status, reason)

        if self.endstatus is not None:
            self.end(self.endstatus, reason)
            return

        if status != RUNNING and self.status in (WAITING_TO_START, PAUSED,
                                                 RUNNING):
            if status == DRAW and reason in (DRAW_REPITITION, DRAW_50MOVES):
                if self.isEngine2EngineGame():
                    self.end(status, reason)
                    return
            else:
                self.end(status, reason)
                return

        if status != self.status and self.status in UNDOABLE_STATES \
                and self.reason in UNDOABLE_REASONS:
            self.__resume()
            self.status = status
            self.reason = UNKNOWN_REASON
            self.emit("game_unended")

    def __pause(self):
        log.debug("GameModel.__pause: %s" % self)
        if self.isEngine2EngineGame():
            for player in self.players:
                player.end(self.status, self.reason)
            if self.timed:
                self.timemodel.end()
        else:
            for player in self.players:
                player.pause()
            if self.timed:
                self.timemodel.pause()

    def pause(self):
        """ Players will raise NotImplementedError if they doesn't support
            pause. Spectators will be ignored. """

        self.__pause()
        self.status = PAUSED
        self.emit("game_paused")

    def __resume(self):
        for player in self.players:
            player.resume()
        if self.timed:
            self.timemodel.resume()
        self.emit("game_resumed")

    def resume(self):
        self.status = RUNNING
        self.__resume()

    def end(self, status, reason):
        if self.status not in UNFINISHED_STATES:
            log.info(
                "GameModel.end: Can't end a game that's already ended: %s %s" %
                (status, reason))
            return
        if self.status not in (WAITING_TO_START, PAUSED, RUNNING):
            self.needsSave = True

        log.debug("GameModel.end: players=%s, self.ply=%s: Ending a game with status %d for reason %d" % (
            repr(self.players), str(self.ply), status, reason))
        self.status = status
        self.reason = reason

        self.emit("game_ended", reason)

        self.__pause()

    def kill(self, reason):
        log.debug("GameModel.kill: players=%s, self.ply=%s: Killing a game for reason %d\n%s" % (
                  repr(self.players), str(self.ply), reason, "".join(
                      traceback.format_list(traceback.extract_stack())).strip()))

        self.status = KILLED
        self.reason = reason

        for player in self.players:
            player.end(self.status, reason)

        for spectator in self.spectators.values():
            spectator.end(self.status, reason)

        if self.timed:
            self.timemodel.end()

        self.emit("game_ended", reason)

    def terminate(self):
        log.debug("GameModel.terminate: %s" % self)
        self.terminated = True

        if self.status != KILLED:
            for player in self.players:
                player.end(self.status, self.reason)

            analyzer_types = list(self.spectators.keys())
            for analyzer_type in analyzer_types:
                self.remove_analyzer(analyzer_type)

            if self.timed:
                log.debug("GameModel.terminate: -> timemodel.end()")
                self.timemodel.end()
                log.debug("GameModel.terminate: <- timemodel.end() %s" %
                          repr(self.timemodel))
                if self.zero_reached_cid is not None:
                    self.timemodel.disconnect(self.zero_reached_cid)

        # ICGameModel may did this if game was a FICS game
        if self.connections is not None:
            for player in self.players:
                for cid in self.connections[player]:
                    player.disconnect(cid)
        self.connections = {}

        self.timemodel.gamemodel = None
        self.players = []
        self.emit("game_terminated")

    # Other stuff

    def undoMoves(self, moves):
        """ Undo and remove moves number of moves from the game history from
            the GameModel, players, and any spectators """
        if self.ply < 1 or moves < 1:
            return
        if self.ply - moves < 0:
            # There is no way in the current threaded/asynchronous design
            # for the GUI to know that the number of moves it requests to takeback
            # will still be valid once the undo is actually processed. So, until
            # we either add some locking or get a synchronous design, we quietly
            # "fix" the takeback request rather than cause AssertionError or IndexError
            moves = 1

        log.debug("GameModel.undoMoves: players=%s, self.ply=%s, moves=%s, board=%s" % (
                  repr(self.players), self.ply, moves, self.boards[-1]))
        self.emit("moves_undoing", moves)
        self.needsSave = True

        self.boards = self.variations[0]
        del self.boards[-moves:]
        del self.moves[-moves:]
        self.boards[-1].board.next = None

        for player in self.players:
            player.playerUndoMoves(moves, self)
        for spectator in self.spectators.values():
            spectator.spectatorUndoMoves(moves, self)

        log.debug("GameModel.undoMoves: undoing timemodel")
        if self.timed:
            self.timemodel.undoMoves(moves)

        self.checkStatus()
        self.setOpening()

        self.emit("moves_undone", moves)

    def isChanged(self):
        if self.ply == 0:
            return False
        if self.needsSave:
            return True
        # what was this for?
        # if not self.uri or not isWriteable(self.uri):
            # return True
        return False

    def add_variation(self, board, moves, comment="", score="", emit=True):
        if board.board.next is None:
            # If we are in the latest played board, and want to add a variation
            # we have to add the latest move first
            if board.board.lastMove is None or board.board.prev is None:
                return
            moves = [Move(board.board.lastMove)] + moves
            board = board.board.prev.pieceBoard

        board0 = board
        board = board0.clone()
        board.board.prev = None

        # this prevents annotation panel node searches to find this instead of board0
        board.board.hash = -1

        if comment:
            board.board.children.append(comment)

        variation = [board]

        for move in moves:
            new = board.move(move)
            if len(variation) == 1:
                new.board.prev = board0.board
                variation[0].board.next = new.board
            else:
                new.board.prev = board.board
                board.board.next = new.board
            variation.append(new)
            board = new

        board0.board.next.children.append(
            [vboard.board for vboard in variation])
        if score:
            variation[-1].board.children.append(score)

        head = None
        for vari in self.variations:
            if board0 in vari:
                head = vari
                break

        variation[0] = board0
        self.variations.append(head[:board0.ply - self.lowply] + variation)
        self.needsSave = True
        if emit:
            self.emit("variation_added", board0.board.next.children[-1], board0.board.next)
        return self.variations[-1]

    def add_move2variation(self, board, move, variationIdx):
        new = board.move(move)
        new.board.prev = board.board
        board.board.next = new.board

        # Find the variation (low level lboard list) to append
        cur_board = board.board
        vari = None
        while cur_board.prev is not None:
            for child in cur_board.prev.next.children:
                if isinstance(child, list) and cur_board in child:
                    vari = child
                    break
            if vari is None:
                cur_board = cur_board.prev
            else:
                break
        vari.append(new.board)

        self.variations[variationIdx].append(new)
        self.needsSave = True
        self.emit("variation_extended", board.board, new.board)

    def remove_variation(self, board, parent):
        """ board must be an lboard object of the first Board object of a variation Board(!) list """
        # Remove the variation (list of lboards) containing board from parent's children list
        for child in parent.children:
            if isinstance(child, list) and board in child:
                parent.children.remove(child)
                break

        # Remove all variations from gamemodel's variations list which contains this board
        for vari in self.variations[1:]:
            if board.pieceBoard in vari:
                self.variations.remove(vari)

        # remove null_board if variation was added on last played move
        if not parent.fen_was_applied:
            parent.prev.next = None

        self.needsSave = True

    def undo_in_variation(self, board):
        """ board must be the latest Board object of a variation board list """
        assert board.board.next is None and len(board.board.children) == 0
        self.emit("variation_undoing")

        for vari in self.variations[1:]:
            if board in vari:
                break

        board = board.board
        parent = board.prev.next

        # If this is a one move only variation we have to remove the whole variation
        # if it's a longer one, just remove the latest move from it
        first_vari_moves = [child[1] for child in parent.children if not isinstance(child, str)]
        if board in first_vari_moves:
            self.remove_variation(board, parent)
        else:
            board.prev.next = None
            del vari[-1]

        self.needsSave = True
        self.emit("variation_undone")
