
from gobject import *
import re
from pychess.Utils import const

types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\- ]{1,4})"
names = "(\w+)(?:\((\w+)\))?"
mf = "(?:([mf]{1,2})\s?)?"
ratingSplit = re.compile("P|E| ")

#0x1 - unregistered
#0x2 - computer
#0x4 - GM
#0x8 - IM
#0x10 - FM
#0x20 - WGM
#0x40 - WIM
#0x80 - WFM

typedic = {"b":_("Blitz"), "s":_("Standard"), "l":_("Lightning")}

from pychess.Utils.const import WHITE

class GameListManager (GObject):
    
    __gsignals__ = {
        'addSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'clearSeeks' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        
        'addGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,int,str)),
        
        'addPlayer' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removePlayer' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        
        'addAdjourn' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.players = set()
        
        
        self.connection.expect_line (self.on_seek_clear, "<sc>")
        self.connection.expect_line (self.on_seek_add, "<s> (.+)")
        self.connection.expect_line (self.on_seek_remove, "<sr> ([\d ]+)")
        
        self.connection.expect_line (self.on_game_list,
                "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(s|b|l)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d+):(\d+)\s*-\s*(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)" % (ratings, ratings))
        self.connection.expect_line (self.on_game_add,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) (?:Creating|Continuing) (u?n?rated) (\S+) match\.\}$")
        self.connection.expect_line (self.on_game_remove,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) ([A-Za-z']+) (.+)\} (\*|1/2-1/2|1-0|0-1)$")
        
        self.connection.expect_line (self.on_player_list,
                "([A-Za-z]+)[\^~:\#. &](\\d{2})((?:\\d{1,4}[P E])+)")
        self.connection.expect_line (self.on_player_remove,
                "%s is no longer available for matches." % names)
        self.connection.expect_fromto (self.on_player_add,
                "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)" % 
                (names, ratings, ratings, ratings, ratings, ratings),
                "is now available for matches.")
        
        self.connection.expect_line (self.on_adjourn_add,
                "\d+: (W|B) (\w+)\s+(N|Y) \[ (\w+)\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(\w+)\s+(.*)")
        
        self.connection.expect_fromto (self.playBoardCreated,
                "Creating: %s %s %s %s %s %s (\d+) (\d+)" %
                    (names, ratings, names, ratings, rated, types),
                "{Game (\d+)\s.*")
        
        
        self.connection.lvm.setVariable("seekinfo", True)
        self.connection.lvm.setVariable("seekremove", True)
        #self.connection.lvm.setVariable("seek", False)
        
        self.connection.lvm.setVariable("gin", True)
        self.connection.lvm.setVariable("allresults", True)
        print >> self.connection.client, "games /sbl"
        
        print >> self.connection.client, "who Isbla"
        #self.connection.lvm.setVariable("availmax", True)
        #self.connection.lvm.setVariable("availmin", True)
        self.connection.lvm.setVariable("availinfo", True)
        
        print >> self.connection.client, "stored"
    
    ###
    
    def seek (self, startmin, incsec, rated, ratings=(0,9999), color=None):
        rchar = rated and "r" or "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        print >> self.connection.client, "seek %d %d %s %s %d-%d" % \
                (startmin, incsec, rchar, cchar, ratings[0], ratings[1])
    
    def challenge (self, playerName, startmin, incsec, rated, color=None):
        rchar = rated and "r" or "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        print >> self.connection.client, "match %s %d %d %s %s" % \
                (playerName, startmin, incsec, rchar, cchar)
    
    def refreshSeeks (self):
        print >> self.connection.client, "iset seekinfo 1"
    
    def getPlayerlist (self):
        return self.players
    
    ###
    
    def on_seek_add (self, match):
        parts = match.groups()[0].split(" ")
        # The <s> message looks like:
        # <s> index w=name_from ti=titles rt=rating t=time i=increment
        #     r=rated('r')/unrated('u') tp=type c=color
        #     rr=rating_range(lower-upper) a=automatic?('t'/'f')
        #     f=formula_checked('t'/f')
        
        seek = {"gameno": parts[0]}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            seek[key] = value
            if key == "tp":
                if not value in ("standard", "lightning", "blitz"):
                    return
                seek[key] = typedic[value[0]]
            elif key == "rr":
                seek["rmin"], seek["rmax"] = value.split("-")
            elif key == "ti":
                seek["cp"] = int(value) & 2 # 0x2 - computer
            elif key == "rt":
                if value[-1] in (" ", "P", "E"):
                    seek[key] = value[:-1]
            elif key == "a":
                seek["manual"] = value == "f" # Must be accepted manually
        
        self.emit("addSeek", seek)
    
    def on_seek_clear (self, *args):
        self.emit("clearSeeks")
    
    def on_seek_remove (self, match):
        for key in match.groups()[0].split(" "):
            if not key: continue
            self.emit("removeSeek", key)
    
    ###
    
    def on_game_list (self, match):
        gameno, wr, wn, br, bn, private, type, rated, min, inc, wmin, wsec, bmin, bsec, wmat, bmat, color, movno = match.groups()
        
        game = {"gameno":gameno, "wn":wn, "bn":bn, "type":typedic[type]}
        self.emit("addGame", game)
    
    def on_game_add (self, match):
        gameno, wn, bn, rated, type = match.groups()
        if not type in ("standard", "blitz", "lightning"):
            return
        type = typedic[type[0]]
        self.emit("addGame", {"gameno":gameno, "wn":wn, "bn":bn, "type":type})
    
    def on_game_remove (self, match):
        gameno, wn, bn, person, comment, result = match.groups()
        result = const.reprResult.index(result)
        self.emit("removeGame", gameno, result, comment)
    
    ###
    
    def on_player_list (self, match):
        handle, title, ratings = match.groups()
        mean = sum(int(r) for r in ratingSplit.split(ratings)[:-1] if int(r))/3.
        self.emit("addPlayer", {"name": handle, "rating": mean, "title":int(title,16)})
        self.players.add(handle)
    
    def on_player_remove (self, match):
        name, title = match.groups()
        self.emit("removePlayer", name)
        if name in self.players:
            self.players.remove(name)
    
    def on_player_add (self, matches):
        name, title, blitz, std, wild, light, bug = matches[0].groups()
        ratings = (blitz, std, wild, light, bug)
        mean = sum(int(r) for r in ratings if r.strip().isdigit())/5.
        self.emit("addPlayer", {"name":name, "title":0, "rating":mean})
        self.players.add(name)
    
    ###
    
    def on_adjourn_add (self, match):
        mycolor, opponent, opponentIsOnline, type, minutes, increment, wscore, bscore, curcolor, moveno, eco, date = match.groups()
        opstatus = opponentIsOnline == "Y" and "Online" or "Offline"
        procPlayed = (int(wscore)+int(bscore))*100/79
        self.emit ("addAdjourn", {"opponent": opponent, "opstatus": opstatus, "date": date, "procPlayed": procPlayed })
    
    ###
    
    def playBoardCreated (self, match):
        self.emit("clearSeeks")
    