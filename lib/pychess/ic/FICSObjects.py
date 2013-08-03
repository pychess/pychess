import datetime
import gobject
from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.Utils.IconLoader import load_icon
from pychess.Utils.Rating import Rating
from pychess.Utils.const import *
from pychess.ic import TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING, TYPE_WILD, \
    TYPE_LOSERS, TITLE_TYPE_DISPLAY_TEXTS, TITLE_TYPE_DISPLAY_TEXTS_SHORT, \
    GAME_TYPES_BY_RATING_TYPE, TYPE_UNREGISTERED, TYPE_COMPUTER, TYPE_ADMINISTRATOR, \
    GAME_TYPES_BY_FICS_NAME, GAME_TYPES, TYPE_CRAZYHOUSE

class FICSPlayer (GObject):
    def __init__ (self, name, online=False, status=IC_STATUS_OFFLINE,
                  game=None, titles=None, ratings=None):
        assert type(name) is str, name
        assert type(online) is bool, online
        GObject.__init__(self)
        self.name = name
        self.online = online
        self._status = status
        self.status = status
        self.game = None
        self.adjournment = False
        if titles is None:
            self.titles = set()
        else:
            self.titles = titles
        if ratings is None:
            self.ratings = {}
            for ratingtype in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING,
                               TYPE_WILD, TYPE_CRAZYHOUSE, TYPE_LOSERS):
                ratingobj = Rating(ratingtype, 0)
                self.setRating(ratingtype, ratingobj)
        else:
            self.ratings = ratings
    
    def long_name (self, game_type=None):
        name = self.name
        
        if game_type is None:
            rating = self.getRatingForCurrentGame()
        else:
            rating = self.getRating(game_type.rating_type)
            if rating is not None:
                rating = rating.elo
        if rating:
            name += " (%d)" % rating
            
        title = self.display_titles()
        if title:
            name += " %s" % title
        return name
        
    def get_online (self):
        return self._online
    def set_online (self, online):
        self._online = online
    online = gobject.property(get_online, set_online)
    
    @property
    def display_online (self):
        if self.online: return _("Online")
        else: return _("Offline")        
        
    def get_status (self):
        return self._status
    def set_status (self, status):
        self._previous_status = self._status
        self._status = status
    status = gobject.property(get_status, set_status)
    
    def restore_previous_status (self):
        self.status = self._previous_status
        
    @property
    def display_status (self):
        status = ""
        if self.status == IC_STATUS_AVAILABLE:
            status = _("Available")
        elif self.status == IC_STATUS_PLAYING:
            status = _("Playing")
            game = self.game
            if game is not None:
                status += " " + game.display_text
        elif self.status == IC_STATUS_IDLE:
            status = _("Idle")
        elif self.status == IC_STATUS_EXAMINING:
            status = _("Examining")
        elif self.status in (IC_STATUS_NOT_AVAILABLE, IC_STATUS_BUSY):
            status = _("Not Available")
        elif self.status == IC_STATUS_RUNNING_SIMUL_MATCH:
            status = _("Running Simul Match")
        elif self.status == IC_STATUS_IN_TOURNAMENT:
            status = _("In Tournament")
