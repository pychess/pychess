import re
import datetime
from gobject import *

from BoardManager import BoardManager, moveListHeader1Str, names, months, dates
from pychess.Utils.const import *
from pychess.System.Log import log

class AdjournManager (GObject):
    
    __gsignals__ = {
        'onAdjournmentsList' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'onGamePreview' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
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
                                        "\s*{.*(?:(?:[Gg]ame.*adjourned)|(?:Still in progress)).*}\s*\*")
        
        self.connection.expect_fromplus(self.__onStoredResponseYES,
                                        "\s*C Opponent\s+On Type\s+Str\s+M\s+ECO\s+Date",
                                        "\s*\d+: (B|W) %s\s+(Y|N) \[([a-z ]{3})\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(---|\?\?\?|[A-Z]\d+)\s+%s" %
                                        (names, dates)) 
        
        self.connection.expect_line (self.__onAdjournedGameResigned,
                                     "You have resigned the game\.")
        
        self.adjournments = []
        
        #TODO: Connect to {Game 67 (MAd vs. Sandstrom) Game adjourned by mutual agreement} *
        #TODO: Connect to adjourned game as adjudicated
        #TODO: connect to "Dildo, with whom you have an adjourned game, has logged on"
    
    def __onStoredResponseYES (self, matchlist):
        #Stored games of User: 
        #     C Opponent     On Type          Str  M    ECO Date
        #  1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997
        #  2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009
        #  3: B cjavad        N [ wr  2   2] 31-31 W18  --- Wed Dec 23, 06:58 PST 2009
        
        del self.adjournments[:]
        
        for match in matchlist[1:]:
            our_color = match.groups()[0]
            opponent, opponent_online = match.groups()[1:3]
            game_type = match.groups()[3]
            minutes, gain = match.groups()[4:6]
            str_white, str_black = match.groups()[6:8]
            next_color = match.groups()[8]
            move_num = match.groups()[9]
            eco = match.groups()[10]
            week, month, day, hour, minute, timezone, year = match.groups()[11:18]
            gametime = datetime.datetime(int(year), months.index(month)+1, int(day),
                                         int(hour), int(minute)).strftime("%x %H:%M")
            
            private = game_type[0] == "p"
            rated = game_type[2] == "r"
            
            our_color = our_color == "B" and BLACK or WHITE
            minutes = int(minutes)
            gain = int(gain)
            length = (int(move_num)-1)*2
            if next_color == "B": length += 1
            opponent_online = opponent_online == "Y"
            
            self.adjournments.append({"color":our_color, "opponent":opponent,
                                      "online":opponent_online, "length":length,
                                      "time":gametime, "minutes":minutes, "gain":gain})
            
            #print >> self.connection, "smoves %s" % opponent
        
        self.emit("onAdjournmentsList", self.adjournments)
        
    def __onStoredResponseNO (self, match):
        self.emit("onAdjournmentsList", [])
    
    def __onSmovesResponse (self, matchlist):
        game = BoardManager.parseGame(matchlist, in_progress=False)
        if game is None: return
        self.emit("onGamePreview", game)
    
    def __onAdjournedGameResigned (self, match):
        self.queryAdjournments()
    
    def queryAdjournments (self):
        print >> self.connection.client, "stored"
    
    def queryMoves (self, opponent):
        print >> self.connection.client, "smoves %s" % opponent
    
    def challenge (self, playerName):
        print >> self.connection.client, "match %s" % playerName
    
    def _weHaveAdjournedGameWith (self, playername):
        for adjournment in self.adjournments:
            if playername == adjournment["opponent"]:
                return True
        return False
    
    def resign (self, playername):
        if not self._weHaveAdjournedGameWith(playername):
            log.warn("AdjournManager.resign: no stored game vs %s\n" % playername)
            return
        log.log("AdjournManager.resign: resigning stored game vs %s\n" % playername)
        print >> self.connection.client, "resign %s" % playername
    
    def draw (self, playername):
        if not self._weHaveAdjournedGameWith(playername):
            log.warn("AdjournManager.draw: no stored game vs %s\n" % playername)
            return
        log.log("AdjournManager.draw: offering %s draw for stored game\n" % playername)
        print >> self.connection.client, "sdraw %s" % playername
    
    def abort (self, playername):
        if not self._weHaveAdjournedGameWith(playername):
            log.warn("AdjournManager.abort: no stored game vs %s\n" % playername)
            return
        log.log("AdjournManager.abort: offering %s abort for stored game\n" % playername)
        print >> self.connection.client, "sabort %s" % playername
    
    def resume (self, playername):
        if not self._weHaveAdjournedGameWith(playername):
            log.warn("AdjournManager.resume: no stored game vs %s\n" % playername)
            return
        log.log("AdjournManager.resume: offering %s resume for stored game\n" % playername)
        print >> self.connection.client, "match %s" % playername
    
#(a)  Users who have more than 15 stored games are restricted from starting new
#games.  If this situation happens to you, review your stored games and see
#which ones might be eligible for adjudication (see "help adjudication").
#
#(b)  It is possible to resign one of your stored games, even when your
#opponent is not logged on (see "help resign").

