import pprint
from gobject import *

from pychess.Utils.const import *
from pychess.Utils.IconLoader import load_icon
from pychess.Utils.Rating import Rating
from pychess.System.Log import log
from pychess.Variants import variants
from pychess.ic.managers.FingerManager import type2Type

wildVariants = (SHUFFLECHESS, FISCHERRANDOMCHESS, RANDOMCHESS, ASYMMETRICRANDOMCHESS,
                UPSIDEDOWNCHESS, PAWNSPUSHEDCHESS, PAWNSPASSEDCHESS)

class FICSPlayer (GObject):
    __gsignals__ = {
        'ratingChanged' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
    }
    def __init__ (self, name, titles=None, status=None, blitzrating=None, blitzdeviation=None,
                  stdrating=None, stddeviation=None, lightrating=None, lightdeviation=None,
                  wildrating=None, wilddeviation=None, bughouserating=None, bughousedeviation=None,
                  crazyhouserating=None, crazyhousedeviation=None, suiciderating=None,
                  suicidedeviation=None, losersrating=None, losersdeviation=None,
                  atomicrating=None, atomicdeviation=None):
        assert name != None
        self.name = name
        if titles == None:
            self.titles = []
        else:
            self.titles = titles
        self.status = status
        self.ratings = {}
        self.game = None
