from __future__ import absolute_import
import re
import datetime

from gi.repository import GObject

from .BoardManager import BoardManager, moveListHeader1Str, names, months, dates
from pychess.ic import *
from pychess.ic.FICSObjects import FICSAdjournedGame, FICSHistoryGame, FICSPlayer
from pychess.Utils.const import *
from pychess.System.Log import log

reasons_dict = {"Adj": WON_ADJUDICATION,
                "Agr": DRAW_AGREE,
                "Dis": WON_DISCONNECTION,
                "Fla": WON_CALLFLAG,
                "Mat": WON_MATE,
                "NM": DRAW_INSUFFICIENT,
                "Rep": DRAW_REPITITION,
                "Res": WON_RESIGN,
                "TM": DRAW_BLACKINSUFFICIENTANDWHITETIME, #DRAW_WHITEINSUFFICIENTANDBLACKTIME
                "WLM": WON_NOMATERIAL,
                "WNM": WON_NOMATERIAL,
                "50": DRAW_50MOVES}

reasons = "(%s)" % "|".join(reasons_dict.keys())

class AdjournManager (GObject.GObject):
    
    __gsignals__ = {
        'adjournedGameAdded' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'onAdjournmentsList' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'historyGameAdded' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'onHistoryList' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect_line (self.__onAdjournedResponseNO,
                                     "%s has no adjourned games\." %
                                     self.connection.username)

        self.connection.expect_line (self.__onHistoryResponseNO,
                                     "%s has no history games\." %
                                     self.connection.username)

        self.connection.expect_fromplus(self.__onStoredResponseYES,
                                        "\s*C Opponent\s+On Type\s+Str\s+M\s+ECO\s+Date",
                                        "\s*\d+: (B|W) %s\s+(Y|N) \[([a-z ]{3})\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(---|\?\?\?|\*\*\*|[A-Z]\d+)\s+%s" %
                                        (names, dates)) 

        self.connection.expect_fromplus(self.__onHistoryResponseYES,
                                        "\s*Opponent\s+Type\s+ECO\s+End\s+Date",
                                        "\s*(\d+): (-|\+|=) \d+\s+(W|B)\s+\d+ %s\s+\[([a-z ]{3})\s+(\d+)\s+(\d+)\]\s+(---|\?\?\?|\*\*\*|[A-Z]\d+)\s+%s\s+%s" %
                                        (names, reasons, dates)) 
        
        self.connection.expect_line (self.__onAdjournedGameResigned,
                                     "You have resigned the game\.")

        self.connection.bm.connect("curGameEnded", self.__onCurGameEnded)
        
        self.queryAdjournments()
        self.queryHistory()
        
        #TODO: Connect to {Game 67 (MAd vs. Sandstrom) Game adjourned by mutual agreement} *
        #TODO: Connect to adjourned game as adjudicated
    
    def __onStoredResponseYES (self, matchlist):
        #Stored games of User: 
        #     C Opponent     On Type          Str  M    ECO Date
        #  1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997
        #  2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009
        #  3: B cjavad        N [ wr  2   2] 31-31 W18  --- Wed Dec 23, 06:58 PST 2009
        adjournments = []
        for match in matchlist[1:]:
            our_color = match.groups()[0]
            opponent_name, opponent_online = match.groups()[1:3]
            game_type = match.groups()[3]
            minutes, gain = match.groups()[4:6]
            str_white, str_black = match.groups()[6:8]
            next_color = match.groups()[8]
            move_num = match.groups()[9]
            eco = match.groups()[10]
            week, month, day, hour, minute, timezone, year = match.groups()[11:18]
            gametime = datetime.datetime(int(year), months.index(month)+1, int(day),
                                         int(hour), int(minute))
            private = game_type[0] == "p"
            rated = game_type[2] == "r"
            gametype = GAME_TYPES_BY_SHORT_FICS_NAME[game_type[1]]
            our_color = our_color == "B" and BLACK or WHITE
            minutes = int(minutes)
            gain = int(gain)
            length = (int(move_num)-1)*2
            if next_color == "B": length += 1
            
            user = self.connection.players.get(
                FICSPlayer(self.connection.getUsername()))
            opponent = FICSPlayer(opponent_name, status=IC_STATUS_OFFLINE)
            opponent = self.connection.players.get(opponent)
            wplayer, bplayer = (user, opponent) if our_color == WHITE \
                                                else (opponent, user)
            game = FICSAdjournedGame(wplayer, bplayer, game_type=gametype,
                rated=rated, our_color=our_color, length=length, time=gametime,
                minutes=minutes, inc=gain, private=private)
            if game.opponent.adjournment != True:
                game.opponent.adjournment = True
            
            if game not in self.connection.games:
                game = self.connection.games.get(game, emit=False)
                self.emit("adjournedGameAdded", game)
            adjournments.append(game)
            
        self.emit("onAdjournmentsList", adjournments)
    __onStoredResponseYES.BLKCMD = BLKCMD_STORED

    def __onHistoryResponseYES (self, matchlist):
        #History for user:
        #Opponent      Type         ECO End Date
        #66: - 1735 B    0 GuestHKZX     [ bu  3   0] B23 Res Sun Dec  6, 15:50 EST 2015
        #67: - 1703 B    0 GuestQWML     [ lu  1   0] B07 Fla Sun Dec  6, 15:53 EST 2015
        history = []
        for match in matchlist[1:]:
            #print(match.groups())
            history_no = match.groups()[0]
            result = match.groups()[1]
            our_color = match.groups()[2]
            if result == "+":
                result = WHITEWON if our_color == "W" else BLACKWON
            elif result == "-":
                result = WHITEWON if our_color == "B" else BLACKWON
            else:
                result = DRAW
            opponent_name = match.groups()[3]
            game_type = match.groups()[4]
            minutes, gain = match.groups()[5:7]
            eco = match.groups()[7]
            reason = reasons_dict[match.groups()[8]]
            week, month, day, hour, minute, timezone, year = match.groups()[9:16]
            gametime = datetime.datetime(int(year), months.index(month)+1, int(day),
                                         int(hour), int(minute))
            private = game_type[0] == "p"
            rated = game_type[2] == "r"
            gametype = GAME_TYPES_BY_SHORT_FICS_NAME[game_type[1]]
            our_color = our_color == "B" and BLACK or WHITE
            minutes = int(minutes)
            gain = int(gain)
            
            user = self.connection.players.get(
                FICSPlayer(self.connection.getUsername()))
            opponent = FICSPlayer(opponent_name, status=IC_STATUS_OFFLINE)
            opponent = self.connection.players.get(opponent)
            wplayer, bplayer = (user, opponent) if our_color == WHITE \
                                                else (opponent, user)
            game = FICSHistoryGame(wplayer, bplayer, game_type=gametype,
                rated=rated, minutes=minutes, inc=gain, private=private,
                our_color=our_color, time=gametime, reason=reason,
                history_no=history_no, result=result)
            
            if game not in self.connection.games:
                game = self.connection.games.get(game, emit=False)
                self.emit("historyGameAdded", game)
            history.append(game)
            
        self.emit("onHistoryList", history)
    __onHistoryResponseYES.BLKCMD = BLKCMD_HISTORY
        
    def __onAdjournedResponseNO (self, match):
        self.emit("onAdjournmentsList", [])
    __onAdjournedResponseNO.BLKCMD = BLKCMD_STORED

    def __onHistoryResponseNO (self, match):
        self.emit("onHistoryList", [])
    __onHistoryResponseNO.BLKCMD = BLKCMD_HISTORY

    def __onAdjournedGameResigned (self, match):
        self.queryAdjournments()

    def __onCurGameEnded (self, bm, game):
        if game.result == ADJOURNED:
            self.queryAdjournments()
        elif game.result in (DRAW, WHITEWON, BLACKWON):
            self.queryHistory()
    
    def queryAdjournments (self):
        self.connection.client.run_command("stored")
    
    def queryHistory (self):
        self.connection.client.run_command("history")

    def queryMoves (self, game):
        if isinstance(game, FICSHistoryGame):
            self.connection.client.run_command("smoves %s %s" % (self.connection.username, game.history_no))
        else:
            self.connection.client.run_command("smoves %s" % game.opponent.name)

    def examine (self, game):
        game.board = None
        self.connection.examined_game = game
        if isinstance(game, FICSAdjournedGame):
            self.connection.client.run_command("examine %s" % game.opponent.name)
        else:
            self.connection.client.run_command("examine %s %s" % (self.connection.username, game.history_no))
    
    def challenge (self, playerName):
        self.connection.client.run_command("match %s" % playerName)
    
    def resign (self, game):
        """ This is (and draw and abort) are possible even when one's
            opponent is not logged on """
        if not game.opponent.adjournment:
            log.warning("AdjournManager.resign: no adjourned game vs %s" % game.opponent)
            return
        log.info("AdjournManager.resign: resigning adjourned game=%s" % game)
        self.connection.client.run_command("resign %s" % game.opponent.name)
    
    def draw (self, game):
        if not game.opponent.adjournment:
            log.warning("AdjournManager.draw: no adjourned game vs %s" % game.opponent)
            return
        log.info("AdjournManager.draw: offering sdraw for adjourned game=%s" % game)
        self.connection.client.run_command("sdraw %s" % game.opponent.name)
    
    def abort (self, game):
        if not game.opponent.adjournment:
            log.warning("AdjournManager.abort: no adjourned game vs %s" % game.opponent)
            return
        log.info("AdjournManager.abort: offering sabort for adjourned game=%s" % game)
        self.connection.client.run_command("sabort %s" % game.opponent.name)
    
    def resume (self, game):
        if not game.opponent.adjournment:
            log.warning("AdjournManager.resume: no adjourned game vs %s" % game.opponent)
            return
        log.info("AdjournManager.resume: offering resume for adjourned game=%s" % game)
        self.connection.client.run_command("match %s" % game.opponent.name)
    
#(a)  Users who have more than 15 stored games are restricted from starting new
#games.  If this situation happens to you, review your stored games and see
#which ones might be eligible for adjudication (see "help adjudication").
