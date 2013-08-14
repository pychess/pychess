import re
import datetime
from gobject import *

from BoardManager import BoardManager, moveListHeader1Str, names, months, dates
from pychess.ic import *
from pychess.ic.block_codes import BLKCMD_SMOVES
from pychess.ic.FICSObjects import FICSAdjournedGame, FICSPlayer
from pychess.Utils.const import *
from pychess.System.Log import log

class AdjournManager (GObject):
    
    __gsignals__ = {
        'adjournedGameAdded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'onAdjournmentsList' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'adjournedGamePreview' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect_line (self.__onStoredResponseNO,
                                     "%s has no adjourned games\." %
                                     self.connection.username)
        
        self.connection.expect_fromto (self.__onSmovesResponse,
                                       moveListHeader1Str,
#                                       "\s*{((?:Game courtesyadjourned by (Black|White))|(?:Still in progress)|(?:Game adjourned by mutual agreement)|(?:(White|Black) lost connection; game adjourned)|(?:Game adjourned by ((?:server shutdown)|(?:adjudication)|(?:simul holder))))} \*")
                                        "\s*{.*(?:(?:[Gg]ame.*adjourned)|(?:Still in progress)|(?:Game drawn.*)|(?:White.*)|(?:Black.*)).*}\s*(?:(?:1/2-1/2)|(?:1-0)|(?:0-1))?\s*")


        self.connection.expect_fromplus(self.__onStoredResponseYES,
                                        "\s*C Opponent\s+On Type\s+Str\s+M\s+ECO\s+Date",
                                        "\s*\d+: (B|W) %s\s+(Y|N) \[([a-z ]{3})\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(---|\?\?\?|[A-Z]\d+)\s+%s" %
                                        (names, dates)) 
        
        self.connection.expect_line (self.__onAdjournedGameResigned,
                                     "You have resigned the game\.")

        self.connection.bm.connect("curGameEnded", self.__onCurGameEnded)
        
        self.queryAdjournments()
        
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
                min=minutes, inc=gain, private=private)
            if game.opponent.adjournment != True:
                game.opponent.adjournment = True
            
            if game not in self.connection.games:
                game = self.connection.games.get(game, emit=False)
                self.emit("adjournedGameAdded", game)
            adjournments.append(game)
            
        self.emit("onAdjournmentsList", adjournments)
        
    def __onStoredResponseNO (self, match):
        self.emit("onAdjournmentsList", [])
    
    def __onSmovesResponse (self, matchlist):
        game = self.connection.bm.parseGame(matchlist, FICSAdjournedGame,
                                            in_progress=False)
        if game is None: return
        self.emit("adjournedGamePreview", game)
    __onSmovesResponse.BLKCMD = BLKCMD_SMOVES
    
    def __onAdjournedGameResigned (self, match):
        self.queryAdjournments()

    def __onCurGameEnded (self, bm, game):
        if game.result == ADJOURNED:
            self.queryAdjournments()
    
    def queryAdjournments (self):
        self.connection.client.run_command("stored")
    
    def queryMoves (self, game):
        self.connection.client.run_command("smoves %s" % game.opponent.name)
    
    def challenge (self, playerName):
        self.connection.client.run_command("match %s" % playerName)
    
    def resign (self, game):
        """ This is (and draw and abort) are possible even when one's
            opponent is not logged on """
        if not game.opponent.adjournment:
            log.warn("AdjournManager.resign: no adjourned game vs %s\n" % game.opponent)
            return
        log.info("AdjournManager.resign: resigning adjourned game=%s\n" % game)
        self.connection.client.run_command("resign %s" % game.opponent.name)
    
    def draw (self, game):
        if not game.opponent.adjournment:
            log.warn("AdjournManager.draw: no adjourned game vs %s\n" % game.opponent)
            return
        log.info("AdjournManager.draw: offering sdraw for adjourned game=%s\n" % game)
        self.connection.client.run_command("sdraw %s" % game.opponent.name)
    
    def abort (self, game):
        if not game.opponent.adjournment:
            log.warn("AdjournManager.abort: no adjourned game vs %s\n" % game.opponent)
            return
        log.info("AdjournManager.abort: offering sabort for adjourned game=%s\n" % game)
        self.connection.client.run_command("sabort %s" % game.opponent.name)
    
    def resume (self, game):
        if not game.opponent.adjournment:
            log.warn("AdjournManager.resume: no adjourned game vs %s\n" % game.opponent)
            return
        log.info("AdjournManager.resume: offering resume for adjourned game=%s\n" % game)
        self.connection.client.run_command("match %s" % game.opponent.name)
    
#(a)  Users who have more than 15 stored games are restricted from starting new
#games.  If this situation happens to you, review your stored games and see
#which ones might be eligible for adjudication (see "help adjudication").
