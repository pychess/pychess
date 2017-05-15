
import datetime

from gi.repository import GObject

from pychess.ic import GAME_TYPES_BY_FICS_NAME
from pychess.ic.icc import DG_GAMELIST_BEGIN, DG_GAMELIST_ITEM, DG_RATING_TYPE_KEY
from pychess.ic.managers.AdjournManager import AdjournManager
from pychess.ic.FICSObjects import FICSAdjournedGame, FICSHistoryGame, FICSJournalGame
from pychess.Utils.const import WON_ADJUDICATION, DRAW_AGREE, WON_DISCONNECTION, WON_CALLFLAG, \
    WON_MATE, DRAW_INSUFFICIENT, DRAW_REPITITION, WON_RESIGN, DRAW_STALEMATE, \
    DRAW_BLACKINSUFFICIENTANDWHITETIME, UNKNOWN_REASON, DRAW_50MOVES, WHITEWON, DRAW, \
    BLACKWON, ADJOURNED, DRAW_CALLFLAG, DRAW_ADJUDICATION, ABORTED, WHITE, BLACK

won_reasons_dict = {
    "0": WON_RESIGN,
    "1": WON_MATE,
    "2": WON_CALLFLAG,
    "3": WON_ADJUDICATION,
    "4": WON_DISCONNECTION,
    "5": WON_DISCONNECTION,
    "6": WON_DISCONNECTION,
    "7": WON_RESIGN,
    "8": WON_MATE,
    "9": WON_CALLFLAG,
    "10": WON_DISCONNECTION,
    "11": WON_DISCONNECTION,
    "12": WON_DISCONNECTION,
    "13": WON_ADJUDICATION,
}

draw_reasons_dict = {
    "0": DRAW_AGREE,
    "1": DRAW_STALEMATE,
    "2": DRAW_REPITITION,
    "3": DRAW_50MOVES,
    "4": DRAW_BLACKINSUFFICIENTANDWHITETIME,  # DRAW_WHITEINSUFFICIENTANDBLACKTIME
    "5": DRAW_INSUFFICIENT,
    "6": DRAW_CALLFLAG,
    "7": DRAW_ADJUDICATION,
    "8": DRAW_AGREE,
    "9": DRAW_CALLFLAG,
    "10": DRAW_ADJUDICATION,
}


