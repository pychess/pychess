
import re
import datetime

from gobject import *

from pychess.Utils.const import *

names = "\w+(?:\([A-Z\*]+\))*"
weekdays = ("Mon","Tue","Wed","Thu","Fri","Sat","Sun")
months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

sanmove = "([a-hxOoKQRBN0-8+#=-]{2,7})"
moveListMoves = re.compile("(\d+)\. +%s +\(\d+:\d+\.\d+\) *(?:%s +\(\d+:\d+\.\d+\))?" %
        (sanmove, sanmove))

class AdjournManager (GObject):
    
    __gsignals__ = {
        'onAdjournmentsList' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'onGamePreview' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,int,int,str,str)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect_line (self.__onStoredResponseNO,
                                     "%s has no adjourned games\." %
                                     self.connection.username)
        
        self.connection.expect_fromto (self.__onSmovesResponse,
                                       "Move\s+(%s)\s+(%s)" % (names,names),
                                       "{(.*[gG]ame adjourned.*)} \*")
        
        self.connection.expect_fromplus(self.__onStoredResponseYES,
                                        "\s*C Opponent\s+On Type\s+Str\s+M\s+ECO\s+Date",
                                        "\s*\d+: (B|W) (%s)\s+(Y|N) \[([a-z ]{3})\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(\?\?\?|[A-Z]\d+)\s+(%s)\s+(%s)\s+(\d+),\s+(\d+):(\d+)\s+([A-Z\?]+)\s+(\d{4})" %
                                        (names, "|".join(weekdays), "|".join(months))) 
        
        self.adjournments = []
        
        #TODO: Connect to {Game 67 (MAd vs. Sandstrom) Game adjourned by mutual agreement} *
        #TODO: Connect to adjourned game as adjudicated
        #TODO: Connect to player has resigned ajourned game
    
    def __onStoredResponseYES (self, matchlist):
        #Stored games of User: 
        #     C Opponent     On Type          Str  M    ECO Date
        #  1: W TheDane       N [ br  2  12]  0-0  B2   ??? Sun Nov 23,  6:14 CST 1997
        #  2: W PyChess       Y [psu  2  12] 39-39 W3   C20 Sun Jan 11, 17:40 ??? 2009
        
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
        #Move  PyChess            selman             
        #----  ----------------   ----------------
        #  1.  e4      (0:00.000)     c5      (0:00.000)  
        #  2.  Nf3     (0:00.000) 
        #      {White lost connection; game adjourned} *
        
        white_name, black_name = matchlist[0].groups()
        end_reason = matchlist[-1].groups()
        
        pgnHead = [
            ("Event", "Ficsgame"),
            ("Site", "Internet"),
            ("White", white_name),
            ("Black", black_name)]
        pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n"
        
        pgnlist = []
        for line in matchlist[2:-1]:
            moveno, wmove, bmove = moveListMoves.match(line).groups()
            pgnlist.append(moveno+".")
            pgnlist.append(wmove)
            if bmove:
                pgnlist.append(bmove)
        pgnlist.append("*")
        pgn += " ".join(pgnlist)
        
        if white_name.lower() == self.connection.username.lower():
            opponent = black_name
        else: opponent = white_name
        for adjournment in self.adjournments:
            if adjournment["opponent"].lower() == opponent.lower():
                 secs = adjournment["minutes"]*60
                 gain = adjournment["gain"]
                 break
        else:
            secs = 60
            gain = 0
        
        self.emit("onGamePreview", pgn, secs, gain, white_name, black_name)
    
    def queryAdjournments (self):
        print >> self.connection.client, "stored"
    
    def queryMoves (self, opponent):
        print >> self.connection.client, "smoves %s" % opponent
    
    def challenge (self, playerName):
        print >> self.connection.client, "match %s" % playerName

#(a)  Users who have more than 15 stored games are restricted from starting new
#games.  If this situation happens to you, review your stored games and see
#which ones might be eligible for adjudication (see "help adjudication").
#
#(b)  It is possible to resign one of your stored games, even when your
#opponent is not logged on (see "help resign").

