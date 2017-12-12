import datetime

from gi.repository import GObject
from .BoardManager import names, months, dates

from pychess.ic import GAME_TYPES_BY_SHORT_FICS_NAME, BLKCMD_STORED, \
    BLKCMD_HISTORY, BLKCMD_JOURNAL
from pychess.ic.FICSObjects import FICSAdjournedGame, FICSHistoryGame, FICSJournalGame

from pychess.Utils.const import WON_ADJUDICATION, DRAW_AGREE, WON_DISCONNECTION, WON_CALLFLAG, \
    WON_MATE, DRAW_INSUFFICIENT, DRAW_REPITITION, WON_RESIGN, DRAW_STALEMATE, \
    DRAW_BLACKINSUFFICIENTANDWHITETIME, WON_NOMATERIAL, DRAW_50MOVES, WHITEWON, DRAW, \
    BLACK, WHITE, BLACKWON, reprResult, ADJOURNED

from pychess.System.Log import log

reasons_dict = {
    "Adj": WON_ADJUDICATION,
    "Agr": DRAW_AGREE,
    "Dis": WON_DISCONNECTION,
    "Fla": WON_CALLFLAG,
    "Mat": WON_MATE,
    "NM": DRAW_INSUFFICIENT,
    "Rep": DRAW_REPITITION,
    "Res": WON_RESIGN,
    "Sta": DRAW_STALEMATE,
    "TM":
    DRAW_BLACKINSUFFICIENTANDWHITETIME,  # DRAW_WHITEINSUFFICIENTANDBLACKTIME
    "WLM": WON_NOMATERIAL,
    "WNM": WON_NOMATERIAL,
    "50": DRAW_50MOVES
}

reasons = "(%s)" % "|".join(reasons_dict.keys())
ratings = "([0-9\ \-\+]{1,4}[P E]?|UNR)"