#        log.debug("display_status: returning \"%s\" for %s\n" % (status, self))
        return status
        
    def get_game (self):
        return self._game
    def set_game (self, game):
        self._game = game
    game = gobject.property(get_game, set_game)
        
    def get_titles (self):
        return self._titles
    def set_titles (self, titles):
        self._titles = titles
    titles = gobject.property(get_titles, set_titles)
    
    def display_titles (self, long=False):
        r = ""
        for title in self.titles:
            if long:
                r += " (" + TITLE_TYPE_DISPLAY_TEXTS[title] + ")"
            else:
                r += " (" + TITLE_TYPE_DISPLAY_TEXTS_SHORT[title] + ")"
        return r

    @property
    def blitz (self):
        return self.getRating(TYPE_BLITZ).elo

    @property
    def standard (self):
        return self.getRating(TYPE_STANDARD).elo

    @property
    def lightning (self):
        return self.getRating(TYPE_LIGHTNING).elo

    @property
    def wild (self):
        return self.getRating(TYPE_WILD).elo

    @property
    def crazyhouse (self):
        return self.getRating(TYPE_CRAZYHOUSE).elo

    @property
    def losers (self):
        return self.getRating(TYPE_LOSERS).elo
        
    def __hash__ (self):
        """ Two players are equal if the first 10 characters of their name match.
            This is to facilitate matching players from output of commands like the 'game'
            command which only return the first 10 characters of a player's name """
        return hash(self.name[0:10].lower())
    
    def __eq__ (self, player):
        if type(self) == type(player) and hash(self) == hash(player):
            return True
        else:
            return False
        
    def __repr__ (self):
        r = "name='%s'" % (self.name + self.display_titles())
        r += ", online=%s" % repr(self.online)
        r += ", adjournment=%s" % repr(self.adjournment)
        r += ", status=%i" % self.status
        game = self.game
        if game != None:
            r += ", game.gameno=%d" % game.gameno
            r += ", game.private=" + repr(game.private)
        else:
            r += ", game=None"
        for rating_type in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING,
                            TYPE_WILD, TYPE_CRAZYHOUSE, TYPE_LOSERS):
            if rating_type in self.ratings:
                r += ", ratings[%s] = (" % \
                    GAME_TYPES_BY_RATING_TYPE[rating_type].display_text
                r +=  self.ratings[rating_type].__repr__() + ")"
        return "<FICSPlayer " + r + ">"
    
    def isAvailableForGame (self):    
        if self.status in \
            (IC_STATUS_PLAYING, IC_STATUS_BUSY, IC_STATUS_OFFLINE,
             IC_STATUS_RUNNING_SIMUL_MATCH, IC_STATUS_NOT_AVAILABLE,
             IC_STATUS_EXAMINING, IC_STATUS_IN_TOURNAMENT):
            return False
        else: return True
    
    def isObservable (self):
        return self.status in (IC_STATUS_PLAYING, IC_STATUS_EXAMINING) and \
               self.game is not None and not self.game.private and self.game.supported
        
    def isGuest (self):
        return TYPE_UNREGISTERED in self.titles

    def isComputer (self):    
        return TYPE_COMPUTER in self.titles

    def isAdmin (self):    
        return TYPE_ADMINISTRATOR in self.titles

    @classmethod
    def getIconByRating (cls, rating, size=16):
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
    
    def getIcon (self, size=16, gametype=None):
        assert type(size) == int, "size not an int: %s" % str(size)
        if self.isGuest():
            return load_icon(size, "stock_people", "system-users")
        elif self.isComputer():
            return load_icon(size, "computer", "stock_notebook")
        elif self.isAdmin():
            return load_icon(size, "security-high", "stock_book_blue")
        else:
            if gametype:
                rating = self.getRating(gametype.rating_type)
                rating = rating.elo if rating is not None else 0
            else:
                rating = self.getStrength()
            return self.getIconByRating(rating, size)
    
    def getMarkup (self, gametype=None):
        markup = "<big><b>%s</b></big>" % self.name
        if self.isGuest():
            markup += " <big>(%s)</big>" % \
                TITLE_TYPE_DISPLAY_TEXTS[TYPE_UNREGISTERED]
        else:
            if gametype:
                rating = self.getRating(gametype.rating_type)
                rating = rating.elo if rating is not None else 0
            else:
                rating = self.getStrength()
            if rating < 1:
                rating = _("Unrated")
            markup += " <big>(%s)</big>" % rating
            
            if self.display_titles() != "":
                markup += "<big>%s</big>" % self.display_titles(long=True)
            
        return markup

    def getRating (self, rating_type):
        if rating_type in self.ratings:
            return self.ratings[rating_type]
        else:
            return None
        
    def setRating (self, rating_type, ratingobj):
        self.ratings[rating_type] = ratingobj
        
    def addRating (self, rating_type, rating):
        if rating == None: return
        ratingobj = Rating(rating_type, rating)
        self.ratings[rating_type] = ratingobj
    
    def copy (self):
        player = FICSPlayer(self.name, online=self.online, status=self.status,
            titles=self.titles.copy(), ratings={})
        for ratingtype, rating in self.ratings.iteritems():
            player.ratings[ratingtype] = rating.copy()
        player.game = self.game
        player.adjournment = self.adjournment
        return player
        
    def update (self, player):
        if not isinstance(player, FICSPlayer): raise TypeError
        if self.game != player.game:
            self.game = player.game
        if self.adjournment != player.adjournment:
            self.adjournment = player.adjournment
        if not self.titles >= player.titles:
            self.titles |= player.titles
        for ratingtype in (TYPE_BLITZ, TYPE_STANDARD, TYPE_LIGHTNING,
                           TYPE_WILD, TYPE_CRAZYHOUSE, TYPE_LOSERS):
            self.ratings[ratingtype].update(player.ratings[ratingtype])
        if self.status != player.status:
            self.status = player.status
        # do last so rating info is there when notifications are generated
        if self.online != player.online:
            self.online = player.online
        
    def getRatingMean (self):
        ratingtotal = 0
        numratings = 0
        for ratingtype in self.ratings:
            if self.ratings[ratingtype].elo == 0: continue
            if self.ratings[ratingtype].deviation == DEVIATION_NONE:
                ratingtotal += self.ratings[ratingtype].elo * 3
                numratings += 3
            elif self.ratings[ratingtype].deviation == DEVIATION_ESTIMATED:
                ratingtotal += self.ratings[ratingtype].elo * 2
                numratings += 2
            elif self.ratings[ratingtype].deviation == DEVIATION_PROVISIONAL:
                ratingtotal += self.ratings[ratingtype].elo * 1
                numratings += 1
        return numratings > 0 and ratingtotal / numratings or 0
    
    # FIXME: this isn't very accurate because of inflated standard ratings
    # and deflated lightning ratings and needs work
    # IDEA: use rank in addition to rating to determine strength
    def getStrength (self):
        if TYPE_BLITZ in self.ratings and \
                self.ratings[TYPE_BLITZ].deviation == DEVIATION_NONE:
            return self.ratings[TYPE_BLITZ].elo
        elif TYPE_LIGHTNING in self.ratings and \
                self.ratings[TYPE_LIGHTNING].deviation == DEVIATION_NONE:
            return self.ratings[TYPE_LIGHTNING].elo
        else:
            return self.getRatingMean()
    
    def getRatingForCurrentGame (self):
        """
        Note: This will not work for adjourned or history games since
        player.game is not set in those cases
        """
        if self.game == None: return None
        rating = self.getRating(self.game.game_type.rating_type)
        if rating != None:
            return rating.elo
        else:
            return None

