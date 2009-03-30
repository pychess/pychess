from gobject import *
import re
from pychess.Utils.const import *

#types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\- ]{1,4})"
names = "(\w+)(?:\((\w+)\))?"
mf = "(?:([mf]{1,2})\s?)?"
ratingSplit = re.compile("P|E| ")

unsupportedWilds = { # We need to disable wild 0 and 1, as they allow castling even
                # when the king starts out in the d row. 
                "wild/0": _("Opposite Kings"),
                "wild/1": _("Limited Shuffle"),
                "bughouse": _("Bughouse"),
                "crazyhouse": _("Crazyhouse"),
                "suicide": _("Suicide"),
                "atomic": _("Atomic") }

wilds = { "wild/2": _("Shuffle"),
          "wild/3": _("Random"),
          "wild/4": _("Asymmetric Random"),
          "wild/5": _("Upside Down"),
          "wild/8": _("Pawns Pushed"),
          "wild/8a": _("Pawns Passed"),
          "wild/fr": _("Fischer Random") }

strToVariant = { "wild/2": SHUFFLECHESS,
                 "wild/3": RANDOMCHESS,
                 "wild/4": ASYMMETRICRANDOMCHESS,
                 "wild/5": UPSIDEDOWNCHESS,
                 "wild/8": PAWNSPUSHEDCHESS,
                 "wild/8a": PAWNSPASSEDCHESS,
                 "wild/fr": FISCHERRANDOMCHESS,
                 "losers": LOSERSCHESS }

variantToSeek = { NORMALCHESS : "",
                  SHUFFLECHESS : "wild 2",
                  RANDOMCHESS: "wild 3",
                  ASYMMETRICRANDOMCHESS: "wild 4",
                  UPSIDEDOWNCHESS : "wild 5",
                  PAWNSPUSHEDCHESS : "wild 8",
                  PAWNSPASSEDCHESS : "wild 8a",
                  FISCHERRANDOMCHESS : "wild fr",
                  LOSERSCHESS : "losers" }

standards = { "blitz": _("Blitz"),
              "lightning": _("Lightning"),
              "untimed": _("Untimed"),
              "standard": _("Standard"),
              "losers": _("Losers"),
              "nonstandard": _("Other")}

shortTypes = { "b": _("Blitz"),
               "l": _("Lightning"),
               "u": _("Untimed"),
               "e": _("Examined Game"),
               "s": _("Standard"),
               "w": _("Wild"),
               "x": _("Atomic"),
               "z": _("Crazyhouse"),
               "B": _("Bughouse"),
               "L": _("Losers"),
               "S": _("Suicide") }

supportedShorts = ("b","l","s","w","L")

def convertName (typename):
    # Try common
    if typename in standards:
        return standards[typename]
    # Get rid of 'Loaded from'
    typename = typename.split()[-1]
    # Try wilds
    if typename in wilds:
        return wilds[typename]
    # Default solution for eco/A00 and a few others
    if "/" in typename:
        a, b = typename.split("/")
        a = a[0].upper() + a[1:]
        b = b[0].upper() + b[1:]
        return a + " " + b
    # Otherwise forget about it
    return typename[0].upper() + typename[1:]

#0x1 - unregistered
#0x2 - computer
#0x4 - GM
#0x8 - IM
#0x10 - FM
#0x20 - WGM
#0x40 - WIM
#0x80 - WFM

