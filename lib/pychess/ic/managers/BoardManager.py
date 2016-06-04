from __future__ import print_function

import re
import threading

from gi.repository import GObject

from pychess.System.Log import log
from pychess.Savers.pgn import msToClockTimeTag

from pychess.Utils.const import WHITEWON, WON_RESIGN, WON_DISCONNECTION, WON_CALLFLAG, \
    BLACKWON, WON_MATE, WON_ADJUDICATION, WON_KINGEXPLODE, WON_NOMATERIAL, UNKNOWN_REASON, \
    DRAW, DRAW_REPITITION, DRAW_BLACKINSUFFICIENTANDWHITETIME, DRAW_WHITEINSUFFICIENTANDBLACKTIME, \
    DRAW_INSUFFICIENT, DRAW_CALLFLAG, DRAW_AGREE, DRAW_STALEMATE, DRAW_50MOVES, DRAW_LENGTH, \
    DRAW_ADJUDICATION, ADJOURNED, ADJOURNED_COURTESY_WHITE, ADJOURNED_COURTESY_BLACK, \
    ADJOURNED_COURTESY, ADJOURNED_AGREEMENT, ADJOURNED_LOST_CONNECTION_WHITE, \
    ADJOURNED_LOST_CONNECTION_BLACK, ADJOURNED_LOST_CONNECTION, ADJOURNED_SERVER_SHUTDOWN, \
    ABORTED, ABORTED_AGREEMENT, ABORTED_DISCONNECTION, ABORTED_EARLY, ABORTED_SERVER_SHUTDOWN, \
    ABORTED_ADJUDICATION, ABORTED_COURTESY, UNKNOWN_STATE, BLACK, WHITE, reprFile, \
    FISCHERRANDOMCHESS, CRAZYHOUSECHESS, WILDCASTLECHESS, WILDCASTLESHUFFLECHESS, ATOMICCHESS, \
    LOSERSCHESS, SUICIDECHESS

from pychess.ic import IC_POS_INITIAL, IC_POS_ISOLATED, IC_POS_OP_TO_MOVE, IC_POS_ME_TO_MOVE, \
    IC_POS_OBSERVING, IC_POS_OBSERVING_EXAMINATION, IC_POS_EXAMINATING, GAME_TYPES, IC_STATUS_PLAYING, \
    BLKCMD_SEEK, BLKCMD_OBSERVE, BLKCMD_MATCH, TYPE_WILD, BLKCMD_SMOVES, BLKCMD_UNOBSERVE, BLKCMD_MOVES, \
    BLKCMD_FLAG, parseRating

from pychess.ic.FICSObjects import FICSGame, FICSBoard, FICSHistoryGame, \
    FICSAdjournedGame, FICSJournalGame

names = "(\w+)"
titles = "((?:\((?:GM|IM|FM|WGM|WIM|WFM|TM|SR|TD|SR|CA|C|U|D|B|T|\*)\))+)?"
ratedexp = "(rated|unrated)"
ratings = "\(\s*([0-9\ \-\+]{1,4}[P E]?|UNR)\)"

weekdays = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
          "Nov", "Dec"]

# "Thu Oct 14, 20:36 PDT 2010"
dates = "(%s)\s+(%s)\s+(\d+),\s+(\d+):(\d+)\s+([A-Z\?]+)\s+(\d{4})" % \
    ("|".join(weekdays), "|".join(months))

# "2010-10-14 20:36 UTC"
datesFatICS = "(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})\s+(UTC)"

moveListHeader1Str = "%s %s vs. %s %s --- (?:%s|%s)" % (
    names, ratings, names, ratings, dates, datesFatICS)
moveListHeader1 = re.compile(moveListHeader1Str)
moveListHeader2Str = "%s ([^ ]+) match, initial time: (\d+) minutes, increment: (\d+) seconds\." % \
    ratedexp
moveListHeader2 = re.compile(moveListHeader2Str, re.IGNORECASE)
sanmove = "([a-hx@OoPKQRBN0-8+#=-]{2,7})"
movetime = "\((\d:)?(\d{1,2}):(\d\d)(?:\.(\d{1,3}))?\)"
moveListMoves = re.compile("\s*(\d+)\. +(?:%s|\.\.\.) +%s *(?:%s +%s)?" %
                           (sanmove, movetime, sanmove, movetime))

creating0 = re.compile(
    "Creating: %s %s %s %s %s ([^ ]+) (\d+) (\d+)(?: \(adjourned\))?" %
    (names, ratings, names, ratings, ratedexp))
creating1 = re.compile(
    "{Game (\d+) \(%s vs\. %s\) (?:Creating|Continuing) %s ([^ ]+) match\." %
    (names, names, ratedexp))
pr = re.compile("<pr> ([\d ]+)")
sr = re.compile("<sr> ([\d ]+)")

fileToEpcord = (("a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3"),
                ("a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6"))

relations = {"-4": IC_POS_INITIAL,
             "-3": IC_POS_ISOLATED,
             "-2": IC_POS_OBSERVING_EXAMINATION,
             "2": IC_POS_EXAMINATING,
             "-1": IC_POS_OP_TO_MOVE,
             "1": IC_POS_ME_TO_MOVE,
             "0": IC_POS_OBSERVING}


