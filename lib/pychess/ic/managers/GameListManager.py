from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE
import re
from pychess.Utils.const import *
from pychess.System.Log import log
from pychess.ic.FICSObjects import FICSPlayer, FICSGame

#types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\- ]{1,4})"
titleslist = "(?:GM|IM|FM|WGM|WIM|TM|SR|TD|CA|C|U|D|B|T|\*)"
titles = "((?:\(%s\))+)?" % titleslist
names = "([a-zA-Z]+)%s" % titles
mf = "(?:([mf]{1,2})\s?)?"
whomatch = "(?:(?:([-0-9+]{1,4})([\^~:\#. &])%s))" % names

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

shortToRatingType = { "b": TYPE_BLITZ,
                      "l": TYPE_LIGHTNING,
                      "s": TYPE_STANDARD,
                      "w": TYPE_WILD,
                      "L": TYPE_LOSERS,
                      "u": TYPE_STANDARD }

supportedShorts = ("b", "l", "s", "w", "L", "u")

hexToTitle = { 0x1 : "U",
               0x2 : "C",
               0x4 : "GM",
               0x8 : "IM",
               0x10 : "FM",
               0x20 : "WGM",
               0x40 : "WIM",
               0x80 : "WFM" }

# From FICS 'help who':
translatedTitles = { 
                    "*": _("Administrator"),
                    "B": _("Blindfold Account"),
                    "C": _("Computer Account"),
                    "T": _("Team Account"),
                    "U": _("Unregistered User"),
                    "CA": _("Chess Advisor"),
                    "SR": _("Service Representative"),
                    "TD": _("Tournament Director"),
                    "TM": _("Mamer Manager"),
                    "FM": _("FIDE Master"),
                    "IM": _("International Master"),
                    "GM": _("Grand Master"),
                    "WIM": _("Women's International Master"),
                    "WGM": _("Women's Grand Master"),
                    }

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