#        self.online = False
        
        for type, rating, deviation in ((TYPE_BLITZ, blitzrating, blitzdeviation),
                                        (TYPE_STANDARD, stdrating, stddeviation),
                                        (TYPE_LIGHTNING, lightrating, lightdeviation),
                                        (TYPE_WILD, wildrating, wilddeviation),
                                        (TYPE_BUGHOUSE, bughouserating, bughousedeviation),
                                        (TYPE_CRAZYHOUSE, crazyhouserating, crazyhousedeviation),
                                        (TYPE_SUICIDE, suiciderating, suicidedeviation),
                                        (TYPE_LOSERS, losersrating, losersdeviation),
                                        (TYPE_ATOMIC, atomicrating, atomicdeviation)):
            if rating and rating > 0:
                ratingobj = Rating(type, rating, deviation=deviation)
                self.setRating(type, ratingobj)
        
        log.debug("FICSPlayer.init():\n")
        log.debug("\t Initializing new player: %s\n" % repr(self))
    
    def __hash__ (self):
        """ Two players are equal if the first 10 characters of their name match.
            This is to facilitate matching players from output of commands like the 'game'
            command which only return the first 10 characters of a player's name """
        return hash(self.name[0:10].lower())
    
    def __eq__ (self, player):
        if type(self) == type(player) and self.__hash__() == player.__hash__():
            return True
        else:
            return False
        
    def __repr__ (self):
        r = "name=%s" % self.name
        if self.titles:
            r += ", titles = "
            for title in self.titles:
                r += "(" + title + ")"
        if self.status != None:
            r += ", status = %i" % self.status
        if self.game != None:
            r += ", game = game.gameno = %s" % self.game.gameno
        for type in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_WILD, TYPE_BUGHOUSE,
                     TYPE_CRAZYHOUSE, TYPE_SUICIDE, TYPE_LOSERS, TYPE_ATOMIC):
            if self.ratings.has_key(type):
                typename = [ k for (k, v) in type2Type.iteritems() if type2Type[k] == type ][0]
                r += ", ratings[%s] = (" % typename
                r +=  self.ratings[type].__repr__() + ")"
        return r
    
    def isAvailableForGame (self):    
        if self.status in \
            (IC_STATUS_PLAYING, IC_STATUS_BUSY, IC_STATUS_OFFLINE,
             IC_STATUS_RUNNING_SIMUL_MATCH, IC_STATUS_NOT_AVAILABLE,
             IC_STATUS_EXAMINING, IC_STATUS_IN_TOURNAMENT):
            return False
        else:
            return True
    
    def isObservable (self):
        if self.status in (IC_STATUS_PLAYING, IC_STATUS_EXAMINING):
            return True
        else:
            return False
        
    def isGuest (self):
        if "U" in self.titles:
            return True
        else:
            return False

    def isComputer (self):    
        if "C" in self.titles:
            return True
        else:
            return False

    def isAdmin (self):    
        if "*" in self.titles:
            return True
        else:
            return False

    @classmethod
    def getIconByRating (cls, rating, size=15):
        assert type(rating) == int, "rating not an int: %s" % str(rating)
        
        if rating >= 1900:
            return load_icon(size, "weather-storm")
        elif rating >= 1600:
            return load_icon(size, "weather-showers")
        elif rating >= 1300:
            return load_icon(size, "weather-overcast")
        elif rating >= 1000:
            return load_icon(size, "weather-few-clouds")
        else:
            return load_icon(size, "weather-clear")
    
    def getIcon (self, size=15):
        assert type(size) == int, "size not an int: %s" % str(size)
        
        if self.isGuest():
            return load_icon(size, "stock_people", "system-users")
        elif self.isComputer():
            return load_icon(size, "stock_notebook", "computer")
        elif self.isAdmin():
            return load_icon(size, "stock_book_blue", "accessories-dictionary")
        else:
            return self.getIconByRating(self.getStrength(), size)
    
    def getTitles (self):
        r = ""
        if self.titles:
            for title in self.titles:
                r += "(" + title + ")"
        return r

    def getRating (self, type):
        if self.ratings.has_key(type):
            return self.ratings[type]
        else:
            return None
        
    def setRating (self, type, ratingobj):
        self.ratings[type] = ratingobj
        
    def updateRating (self, type, ratingobj):
        if self.ratings.has_key(type):
            self.ratings[type].update(ratingobj)
        else:
            self.setRating(type, ratingobj)
        
    def addRating (self, type, rating):
        if rating == None: return
        ratingobj = Rating(type, rating)
        self.ratings[type] = ratingobj
        
    def update (self, ficsplayer):
        assert self == ficsplayer
        log.debug("FICSPlayer.update():\n")
        log.debug("\t Merging ficsplayer: %s\n" % repr(ficsplayer))
        log.debug("\t With self: %s\n" % repr(self))
        for title in ficsplayer.titles:
            if title not in self.titles:
                log.debug("\t appending title: %s\n" % title)
                self.titles.append(title)
        if self.status != ficsplayer.status:
            self.status = ficsplayer.status
        for type in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_WILD, TYPE_BUGHOUSE,
                     TYPE_CRAZYHOUSE, TYPE_SUICIDE, TYPE_LOSERS, TYPE_ATOMIC):
            if ficsplayer.ratings.has_key(type) and self.ratings.has_key(type):
                self.ratings[type].update(ficsplayer.ratings[type])
            elif ficsplayer.ratings.has_key(type):
                self.ratings[type] = ficsplayer.ratings[type]
        
    def getRatingMean (self):
        ratingtotal = 0
        numratings = 0
        for ratingtype in self.ratings:
            if self.ratings[ratingtype].deviation == None or \
               self.ratings[ratingtype].deviation == DEVIATION_NONE:
                ratingtotal += self.ratings[ratingtype].elo * 3
                numratings += 3
            if self.ratings[ratingtype].deviation == DEVIATION_ESTIMATED:
                ratingtotal += self.ratings[ratingtype].elo * 2
                numratings += 2
            if self.ratings[ratingtype].deviation == DEVIATION_PROVISIONAL:
                ratingtotal += self.ratings[ratingtype].elo * 1
                numratings += 1
        return numratings > 0 and ratingtotal / numratings or 0
    
    # FIXME: this isn't very accurate because of inflated standard ratings
    # and deflated lightning ratings and needs work
    # IDEA: use rank in addition to rating to determine strength
    def getStrength (self):
        if self.ratings.has_key(TYPE_BLITZ) and self.ratings[TYPE_BLITZ].deviation != None and \
           self.ratings[TYPE_BLITZ].deviation not in (DEVIATION_ESTIMATED, DEVIATION_PROVISIONAL):
            return self.ratings[TYPE_BLITZ].elo
        elif self.ratings.has_key(TYPE_LIGHTNING) and self.ratings[TYPE_LIGHTNING].deviation != None and \
           self.ratings[TYPE_LIGHTNING].deviation not in (DEVIATION_ESTIMATED, DEVIATION_PROVISIONAL):
            return self.ratings[TYPE_LIGHTNING].elo
        else:
            return self.getRatingMean()
        