#typedic = {"b":_("Blitz"), "s":_("Standard"), "l":_("Lightning")}


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
                "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(%s)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d+):(\d+)\s*-\s*(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)"
                % (ratings, ratings, "|".join(supportedShorts)))
        self.connection.expect_line (self.on_game_add,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) (?:Creating|Continuing) (u?n?rated) ([^ ]+) match\.\}$")
        self.connection.expect_line (self.on_game_remove,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) ([A-Za-z']+) (.+)\} (\*|1/2-1/2|1-0|0-1)$")
        
        self.connection.expect_line (self.on_player_list,
                "([A-Za-z]+)[\^~:\#. &](\\d{2})((?:\\d{1,4}[P E]?)+)")
        self.connection.expect_line (self.on_player_remove,
                "%s is no longer available for matches." % names)
        self.connection.expect_fromto (self.on_player_add,
                "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)" % 
                (names, ratings, ratings, ratings, ratings, ratings),
                "is now available for matches.")
        
        self.connection.expect_line (self.on_adjourn_add,
                "\d+: (W|B) (\w+)\s+(N|Y) \[ (\w+)\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(\w+)\s+(.*)")
        
        #self.connection.expect_fromto (self.playBoardCreated,
        #        "Creating: %s %s %s %s %s ([^ ]+) (\d+) (\d+)" %
        #            (names, ratings, names, ratings, rated),
        #        "{Game (\d+)\s.*")
        
        
        self.connection.lvm.setVariable("seekinfo", True)
        self.connection.lvm.setVariable("seekremove", True)
        #self.connection.lvm.setVariable("seek", False)
        
        self.connection.lvm.setVariable("gin", True)
        self.connection.lvm.setVariable("allresults", True)
        
        #b: blitz      l: lightning   u: untimed      e: examined game
        #s: standard   w: wild        x: atomic       z: crazyhouse        
        #B: Bughouse   L: losers      S: Suicide
        print >> self.connection.client, "games /sblwL"
        
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
    
    def refreshSeeks (self):
        print >> self.connection.client, "iset seekinfo 1"
    
    def getPlayerlist (self):
        return self.players.copy()
    
    ###
    
    def on_seek_add (self, match):
        parts = match.groups()[0].split(" ")
        # The <s> message looks like:
        # <s> index w=name_from ti=titles rt=rating t=time i=increment
        #     r=rated('r')/unrated('u') tp=type("fr"/"4","blitz") c=color
        #     rr=rating_range(lower-upper) a=automatic?('t'/'f')
        #     f=formula_checked('t'/f')
        
        seek = {"gameno": parts[0]}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            seek[key] = value
            if key == "tp":
                if value in unsupportedWilds:
                    return
                seek[key] = convertName(value)
            if key == "rr":
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
        if type in unsupportedWilds: return
        game = {"gameno":gameno, "wn":wn, "bn":bn, "private":private == "p",
                "type":shortTypes[type], "min":int(min), "inc":int(inc) }
        self.emit("addGame", game)
    
    def on_game_add (self, match):
        gameno, wn, bn, rated, type = match.groups()
        if type in unsupportedWilds: return
        self.emit("addGame", {"gameno":gameno, "wn":wn, "bn":bn,
                              "type":convertName(type), "private":False})
    
    def on_game_remove (self, match):
        gameno, wn, bn, person, comment, result = match.groups()
        result = reprResult.index(result)
        self.emit("removeGame", gameno, result, comment)
    
    ###
    
    def on_player_list (self, match):
        handle, title, ratings = match.groups()
        numratings = 0
        ratingtotal = 0
        for rating in ratingSplit.split(ratings):
            if rating.isdigit() and int(rating) > 0:
                numratings += 1
                ratingtotal += int(rating)
        mean = numratings > 0 and ratingtotal/numratings or 0
        self.emit("addPlayer", {"name": handle, "rating": mean, "title":int(title,16)})
        self.players.add(handle)
    
    def on_player_remove (self, match):
        name, title = match.groups()
        self.emit("removePlayer", name)
        if name in self.players:
            self.players.remove(name)
    
    def on_player_add (self, matches):
        name, title, blitz, std, wild, light, bug = matches[0].groups()
        numratings = 0
        ratingtotal = 0
        for rating in (blitz, std, wild, light, bug):
            if rating.isdigit() and int(rating) > 0:
                numratings += 1
                ratingtotal += int(rating)
        mean = numratings > 0 and ratingtotal/numratings or 0
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

if __name__ == "__main__":
    assert convertName("Loaded from eco/a00") == convertName("eco/a00") == "Eco A00"
    assert convertName("wild/fr") == _("Fischer Random")
    assert convertName("blitz") == _("Blitz")