class AdjournManager(GObject.GObject):

    __gsignals__ = {
        'adjournedGameAdded': (GObject.SignalFlags.RUN_FIRST, None,
                               (object, )),
        'onAdjournmentsList': (GObject.SignalFlags.RUN_FIRST, None,
                               (object, )),
        'historyGameAdded': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'onHistoryList': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'journalGameAdded': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'onJournalList': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)

        self.connection = connection

        self.connection.expect_line(self.__onStoredResponseNO,
                                    "%s has no adjourned games\." % names)

        self.connection.expect_line(self.__onHistoryResponseNO,
                                    "%s has no history games\." % names)

        self.connection.expect_line(
            self.__onJournalResponseNO,
            "(%s has no journal entries\.)|(That journal is private.)" % names)

        self.connection.expect_fromABplus(
            self.__onStoredResponseYES, "Stored games for %s:" % names,
            "\s*C Opponent\s+On Type\s+Str\s+M\s+ECO\s+Date",
            "\s*\d+: (B|W) %s\s+(Y|N) \[([a-z ]{3})\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(---|\?\?\?|\*\*\*|[A-Z]\d+)\s+%s"
            % (names, dates))

        self.connection.expect_fromABplus(
            self.__onHistoryResponseYES, "History for %s:" % names,
            "\s*Opponent\s+Type\s+ECO\s+End\s+Date",
            "\s*(\d+): (-|\+|=)\s+(\d+)\s+(W|B)\s+(\d+) %s\s+\[([a-z ]{3})\s*(\d+)\s+(\d+)\]\s+(---|\?\?\?|\*\*\*|[A-Z]\d+)\s+%s\s+%s"
            % (names, reasons, dates))

        self.connection.expect_fromABplus(
            self.__onJournalResponseYES, "Journal for %s:" % names,
            "\s*White\s+Rating\s+Black\s+Rating\s+Type\s+ECO\s+End\s+Result",
            "\s*%%(\d+): %s\s+%s\s+%s\s+%s\s+\[([a-z ]{3})\s+(\d+)\s+(\d+)\]\s+(---|\?\?\?|\*\*\*|[A-Z]\d+)\s+%s\s+(\*|1/2-1/2|1-0|0-1)"
            % (names, ratings, names, ratings, reasons))

        self.connection.expect_line(self.__onAdjournedGameResigned,
                                    "You have resigned the game\.")

        self.connection.bm.connect("curGameEnded", self.__onCurGameEnded)

        self.queryAdjournments()
        self.queryHistory()
        self.queryJournal()

        # TODO: Connect to {Game 67 (MAd vs. Sandstrom) Game adjourned by mutual agreement} *
        # TODO: Connect to adjourned game as adjudicated

    def __onStoredResponseYES(self, matchlist):
        # Stored games for User:
        #     C Opponent     On Type          Str  M    ECO Date
        #  1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997
        #  2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009
        #  3: B cjavad        N [ wr  2   2] 31-31 W18  --- Wed Dec 23, 06:58 PST 2009
        self.connection.stored_owner = matchlist[0].groups()[0]
        adjournments = []
        for match in matchlist[2:]:
            our_color = match.groups()[0]
            opponent_name, opponent_online = match.groups()[1:3]
            game_type = match.groups()[3]
            minutes, gain = match.groups()[4:6]
            str_white, str_black = match.groups()[6:8]
            next_color = match.groups()[8]
            move_num = match.groups()[9]
            week, month, day, hour, minute, timezone, year = match.groups()[11:18]
            gametime = datetime.datetime(
                int(year), months.index(month) + 1, int(day), int(hour),
                int(minute))
            private = game_type[0] == "p"
            rated = game_type[2] == "r"
            gametype = GAME_TYPES_BY_SHORT_FICS_NAME[game_type[1]]
            our_color = our_color == "B" and BLACK or WHITE
            minutes = int(minutes)
            gain = int(gain)
            length = (int(move_num) - 1) * 2
            if next_color == "B":
                length += 1

            user = self.connection.players.get(self.connection.stored_owner)
            opponent = self.connection.players.get(opponent_name)
            wplayer, bplayer = (user, opponent) if our_color == WHITE else (opponent, user)
            game = FICSAdjournedGame(wplayer,
                                     bplayer,
                                     game_type=gametype,
                                     rated=rated,
                                     our_color=our_color,
                                     length=length,
                                     time=gametime,
                                     minutes=minutes,
                                     inc=gain,
                                     private=private)
            if game.opponent.adjournment is False:
                game.opponent.adjournment = True

            if game not in self.connection.games:
                game = self.connection.games.get(game, emit=False)
                self.emit("adjournedGameAdded", game)
            adjournments.append(game)

        self.emit("onAdjournmentsList", adjournments)

    __onStoredResponseYES.BLKCMD = BLKCMD_STORED

    def __onHistoryResponseYES(self, matchlist):
        # History for User:
        # Opponent      Type         ECO End Date
        # 66: - 1735 B    0 GuestHKZX     [ bu  3   0] B23 Res Sun Dec  6, 15:50 EST 2015
        # 67: - 1703 B    0 GuestQWML     [ lu  1   0] B07 Fla Sun Dec  6, 15:53 EST 2015
        history = []
        self.connection.history_owner = matchlist[0].groups()[0]
        for match in matchlist[2:]:
            # print(match.groups())
            history_no = match.groups()[0]
            result = match.groups()[1]
            owner_rating = match.groups()[2]
            owner_color = match.groups()[3]
            opp_rating = match.groups()[4]
            if result == "+":
                result = WHITEWON if owner_color == "W" else BLACKWON
            elif result == "-":
                result = WHITEWON if owner_color == "B" else BLACKWON
            else:
                result = DRAW
            opponent_name = match.groups()[5]
            if owner_color == "W":
                white = self.connection.history_owner
                black = opponent_name
                wrating = owner_rating
                brating = opp_rating
            else:
                white = opponent_name
                black = self.connection.history_owner
                brating = owner_rating
                wrating = opp_rating
            game_type = match.groups()[6]
            minutes, gain = match.groups()[7:9]
            reason = reasons_dict[match.groups()[10]]
            week, month, day, hour, minute, timezone, year = match.groups()[11:18]
            gametime = datetime.datetime(
                int(year), months.index(month) + 1, int(day), int(hour),
                int(minute))
            private = game_type[0] == "p"
            rated = game_type[2] == "r"
            gametype = GAME_TYPES_BY_SHORT_FICS_NAME[game_type[1]]
            owner_color = owner_color == "B" and BLACK or WHITE
            minutes = int(minutes)
            gain = int(gain)

            wplayer = self.connection.players.get(white)
            bplayer = self.connection.players.get(black)
            game = FICSHistoryGame(wplayer,
                                   bplayer,
                                   game_type=gametype,
                                   rated=rated,
                                   minutes=minutes,
                                   inc=gain,
                                   private=private,
                                   wrating=wrating,
                                   brating=brating,
                                   time=gametime,
                                   reason=reason,
                                   history_no=history_no,
                                   result=result)

            if game not in self.connection.games:
                game = self.connection.games.get(game, emit=False)
                self.emit("historyGameAdded", game)
            history.append(game)

        self.emit("onHistoryList", history)

    __onHistoryResponseYES.BLKCMD = BLKCMD_HISTORY

    def __onJournalResponseYES(self, matchlist):
        # Journal for User:
        #     White         Rating  Black         Rating  Type         ECO End Result
        # %01: tentacle      2291    larsa         2050    [ lr  1   2] D35 Rep 1/2-1/2
        # %02: larsa         2045    tentacle      2296    [ lr  1   2] A46 Res 0-1
        journal = []
        self.connection.journal_owner = matchlist[0].groups()[0]
        for match in matchlist[2:]:
            # print(match.groups())
            journal_no = match.groups()[0]
            result = match.groups()[10]
            result = reprResult.index(result)
            white = match.groups()[1]
            wrating = match.groups()[2]
            black = match.groups()[3]
            brating = match.groups()[4]
            game_type = match.groups()[5]
            minutes, gain = match.groups()[6:8]
            reason = reasons_dict[match.groups()[9]]
            private = game_type[0] == "p"
            rated = game_type[2] == "r"
            gametype = GAME_TYPES_BY_SHORT_FICS_NAME[game_type[1]]
            minutes = int(minutes)
            gain = int(gain)

            wplayer = self.connection.players.get(white)
            bplayer = self.connection.players.get(black)
            game = FICSJournalGame(wplayer,
                                   bplayer,
                                   game_type=gametype,
                                   rated=rated,
                                   minutes=minutes,
                                   inc=gain,
                                   private=private,
                                   wrating=wrating,
                                   brating=brating,
                                   reason=reason,
                                   journal_no=journal_no,
                                   result=result)

            if game not in self.connection.games:
                game = self.connection.games.get(game, emit=False)
                self.emit("journalGameAdded", game)
            journal.append(game)

        self.emit("onJournalList", journal)

    __onJournalResponseYES.BLKCMD = BLKCMD_JOURNAL

    def __onStoredResponseNO(self, match):
        self.connection.stored_owner = match.groups()[0]
        self.emit("onAdjournmentsList", [])

    __onStoredResponseNO.BLKCMD = BLKCMD_STORED

    def __onHistoryResponseNO(self, match):
        self.connection.history_owner = match.groups()[0]
        self.emit("onHistoryList", [])

    __onHistoryResponseNO.BLKCMD = BLKCMD_HISTORY

    def __onJournalResponseNO(self, match):
        self.connection.journal_owner = match.groups()[0]
        self.emit("onJournalList", [])

    __onJournalResponseNO.BLKCMD = BLKCMD_JOURNAL

    def __onAdjournedGameResigned(self, match):
        self.queryAdjournments()

    def __onCurGameEnded(self, bm, game):
        if game.result == ADJOURNED:
            self.queryAdjournments()
        elif game.result in (DRAW, WHITEWON, BLACKWON):
            self.queryHistory()

    def queryAdjournments(self, owner=None):
        if owner is None:
            self.connection.client.run_command("stored")
        else:
            self.connection.client.run_command("stored %s" % owner)

    def queryHistory(self, owner=None):
        if owner is None:
            self.connection.client.run_command("history")
        else:
            self.connection.client.run_command("history %s" % owner)

    def queryJournal(self, owner=None):
        if owner is None:
            self.connection.client.run_command("journal")
        else:
            self.connection.client.run_command("journal %s" % owner)

    def queryMoves(self, game):
        if isinstance(game, FICSHistoryGame):
            self.connection.client.run_command("smoves %s %s" % (
                self.connection.history_owner, game.history_no))
        elif isinstance(game, FICSJournalGame):
            self.connection.client.run_command("smoves %s %%%s" % (
                self.connection.journal_owner, game.journal_no))
        else:
            self.connection.client.run_command("smoves %s %s" % (
                self.connection.stored_owner, game.opponent.name))

    def examine(self, game):
        game.board = None
        self.connection.archived_examine = game
        if isinstance(game, FICSAdjournedGame):
            self.connection.client.run_command("examine %s %s" % (
                self.connection.stored_owner, game.opponent.name))
        elif isinstance(game, FICSHistoryGame):
            self.connection.client.run_command("examine %s %s" % (
                self.connection.history_owner, game.history_no))
        elif isinstance(game, FICSJournalGame):
            self.connection.client.run_command("examine %s %%%s" % (
                self.connection.journal_owner, game.journal_no))

    def challenge(self, playerName):
        self.connection.client.run_command("match %s" % playerName)

    def resign(self, game):
        """ This is (and draw and abort) are possible even when one's
            opponent is not logged on """
        if not game.opponent.adjournment:
            log.warning("AdjournManager.resign: no adjourned game vs %s" %
                        game.opponent)
            return
        log.info("AdjournManager.resign: resigning adjourned game=%s" % game)
        self.connection.client.run_command("resign %s" % game.opponent.name)

    def draw(self, game):
        if not game.opponent.adjournment:
            log.warning("AdjournManager.draw: no adjourned game vs %s" %
                        game.opponent)
            return
        log.info("AdjournManager.draw: offering sdraw for adjourned game=%s" %
                 game)
        self.connection.client.run_command("sdraw %s" % game.opponent.name)

    def abort(self, game):
        if not game.opponent.adjournment:
            log.warning("AdjournManager.abort: no adjourned game vs %s" %
                        game.opponent)
            return
        log.info("AdjournManager.abort: offering sabort for adjourned game=%s"
                 % game)
        self.connection.client.run_command("sabort %s" % game.opponent.name)

    def resume(self, game):
        if not game.opponent.adjournment:
            log.warning("AdjournManager.resume: no adjourned game vs %s" %
                        game.opponent)
            return
        log.info("AdjournManager.resume: offering resume for adjourned game=%s"
                 % game)
        self.connection.client.run_command("match %s" % game.opponent.name)

    # (a)  Users who have more than 15 stored games are restricted from starting new
    # games.  If this situation happens to you, review your stored games and see
    # which ones might be eligible for adjudication (see "help adjudication").