#    def getRatingBySeek (self, seek):
#        # TODO: figure out exactly what to do with unsupported game types
#        assert seek != None
#        gainminutes = seek.inc > 0 and (seek.inc*60)-1 or 0
#        if seek.variant and seek.variant in wildVariants:
#            return self.getRating(TYPE_WILD)           
#        elif seek.variant and seek.variant == LOSERSCHESS:
#            return self.getRating(TYPE_LOSERS)
#        elif seek.variant and seek.variant != NORMALCHESS:
#            raise
#        elif (seek.min*60) + gainminutes >= (15*60):
#            return self.getRating(TYPE_STANDARD)
#        elif (seek.min*60) + gainminutes >= (3*60):
#            return self.getRating(TYPE_BLITZ)
#        else:
#            return self.getRating(TYPE_LIGHTNING)
    
    def getGameRating (self):
        game = self.game
        if game == None: return None
        assert game.variant != None and game.variant in wildVariants + (LOSERSCHESS, NORMALCHESS)
        
        if game.variant == NORMALCHESS:
            if game.min == None or game.inc == None:
                rating = self.getRating(TYPE_BLITZ)
            else:
                gainminutes = game.inc > 0 and (game.inc*60)-1 or 0
                if ((game.min*60) + gainminutes) >= (15*60):
                    rating = self.getRating(TYPE_STANDARD)
                elif ((game.min*60) + gainminutes) >= (3*60):
                    rating = self.getRating(TYPE_BLITZ)
                else:
                    rating = self.getRating(TYPE_LIGHTNING)
        elif game.variant in wildVariants:
            rating = self.getRating(TYPE_WILD)    
        elif game.variant == LOSERSCHESS:
            rating = self.getRating(TYPE_LOSERS)
        
        if rating != None:
            return rating.elo
        else:
            return None
        
#    def addGameRating (self, rating):
#        """ Adds a rating to the player based on the type of the game they're playing
#            Note: self.game has to be set for this to work
#        """
#        game = self.game
#        if game == None or rating == None: return
#        assert game.variant != None and game.variant in wildVariants + (LOSERSCHESS, NORMALCHESS)
#        
#        if game.variant == NORMALCHESS:
#            if game.min == None or game.inc == None:
#                # try the type
#                if game.type == "Blitz":
#                    ratingobj = Rating(TYPE_BLITZ, rating)
#                elif game.type == "Standard":
#                    ratingobj = Rating(TYPE_STANDARD, rating)
#                elif game.type == "Lightning":
#                    ratingobj = Rating(TYPE_LIGHTNING, rating)
#                else:
#                    return
#            else:
#                gainminutes = game.inc > 0 and (game.inc*60)-1 or 0
#                if ((game.min*60) + gainminutes) >= (15*60):
#                    ratingobj = Rating(TYPE_STANDARD, rating)
#                elif ((game.min*60) + gainminutes) >= (3*60):
#                    ratingobj = Rating(TYPE_BLITZ, rating)
#                else:
#                    ratingobj = Rating(TYPE_LIGHTNING, rating)
#        elif game.variant in wildVariants:
#            ratingobj = Rating(TYPE_WILD, rating)
#        elif game.variant == LOSERSCHESS:
#            ratingobj = Rating(TYPE_LOSERS, rating)
#
#        self.setRating(type, ratingobj)

#class Singleton(gobject.GObjectMeta):
#    """ Copied from http://burtonini.com/bzr/shackleton/sources.py
#    And in the class using this class you'd put:
#    __metaclass__ = Singleton
#    """
#    def __init__(klass, name, bases, dict):
#        gobject.GObjectMeta.__init__(klass, name, bases, dict)
#        klass.__instance = None
#
#    def __call__(klass, *args, **kwargs):
#        if klass.__instance is None:
#            klass.__instance = gobject.GObjectMeta.__call__(klass, *args, **kwargs)
#        return klass.__instance

