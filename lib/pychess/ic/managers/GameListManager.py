from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE
import re
from pychess.Utils.const import *
from pychess.ic import *
from pychess.ic.FICSObjects import FICSPlayer, FICSGame
from pychess.ic.managers.BoardManager import parse_reason
from pychess.System.Log import log

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\- ]{1,4})"
titleslist = "(?:GM|IM|FM|WGM|WIM|TM|SR|TD|CA|C|U|D|B|T|\*)"
titles = "((?:\(%s\))+)?" % titleslist
names = "([a-zA-Z]+)%s" % titles
mf = "(?:([mf]{1,2})\s?)?"
whomatch = "(?:(?:([-0-9+]{1,4})([\^~:\#. &])%s))" % names

class GameListManager (GObject):
    
    __gsignals__ = {
        'addSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'clearSeeks' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        
        'addGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        
        'playerConnected' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerDisconnected' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerWhoI' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerWho' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerUnavailable' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerAvailable' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        
        'addAdjourn' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.players = set()
        
        self.connection.expect_line (self.on_seek_clear, "<sc>")
        self.connection.expect_line (self.on_seek_add, "<s> (.+)")
        self.connection.expect_line (self.on_seek_add, "<sn> (.+)")
        self.connection.expect_line (self.on_seek_remove, "<sr> ([\d ]+)")
        
        self.connection.expect_line (self.on_game_list,
                "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(%s)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d+):(\d+)\s*-\s*(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)"
                % (ratings, ratings, "|".join(GAME_TYPES_BY_SHORT_FICS_NAME.keys())))
        self.connection.expect_line (self.on_game_add,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) (?:Creating|Continuing) (u?n?rated) ([^ ]+) match\.\}$")
        self.connection.expect_line (self.on_game_remove,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) ([A-Za-z']+) (.+)\} (\*|1/2-1/2|1-0|0-1)$")

        self.connection.expect_line (self.on_player_connect,
                                     "<wa> ([A-Za-z]+)([\^~:\#. &])(\\d{2})" + "(\d{1,4})([P E])"*9)
        self.connection.expect_line (self.on_player_disconnect, "<wd> ([A-Za-z]+)")
        self.connection.expect_line (self.on_player_whoI,
                                     "([A-Za-z]+)([\^~:\#. &])(\\d{2})" + "(\d{1,4})([P E])"*9)
        self.connection.expect_line (self.on_player_who, "%s(?:\s{2,}%s)+" % (whomatch, whomatch))
        self.connection.expect_line (self.on_player_unavailable, "%s is no longer available for matches." % names)
        self.connection.expect_fromto (self.on_player_available, "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)" % 
                (names, ratings, ratings, ratings, ratings, ratings), "is now available for matches.")
        
        self.connection.expect_line (self.on_adjourn_add,
                "\d+: (W|B) (\w+)\s+(N|Y) \[ (\w+)\s+(\d+)\s+(\d+)\]\s+(\d+)-(\d+)\s+(W|B)(\d+)\s+(\w+)\s+(.*)")
        
        #self.connection.expect_fromto (self.gameCreated,
        #        "Creating: %s %s %s %s %s ([^ ]+) (\d+) (\d+)" %
        #            (names, ratings, names, ratings, rated),
        #        "{Game (\d+)\s.*")
        
        
        self.connection.lvm.setVariable("seekinfo", True)
        self.connection.lvm.setVariable("seekremove", True)
        #self.connection.lvm.setVariable("seek", False)
        self.connection.lvm.setVariable("showownseek", True)
        
        self.connection.lvm.setVariable("gin", True)
        self.connection.lvm.setVariable("pin", True)
        self.connection.lvm.setVariable("allresults", True)
        
        # TODO: This makes login take alot longer... maybe gobject.timeout_add it?
        self.who()
        
        #b: blitz      l: lightning   u: untimed      e: examined game
        #s: standard   w: wild        x: atomic       z: crazyhouse        
        #B: Bughouse   L: losers      S: Suicide
        print >> self.connection.client, "games /sblwL"
        
        #self.connection.lvm.setVariable("availmax", True)
        #self.connection.lvm.setVariable("availmin", True)
        self.connection.lvm.setVariable("availinfo", True)
        
        print >> self.connection.client, "stored"
    
    def who (self):
        print >> self.connection.client, "who IsblwzLSBx"
        # the previous who command won't get title info such as (TM)
        print >> self.connection.client, "who"
    
    def seek (self, startmin, incsec, game_type, rated, ratings=(0,9999),
              color=None, manual=False):
        log.debug("GameListManager.seek: %s %s %s %s %s %s %s\n" % \
            (startmin, incsec, game_type, rated, str(ratings), color, manual))
        rchar = rated and "r" or "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        manual = "m" if manual else ""
        s = "seek %d %d %s %s %d-%d %s" % \
            (startmin, incsec, rchar, cchar, ratings[0], ratings[1], manual)
        if isinstance(game_type, VariantGameType):
            s += " " + game_type.seek_text
        print s        
        print >> self.connection.client, s
    
    def refreshSeeks (self):
        print >> self.connection.client, "iset seekinfo 1"
    
    def getPlayerlist (self):
        return self.players.copy()
    
    ###
    
    def on_seek_add (self, match):
        parts = match.groups()[0].split(" ")
        # The <s> message looks like:
        # <s> index w=name_from ti=titles rt=rating t=time i=increment
        #     r=rated('r')/unrated('u') tp=type("wild/fr", "wild/4","blitz")
        #     c=color rr=rating_range(lower-upper) a=automatic?('t'/'f')
        #     f=formula_checked('t'/f')
        
        seek = {"gameno": parts[0]}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            if key in ('w','r','t','i'):
                seek[key] = value
            if key == "tp":
                try:
                    seek["gametype"] = GAME_TYPES[value]
                except KeyError: return
            if key == "rr":
                seek["rmin"], seek["rmax"] = value.split("-")
                seek["rmin"] = int(seek["rmin"])
                seek["rmax"] = int(seek["rmax"])                
            elif key == "ti":
                seek["cp"] = bool(int(value) & 2) # 0x2 - computer
                title = ""
                for hex in HEX_TO_TITLE.keys():
                    if int(value, 16) & hex:
                        title += "(" + \
                            TITLE_TYPE_DISPLAY_TEXTS_SHORT[HEX_TO_TITLE[hex]] + ")"
                seek["title"] = title
            elif key == "rt":
                if value[-1] in (" ", "P", "E"):
                    seek[key] = value[:-1]
                else: seek[key] = value
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
        gameno, wrating, wname, brating, bname, private, shorttype, rated, min, inc, \
           wmin, wsec, bmin, bsec, wmat, bmat, color, movno = match.groups()
        if shorttype not in GAME_TYPES_BY_SHORT_FICS_NAME: return
        game_type = GAME_TYPES_BY_SHORT_FICS_NAME[shorttype]
        rated = rated == "r"
        private = private == "p"
        game = FICSGame(int(gameno), FICSPlayer(wname), FICSPlayer(bname), rated=rated,
            game_type=game_type, min=int(min), inc=int(inc), private=private)
        wrating = self.__parseDigits(wrating) and int(self.__parseDigits(wrating)) or 0
        brating = self.__parseDigits(brating) and int(self.__parseDigits(brating)) or 0
        game.wplayer.addRating(game_type.rating_type, wrating)
        game.bplayer.addRating(game_type.rating_type, brating)
        self.emit("addGame", game)
    
    def on_game_add (self, match):
        gameno, wname, bname, rated, type = match.groups()
        if type not in GAME_TYPES: return
        game_type = GAME_TYPES[type]
        rated = rated == "rated"
        game = FICSGame(int(gameno), FICSPlayer(wname), FICSPlayer(bname), rated=rated,
                        game_type=game_type, private=False)
        self.emit("addGame", game)
    
    def on_game_remove (self, match):
        gameno, wname, bname, person, comment, result = match.groups()
        result, reason = parse_reason(reprResult.index(result), comment, wname=wname)
        game = FICSGame(int(gameno), FICSPlayer(wname), FICSPlayer(bname),
                        result=result, reason=reason)
        self.emit("removeGame", game)
    
    ###
    
    def __getStatus (self, status):
        if status == "^":
            return IC_STATUS_PLAYING
        elif status == " ":
            return IC_STATUS_AVAILABLE
        elif status == ".":
            return IC_STATUS_IDLE
        elif status == "#":
            return IC_STATUS_EXAMINING
        elif status == ":":
            return IC_STATUS_NOT_AVAILABLE
        elif status == "~":
            return IC_STATUS_RUNNING_SIMUL_MATCH
        elif status == "&":
            return IC_STATUS_IN_TOURNAMENT
        
    def __parseDigits (self, rating):
        if rating:
            m = re.match("[0-9]+", rating)
            if m: return m.group(0)
            else: return None
        else: return None
    
    def __getDeviation (self, deviation):
        if re.match("^\s*$", deviation):
            return DEVIATION_NONE
        elif re.match("E", deviation):
            return DEVIATION_ESTIMATED
        elif re.match("P", deviation):
            return DEVIATION_PROVISIONAL
        else:
            return None
    
    def on_player_connect (self, match):
        name, status, titlehex, blitz, blitzdev, std, stddev, light, lightdev, \
            wild, wilddev, bug, bugdev, crazy, crazydev, suicide, suicidedev, \
            losers, losersdev, atomic, atomicdev = match.groups()
        # TODO: should all of the following shit be done in FICSPlayer?
        status = self.__getStatus(status)
        # TODO: titles = self.__parseTitleHex(title)? Put it in FICSPlayer?
        titles = []
        for hex in HEX_TO_TITLE:
            if int(titlehex, 16) & hex:
                titles.append(TITLE_TYPE_DISPLAY_TEXTS_SHORT[HEX_TO_TITLE[hex]])
        blitz = self.__parseDigits(blitz) and int(self.__parseDigits(blitz)) or 0
        blitzdev = self.__getDeviation(blitzdev)
        std = self.__parseDigits(std) and int(self.__parseDigits(std)) or 0
        stddev = self.__getDeviation(stddev)
        light = self.__parseDigits(light) and int(self.__parseDigits(light)) or 0
        lightdev = self.__getDeviation(lightdev)
        wild = self.__parseDigits(wild) and int(self.__parseDigits(wild)) or 0
        wilddev = self.__getDeviation(wilddev)
        bug = self.__parseDigits(bug) and int(self.__parseDigits(bug)) or 0
        bugdev = self.__getDeviation(bugdev)
        crazy = self.__parseDigits(crazy) and int(self.__parseDigits(crazy)) or 0
        crazydev = self.__getDeviation(crazydev)
        suicide = self.__parseDigits(suicide) and int(self.__parseDigits(suicide)) or 0
        suicidedev = self.__getDeviation(suicidedev)
        losers = self.__parseDigits(losers) and int(self.__parseDigits(losers)) or 0
        losersdev = self.__getDeviation(losersdev)
        atomic = self.__parseDigits(atomic) and int(self.__parseDigits(atomic)) or 0
        atomicdev = self.__getDeviation(atomicdev)
        ficsplayer = FICSPlayer(name, status=status, titles=titles,
                                blitzrating=blitz, blitzdeviation=blitzdev,
                                stdrating=std, stddeviation=stddev,
                                lightrating=light, lightdeviation=lightdev,
                                wildrating=wild, wilddeviation=wilddev,
                                bughouserating=bug, bughousedeviation=bugdev,
                                crazyhouserating=crazy, crazyhousedeviation=crazydev,
                                suiciderating=suicide, suicidedeviation=suicidedev,
                                losersrating=losers, losersdeviation=losersdev,
                                atomicrating=atomic, atomicdeviation=atomicdev)
#        log.debug("GLM.on_player_connect():\n")
#        log.debug(match.string + "\n")
#        log.debug(repr(ficsplayer) + "\n")
        self.emit("playerConnected", ficsplayer)
        if name not in self.players:
            self.players.add(name)
    
    def on_player_disconnect (self, match):
        name = match.groups()[0]
#        log.debug("GLM.on_player_disconnect():\n")
#        log.debug(match.string + "\n")
#        log.debug(name + "\n")
        self.emit("playerDisconnected", FICSPlayer(name))
        if name in self.players:
            self.players.remove(name)
    
    def on_player_whoI (self, match):
        name, status, titlehex, blitz, blitzdev, std, stddev, light, lightdev, \
            wild, wilddev, bug, bugdev, crazy, crazydev, suicide, suicidedev, \
            losers, losersdev, atomic, atomicdev = match.groups()
        status = self.__getStatus(status)
        titles = []
        for hex in HEX_TO_TITLE:
            if int(titlehex, 16) & hex:
                titles.append(TITLE_TYPE_DISPLAY_TEXTS_SHORT[HEX_TO_TITLE[hex]])
        blitz = self.__parseDigits(blitz) and int(self.__parseDigits(blitz)) or 0
        blitzdev = self.__getDeviation(blitzdev)
        std = self.__parseDigits(std) and int(self.__parseDigits(std)) or 0
        stddev = self.__getDeviation(stddev)
        light = self.__parseDigits(light) and int(self.__parseDigits(light)) or 0
        lightdev = self.__getDeviation(lightdev)
        wild = self.__parseDigits(wild) and int(self.__parseDigits(wild)) or 0
        wilddev = self.__getDeviation(wilddev)
        bug = self.__parseDigits(bug) and int(self.__parseDigits(bug)) or 0
        bugdev = self.__getDeviation(bugdev)
        crazy = self.__parseDigits(crazy) and int(self.__parseDigits(crazy)) or 0
        crazydev = self.__getDeviation(crazydev)
        suicide = self.__parseDigits(suicide) and int(self.__parseDigits(suicide)) or 0
        suicidedev = self.__getDeviation(suicidedev)
        losers = self.__parseDigits(losers) and int(self.__parseDigits(losers)) or 0
        losersdev = self.__getDeviation(losersdev)
        atomic = self.__parseDigits(atomic) and int(self.__parseDigits(atomic)) or 0
        atomicdev = self.__getDeviation(atomicdev)
        ficsplayer = FICSPlayer(name, status=status, titles=titles,
                                blitzrating=blitz, blitzdeviation=blitzdev,
                                stdrating=std, stddeviation=stddev,
                                lightrating=light, lightdeviation=lightdev,
                                wildrating=wild, wilddeviation=wilddev,
                                bughouserating=bug, bughousedeviation=bugdev,
                                crazyhouserating=crazy, crazyhousedeviation=crazydev,
                                suiciderating=suicide, suicidedeviation=suicidedev,
                                losersrating=losers, losersdeviation=losersdev,
                                atomicrating=atomic, atomicdeviation=atomicdev)
        self.emit("playerWhoI", ficsplayer)
        if name not in self.players:
            self.players.add(name)
    
    def on_player_who (self, match):
#        print "GameListManager.on_player_list_w(): match.string = %s" % match.string
        for blitz, status, name, title in re.findall(whomatch, match.string):
#            print blitz, name, title
            status = self.__getStatus(status)
            titles = []
            if title:
                titles = re.findall(titleslist, title)   
            blitz = self.__parseDigits(blitz) and int(self.__parseDigits(blitz)) or 0
            ficsplayer = FICSPlayer(name, status=status, titles=titles, blitzrating=blitz)         
            self.emit("playerWho", ficsplayer)
            if name not in self.players:
                self.players.add(name)
    
    def on_player_unavailable (self, match):
        name, title = match.groups()
        self.emit("playerUnavailable", FICSPlayer(name, status=IC_STATUS_NOT_AVAILABLE))

    def on_player_available (self, matches):
        name, title, blitz, std, wild, light, bug = matches[0].groups()
        titles = []
        if title:
            titles = re.findall(titleslist, title)
        blitz = self.__parseDigits(blitz) and int(self.__parseDigits(blitz)) or 0
        std = self.__parseDigits(std) and int(self.__parseDigits(std)) or 0
        wild = self.__parseDigits(wild) and int(self.__parseDigits(wild)) or 0
        light = self.__parseDigits(light) and int(self.__parseDigits(light)) or 0
        bug = self.__parseDigits(bug) and int(self.__parseDigits(bug)) or 0
        ficsplayer = FICSPlayer(name, status=IC_STATUS_AVAILABLE, titles=titles,
                                blitzrating=blitz, stdrating=std, wildrating=wild,
                                lightrating=light, bughouserating=bug)
        self.emit("playerAvailable", ficsplayer)
    
    ###
    
    def on_adjourn_add (self, match):
        mycolor, opponent, opponentIsOnline, type, minutes, increment, wscore, \
           bscore, curcolor, moveno, eco, date = match.groups()
        opstatus = opponentIsOnline == "Y" and "Online" or "Offline"
        procPlayed = (int(wscore)+int(bscore))*100/79
        self.emit("addAdjourn", {"opponent": opponent, "opstatus": opstatus, "date": date,
                                  "procPlayed": procPlayed })
    
    ###
    
    def gameCreated (self, match):
        self.emit("clearSeeks")

if __name__ == "__main__":
    assert type_to_display_text("Loaded from eco/a00") == type_to_display_text("eco/a00") == "Eco A00"
    assert type_to_display_text("wild/fr") == Variants.variants[FISCHERRANDOMCHESS].name
    assert type_to_display_text("blitz") == GAME_TYPES["blitz"].display_text
