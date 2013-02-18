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

DEVIATION = {"E": DEVIATION_ESTIMATED,
             "P": DEVIATION_PROVISIONAL,
             " ": DEVIATION_NONE,
             "" : DEVIATION_NONE,
            }

STATUS = {"^": IC_STATUS_PLAYING,
          " ": IC_STATUS_AVAILABLE,
          ".": IC_STATUS_IDLE,
          "#": IC_STATUS_EXAMINING,
          ":": IC_STATUS_NOT_AVAILABLE,
          "~": IC_STATUS_RUNNING_SIMUL_MATCH,
          "&": IC_STATUS_IN_TOURNAMENT,
          }


class HelperManager (GObject):
    
    __gsignals__ = {
        'playerConnected' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerDisconnected' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerUnavailable' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerAvailable' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerWhoI' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'playerWho' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
    }
    
    def __init__ (self, helperconn, connection):
        GObject.__init__(self)
        
        self.helperconn = helperconn
        self.connection = connection

        self.helperconn.expect_line (self.on_game_list,
                "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(%s)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d:)?(\d+):(\d+)\s*-\s*(\d:)?(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)"
                % (ratings, ratings, "|".join(GAME_TYPES_BY_SHORT_FICS_NAME.keys())))

        # New ivar pin
        # http://www.freechess.org/Help/HelpFiles/new_features.html
        self.helperconn.expect_line (self.on_player_whoI,
                                     "([A-Za-z]+)([\^~:\#. &])(\\d{2})" + "(\d{1,4})([P E])" * 4 + "(\d{1,4})([PE]?)")
        self.helperconn.expect_line (self.on_player_who, "%s(?:\s{2,}%s)+" % (whomatch, whomatch))
        
        self.helperconn.expect_line (self.on_game_add,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) (?:Creating|Continuing) (u?n?rated) ([^ ]+) match\.\}$")
        self.helperconn.expect_line (self.on_game_remove,
                "\{Game (\d+) \(([A-Za-z]+) vs\. ([A-Za-z]+)\) ([A-Za-z']+) (.+)\} (\*|1/2-1/2|1-0|0-1)$")

        self.helperconn.expect_line (self.on_player_connect,
                                     "<wa> ([A-Za-z]+)([\^~:\#. &])(\\d{2})" + "(\d{1,4})([P E])" * 4 + "(\d{1,4})([PE]?)")
        self.helperconn.expect_line (self.on_player_disconnect, "<wd> ([A-Za-z]+)")

        self.helperconn.expect_line (self.on_player_unavailable, "%s is no longer available for matches." % names)
        self.helperconn.expect_fromto (self.on_player_available, "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)" % 
                (names, ratings, ratings, ratings, ratings, ratings), "is now available for matches.")

    def on_game_list (self, match):
        gameno, wrating, wname, brating, bname, private, shorttype, rated, min, \
            inc, whour, wmin, wsec, bhour, bmin, bsec, wmat, bmat, color, movno = match.groups()
        try:
            gametype = GAME_TYPES_BY_SHORT_FICS_NAME[shorttype]
        except KeyError:
            return
        
        if gametype.variant_type in UNSUPPORTED:
            return
            
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
        if game_type not in GAME_TYPES:
            return
        if GAME_TYPES[game_type].variant_type in UNSUPPORTED:
            return
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

    @staticmethod
    def parseRating (rating):
        return int(rating) if rating.isdigit() else 0
    
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
        copy.status = STATUS[status]
        copy.titles |= self.__parseTitleHex(titlehex)        

        for ratingtype, elo, dev in \
                ((TYPE_BLITZ, blitz, blitzdev),
                 (TYPE_STANDARD, std, stddev),
                 (TYPE_LIGHTNING, light, lightdev),
                 (TYPE_WILD, wild, wilddev),
                 (TYPE_LOSERS, losers, losersdev)):
            copy.ratings[ratingtype].elo = self.parseRating(elo)
            copy.ratings[ratingtype].deviation = DEVIATION[dev]

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
            copy.status = STATUS[status]
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
