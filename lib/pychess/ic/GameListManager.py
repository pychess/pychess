
from gobject import *

types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\-]{1,4})"
names = "(\w+)(?:\((\w+)\))?"
mf = "(?:([mf]{1,2})\s?)?"

typedic = {"b":_("Blitz"), "s":_("Standard"), "l":_("Lightning")}

from pychess.Utils.const import WHITE

class GameListManager (GObject):
    
    __gsignals__ = {
        'addSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'clearSeeks' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        
        'addGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        
        'addPlayer' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removePlayer' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        
        'addAdjourn' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect ( "<sc>\n", self.on_seek_clear)
        
        self.connection.expect ( "<s> (.+?)\n", self.on_seek_add)
        
        self.connection.expect ( "<sr> ([\d ]+?)\n", self.on_seek_remove)
        
        
        
        self.connection.expect ( "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(s|b|l)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d+):(\d+)\s*-\s*(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)" % (ratings, ratings), self.on_game_list)
        
        self.connection.expect ( "{Game (\d+) \((\w+) vs\. (\w+)\) (.*?)}", self.on_game_addremove)
        
        
        
        self.connection.expect ( "%s(\.| )%s\s+%s(\.| )%s\s+%s(\.| )%s\n" % (ratings, names, ratings, names, ratings, names), self.on_player_list)
        
        self.connection.expect ( "%s is no longer available for matches." % names, self.on_player_remove)
        
        self.connection.expect ( "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)\s+is now available for matches." % (names, ratings, ratings, ratings, ratings, ratings), self.on_player_add)
        
        
        self.connection.expect ( "\s*\d+: (W|B) (\w+)\s+(N|Y) \[ (\w+)\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(\w+)\s+(.*?)\n", self.on_adjourn_add)
        
        
        self.connection.expect ( "Creating: %s %s %s %s %s %s (\d+) (\d+)\n\r{Game (\d+)\s" % (names, ratings, names, ratings, rated, types), self.playBoardCreated)
        
        
        print >> self.connection.client, "iset seekinfo 1"
        print >> self.connection.client, "iset seekremove 1"
        print >> self.connection.client, "set seek 1"
        
        print >> self.connection.client, "set gin 1"
        print >> self.connection.client, "iset allresults 0"
        print >> self.connection.client, "games /sbl"
        
        print >> self.connection.client, "who a"
        print >> self.connection.client, "set availmax 0"
        print >> self.connection.client, "set availmin 0"
        print >> self.connection.client, "set availinfo 1"
        
        print >> self.connection.client, "stored"
        
        self.connection.connect("disconnecting", self.stop)
        
    def stop (self, connection):
        print >> self.connection.client, "iset seekinfo 0"
        print >> self.connection.client, "iset seekremove 0"
        print >> self.connection.client, "set seek 0"
        
        print >> self.connection.client, "set gin 0"
        
        print >> self.connection.client, "set availinfo 0"
    
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
    
    ###
    
    def on_seek_add (self, client, groups):
        parts = groups[0].split(" ")
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
        
        self.emit("addSeek", seek)
    
    def on_seek_clear (self, *args):
        self.emit("clearSeeks")
    
    def on_seek_remove (self, client, groups):
        for key in groups[0].split(" "):
            if not key: continue
            self.emit("removeSeek", key)
    
    ###
    
    def on_game_list (self, client, groups):
        gameno, wr, wn, br, bn, private, type, rated, min, inc, wmin, wsec, bmin, bsec, wmat, bmat, color, movno = groups
        
        game = {"gameno":gameno, "wn":wn, "bn":bn, "type":typedic[type]}
        self.emit("addGame", game)
    
    def on_game_addremove (self, client, groups):
        gameno, wn, bn, comment = groups
        if comment.split()[0] in ("Creating", "Continuing"):
            c, rated, type, m = comment.split()
            if not type in ("standard", "blitz", "lightning"):
                return
            else:
                type = typedic[type[0]]
            game = {"gameno":gameno, "wn":wn, "bn":bn, "type":type}
            self.emit("addGame", game)
        else:
            self.emit("removeGame", gameno)
    
    ###
    
    def on_player_list (self, client, groups):
        for i in xrange(0, len(groups), 4):
            self.emit("addPlayer", {
                "rating": groups[i],
                "status": groups[i+1],
                "name": groups[i+2],
                "title": groups[i+3]
            })
    
    def on_player_remove (self, client, groups):
        name, title = groups
        self.emit("removePlayer", name)
    
    def on_player_add (self, client, groups):
        name, title, blitz, std, wild, light, bug = groups
        self.emit("addPlayer", \
            {"name":name, "title":title, "rating":blitz, "status": " "})
    
    ###
    
    def on_adjourn_add (self, client, groups):
        mycolor, opponent, opponentIsOnline, type, minutes, increment, wscore, bscore, curcolor, moveno, eco, date = groups
        opstatus = opponentIsOnline == "Y" and "Online" or "Offline"
        procPlayed = (int(wscore)+int(bscore))*100/79
        self.emit ("addAdjourn", {"opponent": opponent, "opstatus": opstatus, "date": date, "procPlayed": procPlayed })
    
    ###
    
    def playBoardCreated (self, client, groups):
        self.emit("clearSeeks")