class ICCAdjournManager(AdjournManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.RATING_TYPES = {}

        self.connection.expect_dg_line(DG_RATING_TYPE_KEY, self.on_icc_rating_type_key)
        self.connection.expect_dg_line(DG_GAMELIST_BEGIN, self.on_icc_gamelist_begin)
        self.connection.expect_dg_line(DG_GAMELIST_ITEM, self.on_icc_gamelist_item)

        self.connection.client.run_command("set-2 %s 1" % DG_RATING_TYPE_KEY)
        self.connection.client.run_command("set-2 %s 1" % DG_GAMELIST_BEGIN)
        self.connection.client.run_command("set-2 %s 1" % DG_GAMELIST_ITEM)

        self.queryAdjournments()
        self.queryHistory()
        self.queryJournal()

        self.connection.query_game = None

    def on_icc_rating_type_key(self, data):
        key, value = data.split()
        self.RATING_TYPES[key] = value.lower()

    def on_icc_gamelist_begin(self, data):
        # command {parameters} nhits first last {summary}
        # command is one of search, history, liblist, or stored
        # history {gbtami} 20 1 20 {Recent games of gbtami}
        command, rest = data.split(" ", 1)
        params, rest = rest.split("}", 1)
        name = params[1:]

        # force clean up old gamelists
        if self.connection.history_owner != name:
            self.emit("onAdjournmentsList", [])
            self.emit("onHistoryList", [])
            self.emit("onJournalList", [])

        if command == "stored":
            self.connection.stored_owner = name
        elif command == "history":
            self.connection.history_owner = name
        elif command == "liblist":
            self.connection.journal_owner = name

        self.gamelist_command = command

    def on_icc_gamelist_item(self, data):
        # index id event date time white-name white-rating black-name black-rating rated rating-type
        # wild init-time-W inc-W init-time-B inc-B eco status color mode {note} here
        # status: 0=win 1=draw 2=adjourned 3=abort
        # rating_type: 0=wild, 1=blitz, 2=standard, bullet, 4=bughouse see DG_RATING_TYPE_KEY
        # 99 1731753309 ? 2016.12.08 15:07:53 gbtami 1538 konechno 1644 1 11 0 3 0 3 0 A00 0 1 1 {} 0
        # 98 1731751094 ? 2016.12.08 14:34:37 gbtami 1550 espilva 1484 1 11 0 3 0 3 0 A00 1 0 5 {} 0
        idx, gid, event, date, time, wname, wrating, bname, brating, rated, rating_type, \
            wild, wtime, winc, btime, binc, eco, status, color, mode, rest = data.split(" ", 20)

        if status == "0":
            result = WHITEWON if color == "0" else BLACKWON
        elif status == "1":
            result = DRAW
        elif status == "2":
            result = ADJOURNED
        else:
            result = ABORTED

        white = wname
        black = bname
        wrating = wrating
        brating = brating

        if status == "0":
            reason = won_reasons_dict[mode]
        elif status == "1":
            reason = draw_reasons_dict[mode]
        else:
            reason = UNKNOWN_REASON

        year, month, day = date.split(".")
        hour, minute, sec = time.split(":")
        gametime = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(sec))
        rated = rated == "1"
        fics_name = self.RATING_TYPES[rating_type]
        gametype = GAME_TYPES_BY_FICS_NAME[fics_name]

        minutes = int(wtime)
        gain = int(winc)

        wplayer = self.connection.players.get(white)
        bplayer = self.connection.players.get(black)

        if self.gamelist_command == "stored":
            game = FICSAdjournedGame(
                wplayer,
                bplayer,
                game_type=gametype,
                rated=rated,
                our_color=WHITE if wname == self.connection.username else BLACK,
                minutes=minutes,
                inc=gain)

            if game.opponent.adjournment is False:
                game.opponent.adjournment = True

        elif self.gamelist_command == "history":
            game = FICSHistoryGame(
                wplayer,
                bplayer,
                game_type=gametype,
                rated=rated,
                minutes=minutes,
                inc=gain,
                wrating=wrating,
                brating=brating,
                time=gametime,
                reason=reason,
                history_no=idx,
                result=result)

        elif self.gamelist_command == "liblist":
            game = FICSJournalGame(
                wplayer,
                bplayer,
                game_type=gametype,
                rated=rated,
                minutes=minutes,
                inc=gain,
                wrating=wrating,
                brating=brating,
                time=gametime,
                reason=reason,
                journal_no=idx,
                result=result)

        if game not in self.connection.games:
            game = self.connection.games.get(game, emit=False)
            if self.gamelist_command == "stored":
                self.emit("adjournedGameAdded", game)
            elif self.gamelist_command == "history":
                self.emit("historyGameAdded", game)
            elif self.gamelist_command == "liblist":
                self.emit("journalGameAdded", game)

    def queryJournal(self, owner=None):
        if owner is None:
            self.connection.client.run_command("liblist")
        else:
            self.connection.client.run_command("liblist %s" % owner)

    def queryMoves(self, game):
        self.connection.query_game = game
        if isinstance(game, FICSHistoryGame):
            self.connection.client.run_command("spgn %s %s" % (
                self.connection.history_owner, game.history_no))
        elif isinstance(game, FICSJournalGame):
            self.connection.client.run_command("spgn %s %%%s" % (
                self.connection.journal_owner, game.journal_no))
        else:
            self.connection.client.run_command("spgn %s %s" % (
                self.connection.stored_owner, game.opponent.name))