def parse_reason(result, reason, wname=None):
    """
    Parse the result value and reason line string for the reason and return
    the result and reason the game ended.

    result -- The result of the game, if known. It can be "None", but if it
    is "DRAW", then wname must be supplied
    """
    if result in (WHITEWON, BLACKWON):
        if "resigns" in reason:
            reason = WON_RESIGN
        elif "disconnection" in reason:
            reason = WON_DISCONNECTION
        elif "time" in reason:
            reason = WON_CALLFLAG
        elif "checkmated" in reason:
            reason = WON_MATE
        elif "adjudication" in reason:
            reason = WON_ADJUDICATION
        elif "exploded" in reason:
            reason = WON_KINGEXPLODE
        elif "material" in reason:
            reason = WON_NOMATERIAL
        else:
            reason = UNKNOWN_REASON
    elif result == DRAW:
        assert wname is not None
        if "repetition" in reason:
            reason = DRAW_REPITITION
        elif "material" in reason and "time" in reason:
            if wname + " ran out of time" in reason:
                reason = DRAW_BLACKINSUFFICIENTANDWHITETIME
            else:
                reason = DRAW_WHITEINSUFFICIENTANDBLACKTIME
        elif "material" in reason:
            reason = DRAW_INSUFFICIENT
        elif "time" in reason:
            reason = DRAW_CALLFLAG
        elif "agreement" in reason:
            reason = DRAW_AGREE
        elif "stalemate" in reason:
            reason = DRAW_STALEMATE
        elif "50" in reason:
            reason = DRAW_50MOVES
        elif "length" in reason:
            # FICS has a max game length on 800 moves
            reason = DRAW_LENGTH
        elif "adjudication" in reason:
            reason = DRAW_ADJUDICATION
        else:
            reason = UNKNOWN_REASON
    elif result == ADJOURNED or "adjourned" in reason:
        result = ADJOURNED
        if "courtesy" in reason:
            if wname:
                if wname in reason:
                    reason = ADJOURNED_COURTESY_WHITE
                else:
                    reason = ADJOURNED_COURTESY_BLACK
            elif "white" in reason:
                reason = ADJOURNED_COURTESY_WHITE
            elif "black" in reason:
                reason = ADJOURNED_COURTESY_BLACK
            else:
                reason = ADJOURNED_COURTESY
        elif "agreement" in reason:
            reason = ADJOURNED_AGREEMENT
        elif "connection" in reason:
            if "white" in reason:
                reason = ADJOURNED_LOST_CONNECTION_WHITE
            elif "black" in reason:
                reason = ADJOURNED_LOST_CONNECTION_BLACK
            else:
                reason = ADJOURNED_LOST_CONNECTION
        elif "server" in reason:
            reason = ADJOURNED_SERVER_SHUTDOWN
        else:
            reason = UNKNOWN_REASON
    elif "aborted" in reason:
        result = ABORTED
        if "agreement" in reason:
            reason = ABORTED_AGREEMENT
        elif "moves" in reason:
            # lost connection and too few moves; game aborted *
            reason = ABORTED_DISCONNECTION
        elif "move" in reason:
            # Game aborted on move 1 *
            reason = ABORTED_EARLY
        elif "shutdown" in reason:
            reason = ABORTED_SERVER_SHUTDOWN
        elif "adjudication" in reason:
            reason = ABORTED_ADJUDICATION
        else:
            reason = UNKNOWN_REASON
    elif "courtesyadjourned" in reason:
        result = ADJOURNED
        reason = ADJOURNED_COURTESY
    elif "courtesyaborted" in reason:
        result = ABORTED
        reason = ABORTED_COURTESY
    else:
        result = UNKNOWN_STATE
        reason = UNKNOWN_REASON

    return result, reason


