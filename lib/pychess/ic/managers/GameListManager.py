from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE
import re
from pychess.Utils.const import *
from pychess.ic import *
from pychess.ic.FICSObjects import *
from pychess.ic.managers.BoardManager import parse_reason
from pychess.System.Log import log

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\- ]{1,4})"
titleslist = "(?:GM|IM|FM|WGM|WIM|WFM|TM|SR|TD|CA|C|U|D|B|T|\*)"
titleslist_re = re.compile(titleslist)
titles = "((?:\(%s\))+)?" % titleslist
names = "([a-zA-Z]+)%s" % titles
mf = "(?:([mf]{1,2})\s?)?"
whomatch = "(?:(?:([-0-9+]{1,4})([\^~:\#. &])%s))" % names
whomatch_re = re.compile(whomatch)
rating_re = re.compile("[0-9]{2,}")
deviation_estimated_re = re.compile("E")
deviation_provisional_re = re.compile("P")

class GameListManager (GObject):
    
    __gsignals__ = {
        'addSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'clearSeeks' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        
        'playerConnected' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerDisconnected' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerWhoI' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerWho' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerUnavailable' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerAvailable' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
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
                                     "<wa> ([A-Za-z]+)([\^~:\#. &])(\\d{2})" + "(\d{1,4})([P E])" * 5)
        self.connection.expect_line (self.on_player_disconnect, "<wd> ([A-Za-z]+)")
        self.connection.expect_line (self.on_player_whoI,
                                     "([A-Za-z]+)([\^~:\#. &])(\\d{2})" + "(\d{1,4})([P E])" * 5)
        self.connection.expect_line (self.on_player_who, "%s(?:\s{2,}%s)+" % (whomatch, whomatch))
        self.connection.expect_line (self.on_player_unavailable, "%s is no longer available for matches." % names)
        self.connection.expect_fromto (self.on_player_available, "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)" % 
                (names, ratings, ratings, ratings, ratings, ratings), "is now available for matches.")
        
        self.connection.lvm.setVariable("seekinfo", True)
        self.connection.lvm.setVariable("seekremove", True)
        self.connection.lvm.setVariable("showownseek", True)
        
    def seek (self, startmin, incsec, game_type, rated, ratings=(0, 9999),
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
            if key in ('w', 'r', 't', 'i'):
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
        gameno, wrating, wname, brating, bname, private, shorttype, rated, min, \
            inc, wmin, wsec, bmin, bsec, wmat, bmat, color, movno = match.groups()
        try:
            gametype = GAME_TYPES_BY_SHORT_FICS_NAME[shorttype]
        except KeyError: return
        
        wplayer = self.connection.players.get(FICSPlayer(wname))
        bplayer = self.connection.players.get(FICSPlayer(bname))
        game = FICSGame(wplayer, bplayer, gameno=int(gameno),
            rated=(rated == "r"), private=(private == "p"), min=int(min),
            inc=int(inc), game_type=gametype)
        
        for player, rating in ((wplayer, wrating), (bplayer, brating)):
            if player.status != IC_STATUS_PLAYING:
                player.status = IC_STATUS_PLAYING
            if player.game != game:
                player.game = game
            rating = self.parseRating(rating)
            if player.ratings[gametype.rating_type].elo != rating:
                player.ratings[gametype.rating_type].elo = rating
        
        self.connection.games.get(game)
        
    def on_game_add (self, match):
        gameno, wname, bname, rated, game_type = match.groups()
        if game_type not in GAME_TYPES: return
        wplayer = self.connection.players.get(FICSPlayer(wname))
        bplayer = self.connection.players.get(FICSPlayer(bname))
        game = FICSGame(wplayer, bplayer, gameno=int(gameno),
            rated=(rated == "rated"), game_type=GAME_TYPES[game_type])
        
        for player in (wplayer, bplayer):
            if player.status != IC_STATUS_PLAYING:
                player.status = IC_STATUS_PLAYING
            if player.game != game:
                player.game = game
        
        self.connection.games.get(game)
    
    def on_game_remove (self, match):
        gameno, wname, bname, person, comment, result = match.groups()
        result, reason = parse_reason(reprResult.index(result), comment, wname=wname)
        
        wplayer = FICSPlayer(wname)
        try:
            wplayer = self.connection.players.get(wplayer, create=False)
            wplayer.restore_previous_status() # no status update will be sent by
            # FICS if the player doesn't become available, so we restore
            # previous status first (not necessarily true, but the best guess)
        except KeyError: pass
        bplayer = FICSPlayer(bname)
        try:
            bplayer = self.connection.players.get(bplayer, create=False)
            bplayer.restore_previous_status()
        except KeyError: pass
        
        game = FICSGame(wplayer, bplayer, gameno=int(gameno), result=result,
                        reason=reason)
        game = self.connection.games.get(game, emit=False)
        self.connection.games.game_ended(game)
        # Do this last to give anybody connected to the game's signals a chance
        # to disconnect from them first
        wplayer.game = None
        bplayer.game = None
    
    ###
    
    def __parseStatus (self, status):
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
    
    @staticmethod
    def parseRating (rating):
        if rating:
            m = rating_re.match(rating)
            if m: return int(m.group(0))
            else: return 0
        else: return 0
    
    def __parseDeviation (self, deviation):
        if deviation_estimated_re.match(deviation):
            return DEVIATION_ESTIMATED
        elif deviation_provisional_re.match(deviation):
            return DEVIATION_PROVISIONAL
        else:
            return DEVIATION_NONE
    
    def __parseTitleHex (self, titlehex):
        titles = set()
        for hex in HEX_TO_TITLE:
            if int(titlehex, 16) & hex:
                titles.add(HEX_TO_TITLE[hex])
        return titles
    
    def __parseTitles (self, titles):
        _titles = set()
        if titles:
            for title in titleslist_re.findall(titles):
                if title in TITLES:
                    _titles.add(TITLES[title])
        return _titles
    
    def on_player_connect (self, match):
        name, status, titlehex, blitz, blitzdev, std, stddev, light, lightdev, \
            wild, wilddev, losers, losersdev = match.groups()
        player = self.connection.players.get(FICSPlayer(name))
        copy = player.copy()
        copy.online = True
        copy.status = self.__parseStatus(status)
        copy.titles |= self.__parseTitleHex(titlehex)        

        for ratingtype, elo, dev in \
                ((TYPE_BLITZ, blitz, blitzdev),
                 (TYPE_STANDARD, std, stddev),
                 (TYPE_LIGHTNING, light, lightdev),
                 (TYPE_WILD, wild, wilddev),
                 (TYPE_LOSERS, losers, losersdev)):
            copy.ratings[ratingtype].elo = self.parseRating(elo)
            copy.ratings[ratingtype].deviation = self.__parseDeviation(dev)

        player.update(copy)
    
    def on_player_disconnect (self, match):
        name = match.groups()[0]
        self.connection.players.player_disconnected(FICSPlayer(name))
    
    def on_player_whoI (self, match):
        self.on_player_connect(match)
    
    def on_player_who (self, match):
        for blitz, status, name, titles in whomatch_re.findall(match.string):
            player = self.connection.players.get(FICSPlayer(name))
            copy = player.copy()
            copy.online = True
            copy.status = self.__parseStatus(status)
            copy.titles |= self.__parseTitles(titles)
            copy.ratings[TYPE_BLITZ].elo = self.parseRating(blitz)
            player.update(copy)
    
    def on_player_unavailable (self, match):
        name, titles = match.groups()
        player = self.connection.players.get(FICSPlayer(name))
        copy = player.copy()
        copy.titles |= self.__parseTitles(titles)
        # we get here after players start a game, so we make sure that we don't
        # overwrite IC_STATUS_PLAYING
        if copy.game is None and copy.status != IC_STATUS_PLAYING:
            copy.status = IC_STATUS_NOT_AVAILABLE
        player.update(copy)
        
    def on_player_available (self, matches):
        name, titles, blitz, std, wild, light, bug = matches[0].groups()
        player = self.connection.players.get(FICSPlayer(name))
        copy = player.copy()
        copy.online = True
        copy.status = IC_STATUS_AVAILABLE
        copy.titles |= self.__parseTitles(titles)
        copy.ratings[TYPE_BLITZ].elo = self.parseRating(blitz)
        copy.ratings[TYPE_STANDARD].elo = self.parseRating(std)
        copy.ratings[TYPE_LIGHTNING].elo = self.parseRating(light)
        copy.ratings[TYPE_WILD].elo = self.parseRating(wild)
        player.update(copy)
        
if __name__ == "__main__":
    assert type_to_display_text("Loaded from eco/a00") == type_to_display_text("eco/a00") == "Eco A00"
    assert type_to_display_text("wild/fr") == Variants.variants[FISCHERRANDOMCHESS].name
    assert type_to_display_text("blitz") == GAME_TYPES["blitz"].display_text