class FICSPlayersOnline (GObject):
    __gsignals__ = {
        'FICSPlayerEntered' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayerChanged' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayerExited' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
            
    def __init__ (self, connection):
        GObject.__init__(self)
        self.players = {}
        self.connection = connection
    
    def start (self):
        self.connection.glm.connect("playerConnected", self.addPlayer)
        self.connection.glm.connect("playerDisconnected", self.delPlayer)
        self.connection.glm.connect("playerWhoI", self.addPlayer)
        self.connection.glm.connect("playerWho", self.addPlayer)
        self.connection.glm.connect("playerUnavailable", self.onPlayerUnavailable)
        self.connection.glm.connect("playerAvailable", self.addPlayer)
        self.connection.gamesinprogress.connect("FICSGameCreated", self.gameCreated)
        self.connection.gamesinprogress.connect("FICSGameEnded", self.gameEnded)

    def __getitem__ (self, player):
        if self.players.has_key(hash(player)):
            return self.players[hash(player)]
        else:
            raise KeyError
    
    def __contains__ (self, player):
        if self.players.has_key(hash(player)):
            return True
        else:
            return False
    
    def __add (self, player):
        if not player in self:
            self.players[hash(player)] = player
        else:
            raise Exception("Player %s already exists in %s" % (repr(player), str(self)))

    def __del (self, player):
        if player in self:
            del self.players[hash(player)]
        
    def addPlayer (self, glm, player):
        log.debug("FICSPlayersOnline.addPlayer():\n")
        if player in self:
            log.debug("\t player updated: " + repr(player) + "\n")
            log.debug("\t old player: " + repr(self[player]) + "\n")
            self[player].update(player)
            log.debug("\t new player: " + repr(self[player]) + "\n")
            self.emit('FICSPlayerChanged', self[player])
        else:
            self.__add(player)
            log.debug("player added: " + repr(self[player]) + "\n")
            self.emit('FICSPlayerEntered', self[player])
        
    def delPlayer (self, glm, player):
        if player in self:
            player = self[player]
            self.__del(player)
            self.emit('FICSPlayerExited', player)
    
    def gameCreated (self, gip, game):
        log.debug("FICSPlayersOnline.gameCreated():\n")
        log.debug("Updating players in game: %s\n" % repr(game))
        for player in (game.wplayer, game.bplayer):
            if player in self:
                log.debug("Updating player: %s\n" % repr(player))
                self[player].status = IC_STATUS_PLAYING
                self[player].game = game
                self.emit('FICSPlayerChanged', self[player])
    
    def gameEnded (self, gip, game):
        for player in (game.wplayer, game.bplayer):
            if player in self:
                if self[player].status == IC_STATUS_PLAYING:
                    self[player].status = IC_STATUS_AVAILABLE
                self[player].game = None
                self.emit('FICSPlayerChanged', self[player])
        
    def onPlayerUnavailable (self, glm, player):
        if player in self:
            if self[player].status == IC_STATUS_AVAILABLE:
                self[player].status = player.status
                self.emit('FICSPlayerChanged', self[player])

class FICSBoard:
    def __init__ (self, wms, bms, fen=None, pgn=None):
        self.wms = wms
        self.bms = bms
        assert fen != None or pgn != None
        self.fen = fen
        self.pgn = pgn
        
class FICSGame:
    def __init__ (self, gameno, wplayer, bplayer, rated=False, variant=NORMALCHESS,
                  type=_("Standard"), min=None, inc=None, private=False, result=None,
                  reason=None, board=None):
        self.gameno = gameno
        self.wplayer = wplayer
        self.bplayer = bplayer
        self.rated = rated
        self.variant = variant
        self.type = type
        self.min = min  # not always set ("game created ..." message doesn't specify)
        self.inc = inc  # not always set ("game created ..." message doesn't specify)
        self.private = private
        self.result = result
        self.reason = reason
        self.board = board
    
#    def getGameType (self):
#        assert self.variant in wildVariants + (LOSERSCHESS, NORMALCHESS)
#
#        if self.variant != NORMALCHESS:
#            return variants[self.variant].name
#        else:
#            gainminutes = self.inc > 0 and (self.inc*60)-1 or 0
#            if self.min == None or self.inc == None:
#                rating = self.getRating(TYPE_BLITZ)
#            elif ((self.game.min*60) + gainminutes) >= (15*60):
#                rating = self.getRating(TYPE_STANDARD)
#            elif ((self.game.min*60) + gainminutes) >= (3*60):
#                rating = self.getRating(TYPE_BLITZ)
#            else:
#                rating = self.getRating(TYPE_LIGHTNING)            
        
    def __eq__ (self, game):
        if type(self) == type(game) and self.gameno == game.gameno \
           and self.wplayer == game.wplayer and self.bplayer == game.bplayer:
            return True
        else:
            return False
    
    def __repr__ (self):
        r = "gameno=%s, wplayer=%s, bplayer=%s" % (self.gameno, repr(self.wplayer), repr(self.bplayer))
        r += self.rated and ", rated=True" or ", rated=False"
        r += ", type=%s" % self.type
        r += self.private and ", private=True" or ", private=False"
        if self.min != None:
            r += ", min=%i" % self.min
        if self.inc != None:
            r += ", inc=%i" % self.inc
        if self.result != None:
            r += ", result=%i" % self.result
        if self.reason != None:
            r += ", reason=%i" % self.reason
        return r

class FICSGamesInProgress (GObject):
    __gsignals__ = {
        'FICSGameCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSGameEnded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayGameCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSPlayGameEnded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSObsGameCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'FICSObsGameEnded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.games = {}
        self.connection = connection

    def start (self):
        self.connection.glm.connect("addGame", self.addGame)
        self.connection.bm.connect("gameCreated", self.gameCreated)
        self.connection.bm.connect("obsGameCreated", self.obsGameCreated)
        self.connection.glm.connect("removeGame", self.removeGame)

    def __getitem__ (self, gameno):
        if self.games.has_key(gameno):
            return self.games[gameno]
        else:
            raise KeyError
    
    def addGame (self, glm, game):
        log.debug("FICSGamesInProgress.addGame():\n")
        log.debug("\t Adding game: %s\n" % repr(game))
        if game.wplayer in self.connection.playersonline:
            log.debug("\t Found wplayer in playersonline: %s\n" \
                      % repr(self.connection.playersonline[game.wplayer]))
            game.wplayer = self.connection.playersonline[game.wplayer]
        else:
            log.debug("\t Adding game.wplayer to playersonline: %s\n" % repr(game.wplayer))
            self.connection.playersonline.addPlayer(glm, game.wplayer)
        if game.bplayer in self.connection.playersonline:
            log.debug("\t Found bplayer in playersonline: %s\n" \
                      % repr(self.connection.playersonline[game.bplayer]))
            game.bplayer = self.connection.playersonline[game.bplayer]
        else:
            log.debug("\t Adding game.bplayer to playersonline: %s\n" % repr(game.bplayer))
            self.connection.playersonline.addPlayer(glm, game.bplayer)
        if not self.games.has_key(game.gameno):
            self.games[game.gameno] = game
            self.emit('FICSGameCreated', game)
    
    def gameCreated (self, glm, game):
        self.addGame(glm, game)
        self.emit('FICSPlayGameCreated', game)
    
    def obsGameCreated (self, glm, game):
        self.addGame(glm, game)
        self.emit('FICSObsGameCreated', game)
        
    def removeGame (self, glm, game):
        if self.games.has_key(game.gameno):
            game = self.games[game.gameno]
            del self.games[game.gameno]
            self.emit('FICSGameEnded', game)

class FICSSeek:
    def __init__ (self, name, min, inc, rated, color, variant, rmin=0, rmax=9999):
        self.seeker = name
        self.min = min
        self.inc = inc
        self.rated = rated
        self.color = color
        self.variant = variant
        self.rmin = rmin  # minimum rating one has to have to accept seek
        self.rmax = rmax  # maximum rating one has to have to accept seek
#
#if __name__ == "main":
#    def