class BoardManager(GObject.GObject):

    __gsignals__ = {
        'playGameCreated': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'obsGameCreated': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'exGameCreated': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'archiveGamePreview': (GObject.SignalFlags.RUN_FIRST, None,
                               (object, )),
        'boardUpdate': (GObject.SignalFlags.RUN_FIRST, None,
                        (int, int, int, str, str, str, str, int, int)),
        'timesUpdate': (GObject.SignalFlags.RUN_FIRST, None,
                        (int, int, int,)),
        'obsGameEnded': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'curGameEnded': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'obsGameUnobserved': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'madeExamined': (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        'madeUnExamined': (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        'gamePaused': (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
        'tooManySeeks': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'nonoWhileExamine': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'matchDeclined': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'player_on_censor': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'player_on_noplay': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'player_lagged': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'opp_not_out_of_time': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'req_not_fit_formula': (GObject.SignalFlags.RUN_FIRST, None,
                                (object, str)),
    }

    castleSigns = {}
    queuedStyle12s = {}

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
        self.connection.expect_line(self.onStyle12, "<12> (.+)")
        self.connection.expect_line(self.onWasPrivate,
                                    "Sorry, game (\d+) is a private game\.")
        self.connection.expect_line(self.tooManySeeks,
                                    "You can only have 3 active seeks.")
        self.connection.expect_line(
            self.nonoWhileExamine,
            "(?:You cannot challenge while you are examining a game.)|" +
            "(?:You are already examining a game.)")
        self.connection.expect_line(self.matchDeclined,
                                    "%s declines the match offer." % names)
        self.connection.expect_line(self.player_on_censor,
                                    "%s is censoring you." % names)
        self.connection.expect_line(self.player_on_noplay,
                                    "You are on %s's noplay list." % names)
        self.connection.expect_line(
            self.player_lagged,
            "Game (\d+): %s has lagged for (\d+) seconds\." % names)
        self.connection.expect_line(
            self.opp_not_out_of_time,
            "Opponent is not out of time, wait for server autoflag\.")

        self.connection.expect_n_lines(
            self.req_not_fit_formula,
            "Match request does not fit formula for %s:" % names,
            "%s's formula: (.+)" % names)

        if self.connection.USCN:
            self.connection.expect_n_lines(
                self.onPlayGameCreated,
                "Creating: %s %s %s %s %s ([^ ]+) (\d+) (\d+)(?: \(adjourned\))?"
                % (names, ratings, names, ratings, ratedexp), "",
                "{Game (\d+) \(%s vs\. %s\) (?:Creating|Continuing) %s ([^ ]+) match\."
                % (names, names, ratedexp), "", "<12> (.+)")
        else:
            self.connection.expect_n_lines(
                self.onPlayGameCreated,
                "Creating: %s %s %s %s %s ([^ ]+) (\d+) (\d+)(?: \(adjourned\))?"
                % (names, ratings, names, ratings, ratedexp),
                "{Game (\d+) \(%s vs\. %s\) (?:Creating|Continuing) %s ([^ ]+) match\."
                % (names, names, ratedexp), "", "<12> (.+)")

        # TODO: Trying to precisely match every type of possible response FICS
        # will throw at us for "Your seek matches..." or "Your seek qualifies
        # for [player]'s getgame" is error prone and we can never be sure we
        # even have all of the different types of replies the server will throw
        # at us. So we should probably make it possible for multi-line
        # prediction callbacks in VerboseTelnet to put lines the callback isn't
        # interested in or doesn't handle back onto the input line stack in
        # VerboseTelnet.TelnetLines
        self.connection.expect_fromto(
            self.onMatchingSeekOrGetGame,
            "Your seek (?:matches one already posted by %s|qualifies for %s's getgame)\."
            % (names, names), "(?:<12>|<sn>) (.+)")
        self.connection.expect_fromto(
            self.onInterceptedChallenge,
            "Your challenge intercepts %s's challenge\." % names, "<12> (.+)")

        if self.connection.USCN:
            self.connection.expect_n_lines(self.onObserveGameCreated,
                                           "You are now observing game \d+\.",
                                           '', "<12> (.+)")
        else:
            self.connection.expect_n_lines(
                self.onObserveGameCreated, "You are now observing game \d+\.",
                "Game (\d+): %s %s %s %s %s ([\w/]+) (\d+) (\d+)" %
                (names, ratings, names, ratings, ratedexp), '', "<12> (.+)")

        self.connection.expect_fromto(self.onObserveGameMovesReceived,
                                      "Movelist for game (\d+):",
                                      "{Still in progress} \*")

        self.connection.expect_fromto(
            self.onArchiveGameSMovesReceived,
            moveListHeader1Str,
            #                                       "\s*{((?:Game courtesyadjourned by (Black|White))|(?:Still in progress)|(?:Game adjourned by mutual agreement)|(?:(White|Black) lost connection; game adjourned)|(?:Game adjourned by ((?:server shutdown)|(?:adjudication)|(?:simul holder))))} \*")
            "\s*{.*(?:([Gg]ame.*adjourned.\s*)|(?:Still in progress)|(?:Neither.*)|(?:Game drawn.*)|(?:White.*)|(?:Black.*)).*}\s*(?:(?:1/2-1/2)|(?:1-0)|(?:0-1))?\s*")

        self.connection.expect_line(
            self.onGamePause, "Game (\d+): Game clock (paused|resumed)\.")
        self.connection.expect_line(
            self.onUnobserveGame,
            "Removing game (\d+) from observation list\.")

        self.connection.expect_line(
            self.made_examined,
            "%s has made you an examiner of game (\d+)\." % names)

        self.connection.expect_line(self.made_unexamined,
                                    "You are no longer examining game (\d+)\.")

        self.queuedEmits = {}
        self.gamemodelStartedEvents = {}
        self.theGameImPlaying = None
        self.gamesImObserving = {}

        # The ms ivar makes the remaining second fields in style12 use ms
        self.connection.client.run_command("iset ms 1")
        # Style12 is a must, when you don't want to parse visualoptimized stuff
        self.connection.client.run_command("set style 12")
        # When we observe fischer games, this puts a startpos in the movelist
        self.connection.client.run_command("iset startpos 1")
        # movecase ensures that bc3 will never be a bishop move
        self.connection.client.run_command("iset movecase 1")
        # don't unobserve games when we start a new game
        self.connection.client.run_command("set unobserve 3")
        self.connection.lvm.autoFlagNotify()

        # gameinfo <g1> doesn't really have any interesting info, at least not
        # until we implement crasyhouse and stuff
        # self.connection.client.run_command("iset gameinfo 1")

    def start(self):
        self.connection.games.connect("FICSGameEnded", self.onGameEnd)

    @classmethod
    def parseStyle12(cls, line, castleSigns=None):
        fields = line.split()

        curcol = fields[8] == "B" and BLACK or WHITE
        gameno = int(fields[15])
        relation = relations[fields[18]]
        ply = int(fields[25]) * 2 - (curcol == WHITE and 2 or 1)
        lastmove = fields[28] != "none" and fields[28] or None
        wname = fields[16]
        bname = fields[17]
        wms = int(fields[23])
        bms = int(fields[24])
        gain = int(fields[20])

        # Board data
        fenrows = []
        for row in fields[:8]:
            fenrow = []
            spaceCounter = 0
            for char in row:
                if char == "-":
                    spaceCounter += 1
                else:
                    if spaceCounter:
                        fenrow.append(str(spaceCounter))
                        spaceCounter = 0
                    fenrow.append(char)
            if spaceCounter:
                fenrow.append(str(spaceCounter))
            fenrows.append("".join(fenrow))

        fen = "/".join(fenrows)
        fen += " "

        # Current color
        fen += fields[8].lower()
        fen += " "

        # Castling
        if fields[10:14] == ["0", "0", "0", "0"]:
            fen += "-"
        else:
            if fields[10] == "1":
                fen += castleSigns[0].upper()
            if fields[11] == "1":
                fen += castleSigns[1].upper()
            if fields[12] == "1":
                fen += castleSigns[0].lower()
            if fields[13] == "1":
                fen += castleSigns[1].lower()
        fen += " "
        # 1 0 1 1 when short castling k1 last possibility

        # En passant
        if fields[9] == "-1":
            fen += "-"
        else:
            fen += fileToEpcord[1 - curcol][int(fields[9])]
        fen += " "

        # Half move clock
        fen += str(max(int(fields[14]), 0))
        fen += " "

        # Standard chess numbering
        fen += fields[25]

        return gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen

    def onStyle12(self, match):
        style12 = match.groups()[0]
        gameno = int(style12.split()[15])
        if gameno in self.queuedStyle12s:
            self.queuedStyle12s[gameno].append(style12)
            return

        try:
            self.gamemodelStartedEvents[gameno].wait()
        except KeyError:
            pass

        if gameno in self.castleSigns:
            castleSigns = self.castleSigns[gameno]
        else:
            castleSigns = ("k", "q")
        gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
            self.parseStyle12(style12, castleSigns)

        # examine starts with a <12> line only
        if lastmove is None and relation == IC_POS_EXAMINATING:
            pgnHead = [
                ("Event", "FICS examined game"), ("Site", "freechess.org"),
                ("White", wname), ("Black", bname), ("Result", "*"),
                ("SetUp", "1"), ("FEN", fen)
            ]
            pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n*\n"
            wplayer = self.connection.players.get(wname)
            bplayer = self.connection.players.get(bname)

            # examine from console or got mexamine in observed game
            if self.connection.examined_game is None:
                no_smoves = True
                game = FICSGame(wplayer,
                                bplayer,
                                gameno=int(gameno),
                                game_type=GAME_TYPES["examined"],
                                minutes=0,
                                inc=0,
                                board=FICSBoard(0,
                                                0,
                                                pgn=pgn),
                                relation=relation)
                self.connection.examined_game = game
            else:
                # examine an archived game from GUI
                no_smoves = False
                game = self.connection.examined_game
                game.gameno = int(gameno)
                game.relation = relation
                # game.game_type = GAME_TYPES["examined"]
            game = self.connection.games.get(game)

            # don't start new game in puzzlebot/endgamebot when they just reuse gameno
            if game.relation == IC_POS_OBSERVING_EXAMINATION or \
                    (game.board is not None and game.board.pgn == pgn):
                self.emit("boardUpdate", gameno, ply, curcol, lastmove, fen,
                          wname, bname, wms, bms)
                return

            game.relation = relation
            game.board = FICSBoard(0, 0, pgn=pgn)
            self.gamesImObserving[game] = wms, bms

            # start a new game now or after smoves
            self.gamemodelStartedEvents[game.gameno] = threading.Event()
            if no_smoves:
                self.emit("exGameCreated", game)
                self.gamemodelStartedEvents[game.gameno].wait()
            else:
                if isinstance(game, FICSHistoryGame):
                    self.connection.client.run_command("smoves %s %s" % (
                        self.connection.history_owner, game.history_no))
                elif isinstance(game, FICSJournalGame):
                    self.connection.client.run_command("smoves %s %%%s" % (
                        self.connection.journal_owner, game.journal_no))
                elif isinstance(game, FICSAdjournedGame):
                    self.connection.client.run_command("smoves %s %s" % (
                        self.connection.stored_owner, game.opponent.name))
                self.connection.client.run_command("forward 999")
        else:
            self.emit("boardUpdate", gameno, ply, curcol, lastmove, fen, wname,
                      bname, wms, bms)

    def onGameModelStarted(self, gameno):
        self.gamemodelStartedEvents[gameno].set()

    def onWasPrivate(self, match):
        # When observable games were added to the list later than the latest
        # full send, private information will not be known.
        gameno = int(match.groups()[0])
        try:
            game = self.connection.games.get_game_by_gameno(gameno)
        except KeyError:
            return
        game.private = True

    onWasPrivate.BLKCMD = BLKCMD_OBSERVE

    def tooManySeeks(self, match):
        self.emit("tooManySeeks")

    tooManySeeks.BLKCMD = BLKCMD_SEEK

    def nonoWhileExamine(self, match):
        self.emit("nonoWhileExamine")

    nonoWhileExamine.BLKCMD = BLKCMD_SEEK

    def matchDeclined(self, match):
        decliner, = match.groups()
        decliner = self.connection.players.get(decliner)
        self.emit("matchDeclined", decliner)

    @classmethod
    def generateCastleSigns(cls, style12, game_type):
        if game_type.variant_type == FISCHERRANDOMCHESS:
            backrow = style12.split()[0]
            leftside = backrow.find("r")
            rightside = backrow.find("r", leftside + 1)
            return (reprFile[rightside], reprFile[leftside])
        else:
            return ("k", "q")

    def onPlayGameCreated(self, matchlist):
        log.debug(
            "'%s' '%s' '%s'" %
            (matchlist[0].string, matchlist[1].string, matchlist[-1].string),
            extra={"task": (self.connection.username, "BM.onPlayGameCreated")})
        wname, wrating, bname, brating, rated, match_type, minutes, inc = matchlist[
            0].groups()
        item = 2 if self.connection.USCN else 1
        gameno, wname, bname, rated, match_type = matchlist[item].groups()
        gameno = int(gameno)
        wrating = parseRating(wrating)
        brating = parseRating(brating)
        rated = rated == "rated"
        game_type = GAME_TYPES[match_type]

        wplayer = self.connection.players.get(wname)
        bplayer = self.connection.players.get(bname)
        for player, rating in ((wplayer, wrating), (bplayer, brating)):
            if game_type.rating_type in player.ratings and \
                    player.ratings[game_type.rating_type] != rating:
                player.ratings[game_type.rating_type] = rating
                player.emit("ratings_changed", game_type.rating_type, player)

        style12 = matchlist[-1].groups()[0]
        castleSigns = self.generateCastleSigns(style12, game_type)
        self.castleSigns[gameno] = castleSigns
        gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
            self.parseStyle12(style12, castleSigns)

        game = FICSGame(wplayer,
                        bplayer,
                        gameno=gameno,
                        rated=rated,
                        game_type=game_type,
                        minutes=int(minutes),
                        inc=int(inc),
                        board=FICSBoard(wms,
                                        bms,
                                        fen=fen))

        game = self.connection.games.get(game)

        for player in (wplayer, bplayer):
            if player.status != IC_STATUS_PLAYING:
                player.status = IC_STATUS_PLAYING
            if player.game != game:
                player.game = game

        self.theGameImPlaying = game
        self.gamemodelStartedEvents[gameno] = threading.Event()
        self.connection.client.run_command("follow")
        self.emit("playGameCreated", game)

    def onMatchingSeekOrGetGame(self, matchlist):
        if matchlist[-1].string.startswith("<12>"):
            for line in matchlist[1:-4]:
                if line.startswith("<sr>"):
                    self.connection.glm.on_seek_remove(sr.match(line))
                elif line.startswith("<pr>"):
                    self.connection.om.onOfferRemove(pr.match(line))
            self.onPlayGameCreated((creating0.match(matchlist[
                -4]), creating1.match(matchlist[-3]), matchlist[-1]))
        else:
            self.connection.glm.on_seek_add(matchlist[-1])

    onMatchingSeekOrGetGame.BLKCMD = BLKCMD_SEEK

    def onInterceptedChallenge(self, matchlist):
        self.onMatchingSeekOrGetGame(matchlist)

    onInterceptedChallenge.BLKCMD = BLKCMD_MATCH

    def parseGame(self, matchlist, gameclass, in_progress=False, gameno=None):
        """
        Parses the header and movelist for an observed or stored game from its
        matchlist (an re.match object) into a gameclass (FICSGame or subclass
        of) object.

        in_progress - should be True for an observed game matchlist, and False
        for stored/adjourned games
        """
        # ################   observed game movelist example:
        #        Movelist for game 64:
        #
        #        Ajido (2281) vs. IMgooeyjim (2068) --- Thu Oct 14, 20:36 PDT 2010
        #        Rated standard match, initial time: 15 minutes, increment: 3 seconds.
        #
        #        Move  Ajido                   IMgooeyjim
        #        ----  ---------------------   ---------------------
        #          1.  d4      (0:00.000)      Nf6     (0:00.000)
        #          2.  c4      (0:04.061)      g6      (0:00.969)
        #          3.  Nc3     (0:13.280)      Bg7     (0:06.422)
        #              {Still in progress} *
        #
        # #################   stored game example:
        #        BwanaSlei (1137) vs. mgatto (1336) --- Wed Nov  5, 20:56 PST 2008
        #        Rated blitz match, initial time: 5 minutes, increment: 0 seconds.
        #
        #        Move  BwanaSlei               mgatto
        #        ----  ---------------------   ---------------------
        #        1.  e4      (0:00.000)      c5      (0:00.000)
        #        2.  d4      (0:05.750)      cxd4    (0:03.020)
        #        ...
        #        23.  Qxf3    (1:05.500)
        #             {White lost connection; game adjourned} *
        #
        # ################# stored wild/3 game with style12:
        #        kurushi (1626) vs. mgatto (1627) --- Thu Nov  4, 10:33 PDT 2010
        #        Rated wild/3 match, initial time: 3 minutes, increment: 0 seconds.
        #
        #        <12> nqbrknrn pppppppp -------- -------- -------- -------- PPPPPPPP NQBRKNRN W -1 0 0 0 0 0 17 kurushi mgatto -4 3 0 39 39 169403 45227 1 none (0:00.000) none 0 1 0
        #
        #        Move  kurushi                 mgatto
        #        ----  ---------------------   ---------------------
        #          1.  Nb3     (0:00.000)      d5      (0:00.000)
        #          2.  Nhg3    (0:00.386)      e5      (0:03.672)
        #         ...
        #         28.  Rxd5    (0:00.412)
        #              {Black lost connection; game adjourned} *
        #
        # #################  stored game movelist following stored game(s):
        #        Stored games for mgatto:
        #        C Opponent       On Type          Str  M    ECO Date
        #        1: W BabyLurking     Y [ br  5   0] 29-13 W27  D37 Fri Nov  5, 04:41 PDT 2010
        #        2: W gbtami          N [ wr  5   0] 32-34 W14  --- Thu Oct 21, 00:14 PDT 2010
        #
        #        mgatto (1233) vs. BabyLurking (1455) --- Fri Nov  5, 04:33 PDT 2010
        #        Rated blitz match, initial time: 5 minutes, increment: 0 seconds.
        #
        #        Move  mgatto             BabyLurking
        #        ----  ----------------   ----------------
        #        1.  Nf3     (0:00)     d5      (0:00)
        #        2.  d4      (0:03)     Nf6     (0:00)
        #        3.  c4      (0:03)     e6      (0:00)
        #        {White lost connection; game adjourned} *
        #
        # ################## stored game movelist following stored game(s):
        # ##   Note: A wild stored game in this format won't be parseable into a board because
        # ##   it doesn't come with a style12 that has the start position, so we warn and return
        # ##################
        #        Stored games for mgatto:
        #        C Opponent       On Type          Str  M    ECO Date
        #        1: W gbtami          N [ wr  5   0] 32-34 W14  --- Thu Oct 21, 00:14 PDT 2010
        #
        #        mgatto (1627) vs. gbtami (1881) --- Thu Oct 21, 00:10 PDT 2010
        #        Rated wild/fr match, initial time: 5 minutes, increment: 0 seconds.
        #
        #        Move  mgatto             gbtami
        #        ----  ----------------   ----------------
        #        1.  d4      (0:00)     b6      (0:00)
        #        2.  b3      (0:06)     d5      (0:03)
        #        3.  c4      (0:08)     e6      (0:03)
        #        4.  e3      (0:04)     dxc4    (0:02)
        #        5.  bxc4    (0:02)     g6      (0:09)
        #        6.  Nd3     (0:12)     Bg7     (0:02)
        #        7.  Nc3     (0:10)     Ne7     (0:03)
        #        8.  Be2     (0:08)     c5      (0:05)
        #        9.  a4      (0:07)     cxd4    (0:38)
        #        10.  exd4    (0:06)     Bxd4    (0:03)
        #        11.  O-O     (0:10)     Qc6     (0:06)
        #        12.  Bf3     (0:16)     Qxc4    (0:04)
        #        13.  Bxa8    (0:03)     Rxa8    (0:14)
        #        {White lost connection; game adjourned} *
        #
        # #################   other reasons the game could be stored/adjourned:
        #        Game courtesyadjourned by (Black|White)
        #        Still in progress                    # This one must be a FICS bug
        #        Game adjourned by mutual agreement
        #        (White|Black) lost connection; game adjourned
        #        Game adjourned by ((server shutdown)|(adjudication)|(simul holder))

        index = 0
        if in_progress:
            gameno = int(matchlist[index].groups()[0])
            index += 2
        header1 = matchlist[index] if isinstance(matchlist[index], str) \
            else matchlist[index].group()

        matches = moveListHeader1.match(header1).groups()
        wname, wrating, bname, brating = matches[:4]
        if self.connection.FatICS:
            year, month, day, hour, minute, timezone = matches[11:]
        else:
            weekday, month, day, hour, minute, timezone, year = matches[4:11]
            month = months.index(month) + 1

        wrating = parseRating(wrating)
        brating = parseRating(brating)
        rated, game_type, minutes, increment = \
            moveListHeader2.match(matchlist[index + 1]).groups()
        minutes = int(minutes)
        increment = int(increment)
        game_type = GAME_TYPES[game_type]

        reason = matchlist[-1].group().lower()
        if in_progress:
            result = None
            result_str = "*"
        elif "1-0" in reason:
            result = WHITEWON
            result_str = "1-0"
        elif "0-1" in reason:
            result = BLACKWON
            result_str = "0-1"
        elif "1/2-1/2" in reason:
            result = DRAW
            result_str = "1/2-1/2"
        else:
            result = ADJOURNED
            result_str = "*"
        result, reason = parse_reason(result, reason, wname=wname)

        index += 3
        if matchlist[index].startswith("<12>"):
            style12 = matchlist[index][5:]
            castleSigns = self.generateCastleSigns(style12, game_type)
            gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, \
                fen = self.parseStyle12(style12, castleSigns)
            initialfen = fen
            movesstart = index + 4
        else:
            if game_type.rating_type == TYPE_WILD:
                # we need a style12 start position to correctly parse a wild/* board
                log.error("BoardManager.parseGame: no style12 for %s board." %
                          game_type.fics_name)
                return None
            castleSigns = ("k", "q")
            initialfen = None
            movesstart = index + 2

        if in_progress:
            self.castleSigns[gameno] = castleSigns

        moves = {}
        times = {}
        wms = bms = minutes * 60 * 1000

        for line in matchlist[movesstart:-1]:
            if not moveListMoves.match(line):
                log.error("BoardManager.parseGame: unmatched line: \"%s\"" %
                          repr(line))
                raise Exception("BoardManager.parseGame: unmatched line: \"%s\"" % repr(line))
            moveno, wmove, whour, wmin, wsec, wmsec, bmove, bhour, bmin, bsec, bmsec = \
                moveListMoves.match(line).groups()
            whour = 0 if whour is None else int(whour[0])
            bhour = 0 if bhour is None else int(bhour[0])
            ply = int(moveno) * 2 - 2
            if wmove:
                moves[ply] = wmove
                wms -= (int(whour) * 60 * 60 * 1000) + (
                    int(wmin) * 60 * 1000) + (int(wsec) * 1000)
                if wmsec is not None:
                    wms -= int(wmsec)
                else:
                    wmsec = 0
                if increment > 0:
                    wms += (increment * 1000)
                times[ply] = "%01d:%02d:%02d.%03d" % (int(whour), int(wmin),
                                                      int(wsec), int(wmsec))
            if bmove:
                moves[ply + 1] = bmove
                bms -= (int(bhour) * 60 * 60 * 1000) + (
                    int(bmin) * 60 * 1000) + (int(bsec) * 1000)
                if bmsec is not None:
                    bms -= int(bmsec)
                else:
                    bmsec = 0
                if increment > 0:
                    bms += (increment * 1000)
                times[ply + 1] = "%01d:%02d:%02d.%03d" % (
                    int(bhour), int(bmin), int(bsec), int(bmsec))

        if in_progress and gameno in self.queuedStyle12s:
            # Apply queued board updates
            for style12 in self.queuedStyle12s[gameno]:
                gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
                    self.parseStyle12(style12, castleSigns)
                if lastmove is None:
                    continue
                moves[ply - 1] = lastmove
                # Updated the queuedMoves in case there has been a takeback
                for moveply in list(moves.keys()):
                    if moveply > ply - 1:
                        del moves[moveply]
            del self.queuedStyle12s[gameno]

        pgnHead = [
            ("Event", "FICS %s %s game" %
             (rated.lower(), game_type.fics_name)),
            ("Site", "freechess.org"),
            ("White", wname),
            ("Black", bname),
            ("TimeControl", "%d+%d" % (minutes * 60, increment)),
            ("Result", result_str),
            ("WhiteClock", msToClockTimeTag(wms)),
            ("BlackClock", msToClockTimeTag(bms)),
        ]
        if wrating != 0:
            pgnHead += [("WhiteElo", wrating)]
        if brating != 0:
            pgnHead += [("BlackElo", brating)]
        if year and month and day and hour and minute:
            pgnHead += [
                ("Date", "%04d.%02d.%02d" % (int(year), int(month), int(day))),
                ("Time", "%02d:%02d:00" % (int(hour), int(minute))),
            ]
        if initialfen:
            pgnHead += [("SetUp", "1"), ("FEN", initialfen)]
        if game_type.variant_type == FISCHERRANDOMCHESS:
            pgnHead += [("Variant", "Fischerandom")]
            # FR is the only variant used in this tag by the PGN generator @
            # ficsgames.org. They put all the other wild/* stuff only in the
            # "Event" header.
        elif game_type.variant_type == CRAZYHOUSECHESS:
            pgnHead += [("Variant", "Crazyhouse")]
        elif game_type.variant_type in (WILDCASTLECHESS,
                                        WILDCASTLESHUFFLECHESS):
            pgnHead += [("Variant", "Wildcastle")]
        elif game_type.variant_type == ATOMICCHESS:
            pgnHead += [("Variant", "Atomic")]
        elif game_type.variant_type == LOSERSCHESS:
            pgnHead += [("Variant", "Losers")]
        elif game_type.variant_type == SUICIDECHESS:
            pgnHead += [("Variant", "Suicide")]
        pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n"

        moves = sorted(moves.items())
        for ply, move in moves:
            if ply % 2 == 0:
                pgn += "%d. " % (ply // 2 + 1)
            time = times[ply]
            pgn += "%s {[%%emt %s]} " % (move, time)
        pgn += "*\n"

        wplayer = self.connection.players.get(wname)
        bplayer = self.connection.players.get(bname)
        for player, rating in ((wplayer, wrating), (bplayer, brating)):
            if game_type.rating_type in player.ratings and \
                    player.ratings[game_type.rating_type] != rating:
                player.ratings[game_type.rating_type] = rating
                player.emit("ratings_changed", game_type.rating_type, player)
        game = gameclass(wplayer,
                         bplayer,
                         game_type=game_type,
                         result=result,
                         rated=(rated.lower() == "rated"),
                         minutes=minutes,
                         inc=increment,
                         board=FICSBoard(wms,
                                         bms,
                                         pgn=pgn))

        if in_progress:
            game.gameno = gameno
        else:
            if gameno is not None:
                game.gameno = gameno
            game.reason = reason
        game = self.connection.games.get(game, emit=False)

        return game

    def onObserveGameCreated(self, matchlist):
        log.debug("'%s'" % (matchlist[1].string),
                  extra={"task": (self.connection.username,
                                  "BM.onObserveGameCreated")})
        if self.connection.USCN:
            # TODO? is this ok?
            game_type = GAME_TYPES["blitz"]
            castleSigns = ("k", "q")
        else:
            gameno, wname, wrating, bname, brating, rated, gametype, minutes, inc = matchlist[
                1].groups()
            wrating = parseRating(wrating)
            brating = parseRating(brating)
            game_type = GAME_TYPES[gametype]

        style12 = matchlist[-1].groups()[0]

        castleSigns = self.generateCastleSigns(style12, game_type)
        gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
            self.parseStyle12(style12, castleSigns)
        gameno = int(gameno)
        self.castleSigns[gameno] = castleSigns

        wplayer = self.connection.players.get(wname)
        bplayer = self.connection.players.get(bname)

        if relation == IC_POS_OBSERVING_EXAMINATION:
            pgnHead = [
                ("Event", "FICS %s %s game" % (rated, game_type.fics_name)),
                ("Site", "freechess.org"), ("White", wname), ("Black", bname),
                ("Result", "*"), ("SetUp", "1"), ("FEN", fen)
            ]
            pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n*\n"
            game = FICSGame(wplayer,
                            bplayer,
                            gameno=gameno,
                            rated=rated == "rated",
                            game_type=game_type,
                            minutes=int(minutes),
                            inc=int(inc),
                            board=FICSBoard(wms,
                                            bms,
                                            pgn=pgn),
                            relation=relation)
            game = self.connection.games.get(game)
            self.gamesImObserving[game] = wms, bms

            self.gamemodelStartedEvents[game.gameno] = threading.Event()
            self.emit("obsGameCreated", game)
            self.gamemodelStartedEvents[game.gameno].wait()
        else:
            game = FICSGame(wplayer,
                            bplayer,
                            gameno=gameno,
                            rated=rated == "rated",
                            game_type=game_type,
                            minutes=int(minutes),
                            inc=int(inc),
                            relation=relation)
            game = self.connection.games.get(game, emit=False)

            if not game.supported:
                log.warning("Trying to follow an unsupported type game %s" %
                            game.game_type)
                return

            if game.gameno in self.gamemodelStartedEvents:
                log.warning("%s already in gamemodelstartedevents" %
                            game.gameno)
                return

            self.gamesImObserving[game] = wms, bms
            self.queuedStyle12s[game.gameno] = []
            self.queuedEmits[game.gameno] = []
            self.gamemodelStartedEvents[game.gameno] = threading.Event()

            # FICS doesn't send the move list after 'observe' and 'follow' commands
            self.connection.client.run_command("moves %d" % game.gameno)

    onObserveGameCreated.BLKCMD = BLKCMD_OBSERVE

    def onObserveGameMovesReceived(self, matchlist):
        log.debug("'%s'" % (matchlist[0].string),
                  extra={"task": (self.connection.username,
                                  "BM.onObserveGameMovesReceived")})
        game = self.parseGame(matchlist, FICSGame, in_progress=True)
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

    onObserveGameMovesReceived.BLKCMD = BLKCMD_MOVES

    def onArchiveGameSMovesReceived(self, matchlist):
        log.debug("'%s'" % (matchlist[0].string),
                  extra={"task": (self.connection.username,
                                  "BM.onArchiveGameSMovesReceived")})
        klass = FICSAdjournedGame if "adjourn" in matchlist[-1].group(
        ) else FICSHistoryGame
        if self.connection.examined_game is not None:
            gameno = self.connection.examined_game.gameno
        else:
            gameno = None
        game = self.parseGame(matchlist,
                              klass,
                              in_progress=False,
                              gameno=gameno)
        if game.gameno not in self.gamemodelStartedEvents:
            self.emit("archiveGamePreview", game)
            return
        game.relation = IC_POS_EXAMINATING
        game.game_type = GAME_TYPES["examined"]
        self.emit("exGameCreated", game)
        try:
            self.gamemodelStartedEvents[game.gameno].wait()
        except KeyError:
            pass

    onArchiveGameSMovesReceived.BLKCMD = BLKCMD_SMOVES

    def onGameEnd(self, games, game):
        log.debug("BM.onGameEnd: %s" % game)
        if game == self.theGameImPlaying:
            if game.gameno in self.gamemodelStartedEvents:
                self.gamemodelStartedEvents[game.gameno].wait()
            self.emit("curGameEnded", game)
            self.theGameImPlaying = None
            del self.gamemodelStartedEvents[game.gameno]

        elif game in self.gamesImObserving:
            log.debug("BM.onGameEnd: %s: gamesImObserving" % game)
            if game.gameno in self.queuedEmits:
                log.debug("BM.onGameEnd: %s: queuedEmits" % game)
                self.queuedEmits[game.gameno].append(
                    lambda: self.emit("obsGameEnded", game))
            else:
                try:
                    event = self.gamemodelStartedEvents[game.gameno]
                except KeyError:
                    pass
                else:
                    log.debug("BM.onGameEnd: %s: event.wait()" % game)
                    event.wait()
                del self.gamesImObserving[game]
                self.emit("obsGameEnded", game)

    def onGamePause(self, match):
        gameno, state = match.groups()
        gameno = int(gameno)
        if gameno in self.queuedEmits:
            self.queuedEmits[gameno].append(
                lambda: self.emit("gamePaused", gameno, state == "paused"))
        else:
            if gameno in self.gamemodelStartedEvents:
                self.gamemodelStartedEvents[gameno].wait()
            self.emit("gamePaused", gameno, state == "paused")

    def onUnobserveGame(self, match):
        gameno = int(match.groups()[0])
        log.debug("BM.onUnobserveGame: gameno: %s" % gameno)
        try:
            del self.gamemodelStartedEvents[gameno]
            game = self.connection.games.get_game_by_gameno(gameno)
        except KeyError:
            return
        self.emit("obsGameUnobserved", game)
        # TODO: delete self.castleSigns[gameno] ?

    onUnobserveGame.BLKCMD = BLKCMD_UNOBSERVE

    def player_lagged(self, match):
        gameno, player, num_seconds = match.groups()
        player = self.connection.players.get(player)
        self.emit("player_lagged", player)

    def opp_not_out_of_time(self, match):
        self.emit("opp_not_out_of_time")

    opp_not_out_of_time.BLKCMD = BLKCMD_FLAG

    def req_not_fit_formula(self, matchlist):
        player, formula = matchlist[1].groups()
        player = self.connection.players.get(player)
        self.emit("req_not_fit_formula", player, formula)

    req_not_fit_formula.BLKCMD = BLKCMD_MATCH

    def player_on_censor(self, match):
        player, = match.groups()
        player = self.connection.players.get(player)
        self.emit("player_on_censor", player)

    player_on_censor.BLKCMD = BLKCMD_MATCH

    def player_on_noplay(self, match):
        player, = match.groups()
        player = self.connection.players.get(player)
        self.emit("player_on_noplay", player)

    player_on_noplay.BLKCMD = BLKCMD_MATCH

    def made_examined(self, match):
        """ Changing from observer to examiner """
        player, gameno = match.groups()
        gameno = int(gameno)
        try:
            self.connection.games.get_game_by_gameno(gameno)
        except KeyError:
            return
        self.emit("madeExamined", gameno)

    def made_unexamined(self, match):
        """You are no longer examine game"""
        self.connection.examined_game = None
        gameno, = match.groups()
        gameno = int(gameno)
        try:
            self.connection.games.get_game_by_gameno(gameno)
        except KeyError:
            return
        self.emit("madeUnExamined", gameno)

    ############################################################################
    #   Interacting                                                            #
    ############################################################################

    def isPlaying(self):
        return self.theGameImPlaying is not None

    def sendMove(self, move):
        self.connection.client.run_command(move)

    def resign(self):
        self.connection.client.run_command("resign")

    def callflag(self):
        self.connection.client.run_command("flag")

    def observe(self, game, player=None):
        if game is not None:
            self.connection.client.run_command("observe %d" % game.gameno)
        elif player is not None:
            self.connection.client.run_command("observe %s" % player.name)

    def follow(self, player):
        self.connection.client.run_command("follow %s" % player.name)

    def unexamine(self):
        self.connection.client.run_command("unexamine")

    def unobserve(self, game):
        if game.gameno is not None:
            self.connection.client.run_command("unobserve %d" % game.gameno)

    def play(self, seekno):
        self.connection.client.run_command("play %s" % seekno)

    def accept(self, offerno):
        self.connection.client.run_command("accept %s" % offerno)

    def decline(self, offerno):
        self.connection.client.run_command("decline %s" % offerno)


if __name__ == "__main__":
    from pychess.ic.FICSConnection import Connection
    con = Connection("", "", "", "")
    bm = BoardManager(con)

    print(bm._BoardManager__parseStyle12(
        "rkbrnqnb pppppppp -------- -------- -------- -------- PPPPPPPP RKBRNQNB W -1 1 1 1 1 0 161 GuestNPFS GuestMZZK -1 2 12 39 39 120 120 1 none (0:00) none 1 0 0",
        ("d", "a")))

    print(bm._BoardManager__parseStyle12(
        "rnbqkbnr pppp-ppp -------- ----p--- ----PP-- -------- PPPP--PP RNBQKBNR B 5 1 1 1 1 0 241 GuestGFFC GuestNXMP -4 2 12 39 39 120000 120000 1 none (0:00.000) none 0 0 0",
        ("k", "q")))