class FICSPlayers (GObject):
    __gsignals__ = {
        'FICSPlayerEntered' : (SIGNAL_RUN_FIRST, None, (object,)),
        'FICSPlayerExited' : (SIGNAL_RUN_FIRST, None, (object,))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.players = {}
        self.players_cids = {}
        self.connection = connection
    
    def start (self):
#        self.connection.fm.connect("fingeringFinished", self.onFinger)
        pass

    def __getitem__ (self, player):
        if type(player) is not FICSPlayer: raise TypeError("%s" % repr(player))
        if hash(player) in self.players:
            return self.players[hash(player)]
        else:
            raise KeyError

    def __setitem__ (self, key, value):
        """ key and value must be the same FICSPlayer object """
        if type(key) is not FICSPlayer: raise TypeError
        if type(value) is not FICSPlayer: raise TypeError
        if key != value:
            raise Exception("Not the same: %s %s" % (repr(key), repr(value)))
        if hash(value) in self.players:
            raise Exception("%s already exists in %s" % (repr(value), repr(self)))
        self.players[hash(value)] = value
        self.players_cids[hash(value)] = value.connect("notify::online",
                                                       self.online_changed)
    
    def __delitem__ (self, player):
        if type(player) is not FICSPlayer: raise TypeError
        if player in self:
            del self.players[hash(player)]
        if hash(player) in self.players_cids:
            if player.handler_is_connected(self.players_cids[hash(player)]):
                player.disconnect(self.players_cids[hash(player)])
            del self.players_cids[hash(player)]
            
    def __contains__ (self, player):
        if type(player) is not FICSPlayer: raise TypeError
        if hash(player) in self.players:
            return True
        else:
            return False
    
    def keys(self): return self.players.keys()
    def items(self): return self.players.items()
    def values(self): return self.players.values()
    
    def online_changed (self, player, property):
        if player.online:
            self.emit("FICSPlayerEntered", player)
    
    # This method is a temporary hack until ChatWindow/ChatManager are
    # converted to use FICSPlayer references rather than player's names
    def get_online_playernames (self):
        names = []
        for player in self.values():
            if player.online:
                names.append(player.name)
        return names

    def get (self, player, create=True):
        # TODO: lock
        if player in self:
            player = self[player]
        elif create:
            self[player] = player
        else:
            raise KeyError
        return player
        
    def player_disconnected (self, player):
        if player in self:
            player = self[player]
            if player.adjournment:
                player.online = False
                player.status = IC_STATUS_OFFLINE
            else:
                del self[player]
            self.emit('FICSPlayerExited', player)
    
#    def onFinger (self, fm, finger):
#        player = FICSPlayer(finger.getName())
#        if player in self:
#            self[player].finger = finger
#            # TODO: merge ratings and titles from finger object into ficsplayer object

class FICSBoard:
    def __init__ (self, wms, bms, fen=None, pgn=None):
        assert type(wms) is int, wms
        assert type(bms) is int, bms
        self.wms = wms
        self.bms = bms
#        assert fen != None or pgn != None
        self.fen = fen
        self.pgn = pgn

class FICSGame (GObject):
    def __init__ (self, wplayer, bplayer, gameno=None,
                  game_type=None, rated=False, min=None, inc=None, result=None,
                  reason=None, board=None, private=False):
        assert isinstance(wplayer, FICSPlayer), wplayer
        assert isinstance(bplayer, FICSPlayer), bplayer
        assert gameno is None or type(gameno) is int, gameno
        assert type(rated) is bool, rated
        assert game_type is None or game_type is GAME_TYPES_BY_FICS_NAME["wild"] \
            or game_type in GAME_TYPES.values(), game_type
        assert min is None or type(min) is int, min
        assert inc is None or type(inc) is int, inc
        assert result is None or type(result) is int, result
        assert reason is None or type(reason) is int, reason
        assert board is None or isinstance(board, FICSBoard), board
        assert type(private) is bool, private
        GObject.__init__(self)
        self.wplayer = wplayer
        self.bplayer = bplayer
        self.gameno = gameno
        self.rated = rated
        self.game_type = game_type
        self.min = min  # not always set ("game created ..." message doesn't specify)
        self.inc = inc  # not always set ("game created ..." message doesn't specify)
        self.result = result
        self.reason = reason
        self.board = board
        self.private = private
    
    def __hash__ (self):
        return hash(":".join((self.wplayer.name[0:10].lower(),
            self.bplayer.name[0:10].lower(), str(self.gameno))))
    
    def __eq__ (self, game):
        if isinstance(game, FICSGame) and hash(self) == hash(game):
            return True
        else:
            return False
    
    def __repr__ (self):
        r = "<FICSGame wplayer=%s, bplayer=%s" % \
            (repr(self.wplayer), repr(self.bplayer))
        if self.gameno is not None:
            r += ", gameno=%d" % self.gameno
        r += ", game_type=%s" % self.game_type
        r += self.rated and ", rated=True" or ", rated=False"
        if self.min != None:
            r += ", min=%i" % self.min
        if self.inc != None:
            r += ", inc=%i" % self.inc
        if self.result != None:
            r += ", result=%i" % self.result
        if self.reason != None:
            r += ", reason=%i" % self.reason
        r += ", private=%s>" % repr(self.private)
        return r
        
    def get_private (self):
        return self._private
    def set_private (self, private):
        self._private = private
    private = gobject.property(get_private, set_private)
 
    @property
    def display_rated (self):
        if self.rated: return _("Rated")
        else: return _("Unrated")
        
    @property
    def display_text (self):
        text = ""
        gametype = self.game_type
        if gametype is not None:
            text += gametype.display_text
            if self.private:
                text += " (" + _("Private") + ")"
        return text
    
    @property
    def display_timecontrol (self):
        t = ""
        if self.min is not None:
            t = _("%d min") % self.min
        if self.inc is not None and self.inc != 0:
            t += _(" + %d sec") % self.inc
        return t
    
    def update (self, game):
        if self.rated != game.rated:
            self.rated = game.rated
        if self.private != game.private:
            self.private = game.private
        if game.min is not None and self.min != game.min:
            self.min = game.min
        if game.inc is not None and self.inc != game.inc:
            self.inc = game.inc
        if game.game_type is not None and \
                self.game_type != game.game_type and not \
                (self.game_type is not None and \
                 game.game_type is GAME_TYPES_BY_FICS_NAME["wild"]):
            self.game_type = game.game_type
        if game.result is not None and self.result != game.result:
            self.result = game.result
        if game.reason is not None and self.reason != game.reason:
            self.reason = game.reason
        if game.board is not None and self.board != game.board:
            self.board = game.board
    
    @property
    def supported(self):
        if self.game_type is GAME_TYPES_BY_FICS_NAME["wild"]:
            return True
        elif self.game_type is not None and self.game_type.fics_name in GAME_TYPES:
            return not GAME_TYPES[self.game_type.fics_name].variant_type in UNSUPPORTED
        else:
            return False


class FICSAdjournedGame (FICSGame):
    def __init__ (self, wplayer, bplayer, our_color=None,
                  length=None, time=None, rated=False, game_type=None,
                  private=False, min=None, inc=None, result=None, reason=None,
                  board=None):
        assert our_color is None or our_color in (WHITE, BLACK), our_color
        assert length is None or type(length) is int, length
        assert time is None or type(time) is datetime.datetime, time        
        FICSGame.__init__(self, wplayer, bplayer, rated=rated, private=private,
            game_type=game_type, min=min, inc=inc, result=result, reason=reason,
            board=board)
        self.our_color = our_color
        self.length = length
        self.time = time
        
    def __repr__ (self):
        s = FICSGame.__repr__(self)[0:-1]
        s = s.replace("<FICSGame", "<FICSAdjournedGame")
        if self.our_color != None:
            s += ", our_color=%i" % self.our_color
        if self.length != None:
            s += ", length=%i" % self.length
        if self.time != None:
            s += ", time=%s" % self.display_time
        return s + ">"
    
    @property
    def display_time (self):
        if self.time is not None:
            return self.time.strftime("%x %H:%M")
    
    @property
    def opponent (self):
        if self.our_color == WHITE:
            return self.bplayer
        elif self.our_color == BLACK:
            return self.wplayer

class FICSGames (GObject):
    __gsignals__ = {
        'FICSGameCreated' : (SIGNAL_RUN_FIRST, None, (object,)),
        'FICSGameEnded' : (SIGNAL_RUN_FIRST, None, (object,)),
        'FICSAdjournedGameRemoved' : (SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.games = {}
        self.games_by_gameno = {}
        self.connection = connection

    def start (self):
        self.connection.adm.connect("onAdjournmentsList", self.onAdjournmentsList)
        self.connection.bm.connect("curGameEnded", self.onCurGameEnded)
    
    def __getitem__ (self, game):
        if not isinstance(game, FICSGame):
            raise TypeError("Not a FICSGame: %s" % repr(game))
        if hash(game) in self.games:
            return self.games[hash(game)]
        else:
            raise KeyError

    def __setitem__ (self, key, value):
        """ key and value must be the same game """
        if not isinstance(key, FICSGame): raise TypeError
        if not isinstance(value, FICSGame): raise TypeError
        if key != value:
            raise Exception("Not the same: %s %s" % (repr(key), repr(value)))
        if hash(value) in self.games:
            raise Exception("%s already exists in %s" % (repr(value), repr(self)))
        self.games[hash(value)] = value
        self.games_by_gameno[value.gameno] = value
        
    def __delitem__ (self, game):
        if not isinstance(game, FICSGame): raise TypeError
        if game in self:
            del self.games[hash(game)]
        if game.gameno in self.games_by_gameno:
            del self.games_by_gameno[game.gameno]
        
    def __contains__ (self, game):
        if not isinstance(game, FICSGame): raise TypeError
        if hash(game) in self.games:
            return True
        else:
            return False
    
    def keys(self): return self.games.keys()
    def items(self): return self.games.items()
    def values(self): return self.games.values()
    
    def get_game_by_gameno (self, gameno):
        if type(gameno) is not int: raise TypeError
        return self.games_by_gameno.get(gameno)
    
    def get (self, game, create=True, emit=True):
        # TODO: lock
        if game in self:
            self[game].update(game)
            game = self[game]
        elif create:
            self[game] = game
            if emit:
                self.emit("FICSGameCreated", game)
        else:
            raise KeyError
        return game
    
    def game_ended (self, game):
        if game in self:
            game = self[game]
            del self[game]
            self.emit("FICSGameEnded", game)
    
    def onAdjournmentsList (self, adm, adjournments):
        for game in self.values():
            if isinstance(game, FICSAdjournedGame):
                if game not in adjournments:
                    del self[game]
                    game.opponent.adjournment = False
                    self.emit("FICSAdjournedGameRemoved", game)
    
    def onCurGameEnded (self, bm, game):
        for _game in self.values():
            if isinstance(_game, FICSAdjournedGame):
                for player in (game.wplayer, game.bplayer):
                    if player == _game.opponent:
                        del self[_game]
                        _game.opponent.adjournment = False
                        self.emit("FICSAdjournedGameRemoved", _game)
    
class FICSSeek:
    def __init__ (self, name, min, inc, rated, color, game_type, rmin=0, rmax=9999):
        assert game_type in GAME_TYPES, game_type
        self.seeker = name
        self.min = min
        self.inc = inc
        self.rated = rated
        self.color = color
        self.game_type = game_type
        self.rmin = rmin  # minimum rating one has to have to be offered this seek
        self.rmax = rmax  # maximum rating one has to have to be offered this seek