#typedic = {"b":_("Blitz"), "s":_("Standard"), "l":_("Lightning")}


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
                % (ratings, ratings, "|".join(supportedShorts)))
        self.connection.expect_line (self.on_game_add,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) (?:Creating|Continuing) (u?n?rated) ([^ ]+) match\.\}$")
        self.connection.expect_line (self.on_game_remove,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) ([A-Za-z']+) (.+)\} (\*|1/2-1/2|1-0|0-1)$")

        self.connection.expect_line (self.on_player_connect, "<wa> ([A-Za-z]+)([\^~:\#. &])(\\d{2})(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)")
        self.connection.expect_line (self.on_player_disconnect, "<wd> ([A-Za-z]+)")
        self.connection.expect_line (self.on_player_whoI, "([A-Za-z]+)([\^~:\#. &])(\\d{2})(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)(\d{1,4})([P E]?)")
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
                
    ###
    
    def seek (self, startmin, incsec, rated, ratings=(0,9999), color=None, variant=NORMALCHESS, manual=False):
        rchar = rated and "r" or "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        print "seek %d %d %s %s %d-%d %s %s" % \
            (startmin, incsec, rchar, cchar, ratings[0], ratings[1], variantToSeek[variant], manual and "m" or "")        
        print >> self.connection.client, "seek %d %d %s %s %d-%d %s %s" % \
                (startmin, incsec, rchar, cchar, ratings[0], ratings[1], variantToSeek[variant], manual and "m" or "")
    
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
            if key in ('w','r','t','i'):
                seek[key] = value
            if key == "tp":
                if value in unsupportedWilds:
                    return
                seek[key] = convertName(value)
            if key == "rr":
                seek["rmin"], seek["rmax"] = value.split("-")
            elif key == "ti":
                seek["cp"] = bool(int(value) & 2) # 0x2 - computer
                title = ""
                for hex in hexToTitle.keys():
                    if int(value, 16) & hex:
                        title += "(" + hexToTitle[hex] + ")"
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
        if shorttype not in supportedShorts: return
        rated = rated == "r"
        type = shortTypes[shorttype]
        min = int(min)
        inc = int(inc)
        private = private == "p"
        game = FICSGame(gameno, FICSPlayer(wname), FICSPlayer(bname), rated=rated,
                        type=type, min=min, inc=inc, private=private)
        wrating = self.__parseDigits(wrating) and int(self.__parseDigits(wrating)) or 0
        brating = self.__parseDigits(brating) and int(self.__parseDigits(brating)) or 0
        game.wplayer.addRating(shortToRatingType[shorttype], wrating)
        game.bplayer.addRating(shortToRatingType[shorttype], brating)
        self.emit("addGame", game)
    
    def on_game_add (self, match):
        gameno, wname, bname, rated, type = match.groups()
        if type in unsupportedWilds: return
        rated = rated == "rated"
        type = convertName(type)
        game = FICSGame(gameno, FICSPlayer(wname), FICSPlayer(bname), rated=rated,
                        type=type, private=False)
        self.emit("addGame", game)
    
    def on_game_remove (self, match):
        gameno, wname, bname, person, comment, result = match.groups()
        result = reprResult.index(result)
        parts = set(re.findall("\w+",comment))
        if result in (WHITEWON, BLACKWON):
            if "resigns" in parts:
                reason = WON_RESIGN
            elif "disconnection" in parts:
                reason = WON_DISCONNECTION
            elif "time" in parts:
                reason = WON_CALLFLAG
            elif "checkmated" in parts:
                reason = WON_MATE
            elif "adjudication" in parts:
                reason = WON_ADJUDICATION
            else:
                reason = UNKNOWN_REASON
        elif result == DRAW:
            if "repetition" in parts:
                reason = DRAW_REPITITION
            elif "material" in parts and "time" in parts:
                if re.search(wname + " ran out of time", comment, re.IGNORECASE):
                    reason = DRAW_BLACKINSUFFICIENTANDWHITETIME
                else:
                    reason = DRAW_WHITEINSUFFICIENTANDBLACKTIME
            elif "material" in parts:
                reason = DRAW_INSUFFICIENT
            elif "time" in parts:
                reason = DRAW_CALLFLAG
            elif "agreement" in parts:
                reason = DRAW_AGREE
            elif "stalemate" in parts:
                reason = DRAW_STALEMATE
            elif "50" in parts:
                reason = DRAW_50MOVES
            elif "length" in parts:
                # FICS has a max game length on 800 moves
                reason = DRAW_LENGTH
            elif "adjudication" in parts:
                reason = DRAW_ADJUDICATION
            else:
                reason = UNKNOWN_REASON
        elif "adjourned" in parts:
            result = ADJOURNED
            if "connection" in parts:
                reason = ADJOURNED_LOST_CONNECTION
            elif "agreement" in parts:
                reason = ADJOURNED_AGREEMENT
            elif "shutdown" in parts:
                reason = ADJOURNED_SERVER_SHUTDOWN
            else:
                reason = UNKNOWN_REASON
        elif "aborted" in parts:
            result = ABORTED
            if "agreement" in parts:
                reason = ABORTED_AGREEMENT
            elif "moves" in parts:
                # lost connection and too few moves; game aborted *
                reason = ABORTED_EARLY
            elif "move" in parts:
                # Game aborted on move 1 *
                reason = ABORTED_EARLY
            elif "shutdown" in parts:
                reason = ABORTED_SERVER_SHUTDOWN
            elif "adjudication" in parts:
                reason = ABORTED_ADJUDICATION
            else:
                reason = UNKNOWN_REASON
        elif "courtesyadjourned" in parts:
            result = ADJOURNED
            reason = ADJOURNED_COURTESY
        elif "courtesyaborted" in parts:
            result = ABORTED
            reason = ABORTED_COURTESY
        else:
            result = UNKNOWN_STATE
            reason = UNKNOWN_REASON
        
        game = FICSGame(gameno, FICSPlayer(wname), FICSPlayer(bname),
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
        for hex in hexToTitle.keys():
            if int(titlehex, 16) & hex:
                titles.append(hexToTitle[hex])
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
        log.debug("GLM.on_player_connect():\n")
        log.debug(match.string + "\n")
        log.debug(repr(ficsplayer) + "\n")
        self.emit("playerConnected", ficsplayer)
        if name not in self.players:
            self.players.add(name)
    
    def on_player_disconnect (self, match):
        name = match.groups()[0]
        log.debug("GLM.on_player_disconnect():\n")
        log.debug(match.string + "\n")
        log.debug(name + "\n")
        self.emit("playerDisconnected", FICSPlayer(name))
        if name in self.players:
            self.players.remove(name)
    
    def on_player_whoI (self, match):
        name, status, titlehex, blitz, blitzdev, std, stddev, light, lightdev, \
            wild, wilddev, bug, bugdev, crazy, crazydev, suicide, suicidedev, \
            losers, losersdev, atomic, atomicdev = match.groups()
        status = self.__getStatus(status)
        titles = []
        for hex in hexToTitle.keys():
            if int(titlehex, 16) & hex:
                titles.append(hexToTitle[hex])
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
        self.emit ("addAdjourn", {"opponent": opponent, "opstatus": opstatus, "date": date,
                                  "procPlayed": procPlayed })
    
    ###
    
    def gameCreated (self, match):
        self.emit("clearSeeks")

if __name__ == "__main__":
    assert convertName("Loaded from eco/a00") == convertName("eco/a00") == "Eco A00"
    assert convertName("wild/fr") == _("Fischer Random")
    assert convertName("blitz") == _("Blitz")
