# -*- coding: utf-8 -*-

import datetime
from gi.repository import GObject
#from gobject import GObject, SIGNAL_RUN_FIRST

from pychess.System.Log import log
from pychess.Utils.IconLoader import load_icon
from pychess.Utils.Rating import Rating
from pychess.Utils.const import *
from pychess.ic import *

class FICSRatings (dict):
    def __init__ (self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        
        for ratingtype in RATING_TYPES:
            self[ratingtype] = Rating(ratingtype, 0)
    
    def __setitem__ (self, key, val):
        if key not in RATING_TYPES:
            raise TypeError("bad key: %s %s" % (repr(key), type(key)))
        elif not isinstance(val, Rating):
            raise TypeError("bad val: %s %s" % (repr(val), type(val)))
        dict.__setitem__(self, key, val)

def make_sensitive_if_available (button, player):
    if player.isAvailableForGame():
        button.set_property("sensitive", True)
        button.set_property("tooltip-text", "")
    else:
        button.set_property("sensitive", False)
        button.set_property("tooltip-text", _("%(player)s is %(status)s") % \
            {"player": player.name, "status": player.display_status.lower()})

def make_sensitive_if_playing (button, player):
    status = player.display_status.lower()
    if player.status == IC_STATUS_PLAYING:
        button.set_property("sensitive", True)
    else:
        button.set_property("sensitive", False)
        if player.status != IC_STATUS_OFFLINE:
            status = _("not playing")
    button.set_property("tooltip-text", _("%(player)s is %(status)s") % \
        {"player": player.name, "status": status})

def get_player_tooltip_text (player, show_status=True):
    text = "%s" % player.name
    text += "%s" % player.display_titles(long=True)
    if player.blitz:
        text += "\n%s: %s" % (_("Blitz"), player.blitz)
    if player.standard:
        text += "\n%s: %s" % (_("Standard"), player.standard)
    if player.lightning:
        text += "\n%s: %s" % (_("Lightning"), player.lightning)
    if player.atomic:
        text += "\n%s: %s" % (_("Atomic"), player.atomic)
    if player.bughouse:
        text += "\n%s: %s" % (_("Bughouse"), player.bughouse)
    if player.crazyhouse:
        text += "\n%s: %s" % (_("Crazyhouse"), player.crazyhouse)
    if player.losers:
        text += "\n%s: %s" % (_("Losers"), player.losers)
    if player.suicide:
        text += "\n%s: %s" % (_("Suicide"), player.suicide)
    if player.wild:
        text += "\n%s: %s" % (_("Wild"), player.wild)
    if show_status:
        text += "\n%s" % player.display_status
    return text
        
class FICSPlayer (GObject.GObject):
    def __init__ (self, name, online=False, status=IC_STATUS_UNKNOWN, game=None,
                  titles=None):
        assert type(name) is str, name
        assert type(online) is bool, online
        GObject.GObject.__init__(self)
        self.name = name
        self.online = online
        self._status = status
        self.status = status
        self.game = None
        self.adjournment = False
        self.keep_after_logout = False  # Whether to remove from Players after they logout
        self.ratings = FICSRatings()
        if titles is None:
            self.titles = set()
        else:
            self.titles = titles
    
    def long_name (self, game_type=None):
        name = self.name
        
        if game_type:
            rating = self.getRatingByGameType(game_type)
        else:
            rating = self.getRatingForCurrentGame()
        if rating:
            name += " (%d)" % rating
            
        title = self.display_titles()
        if title:
            name += "%s" % title
        return name
        
    def get_online (self):
        return self._online
    def set_online (self, online):
        self._online = online
    online = GObject.property(get_online, set_online)
    
    @property
    def display_online (self):
        if self.online: return _("Online")
        else: return _("Offline")        
        
    def get_status (self):
        return self._status
    def set_status (self, status):
        self._previous_status = self._status
        self._status = status
    status = GObject.property(get_status, set_status)
    
    def restore_previous_status (self):
        self.status = self._previous_status
        
    @property
    def display_status (self):
        if self.status == IC_STATUS_AVAILABLE:
            return _("Available")
        elif self.status == IC_STATUS_PLAYING:
            status = _("Playing")
            game = self.game
            if game is not None:
                status += " " + game.display_text
            return status
        elif self.status == IC_STATUS_IDLE:
            return _("Idle")
        elif self.status == IC_STATUS_OFFLINE:
            return _("Offline")
        elif self.status == IC_STATUS_EXAMINING:
            return _("Examining")
        elif self.status in (IC_STATUS_NOT_AVAILABLE, IC_STATUS_BUSY):
            return _("Not Available")
        elif self.status == IC_STATUS_RUNNING_SIMUL_MATCH:
            return _("Running Simul Match")
        elif self.status == IC_STATUS_IN_TOURNAMENT:
            return _("In Tournament")
        else:
            return ""
        
    def get_game (self):
        return self._game
    def set_game (self, game):
        if game is not None and not isinstance(game, FICSMatch):
            raise TypeError(type(game))
        self._game = game
    game = GObject.property(get_game, set_game)
        
    def get_titles (self):
        return self._titles
    def set_titles (self, titles):
        self._titles = titles
    titles = GObject.property(get_titles, set_titles)
    
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
        return self.ratings[TYPE_BLITZ].elo

    @property
    def standard (self):
        return self.ratings[TYPE_STANDARD].elo

    @property
    def lightning (self):
        return self.ratings[TYPE_LIGHTNING].elo

    @property
    def atomic (self):
        return self.ratings[TYPE_ATOMIC].elo

    @property
    def bughouse (self):
        return self.ratings[TYPE_BUGHOUSE].elo

    @property
    def crazyhouse (self):
        return self.ratings[TYPE_CRAZYHOUSE].elo

    @property
    def losers (self):
        return self.ratings[TYPE_LOSERS].elo

    @property
    def suicide (self):
        return self.ratings[TYPE_SUICIDE].elo

    @property
    def wild (self):
        return self.ratings[TYPE_WILD].elo

    def __hash__ (self):
        """ Two players are equal if the first 10 characters of their name match.
            This is to facilitate matching players from output of commands like the 'games'
            command which only return the first 10 characters of a player's name """
        return hash(self.name[0:10].lower())
    
    def __eq__ (self, player):
        if type(self) == type(player) and hash(self) == hash(player):
            return True
        else:
            return False
        
    def __repr__ (self):
        r = "name='%s'" % (self.name + self.display_titles())
        r += ", id=%s" % (id(self))
        r += ", online=%s" % repr(self.online)
        r += ", adjournment=%s" % repr(self.adjournment)
        r += ", status=%i" % self.status
        game = self.game
        if game != None:
            r += ", game.gameno=%d" % game.gameno
            r += ", game.rated=%s" % game.rated
            r += ", game.private=" + repr(game.private)
        else:
            r += ", game=None"
        for rating_type in RATING_TYPES:
            if rating_type in self.ratings:
                r += ", %s=%s" % \
                    (GAME_TYPES_BY_RATING_TYPE[rating_type].display_text,
                     repr(self.ratings[rating_type].elo))
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
                rating = self.getRatingByGameType(gametype)
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
                rating = self.getRatingByGameType(gametype)
            else:
                rating = self.getStrength()
            if rating < 1:
                rating = _("Unrated")
            markup += " <big>(%s)</big>" % rating
            
            if self.display_titles() != "":
                markup += "<big>%s</big>" % self.display_titles(long=True)
            
        return markup
    
    def copy (self):
        player = FICSPlayer(self.name, online=self.online, status=self.status,
            titles=self.titles.copy())
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
        for ratingtype in RATING_TYPES:
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
    
    def getRatingByGameType (self, game_type):
        try:
            return self.ratings[game_type.rating_type].elo
        except KeyError:
            return 0
        except AttributeError:
            return 0
    
    def getRatingForCurrentGame (self):
        try:
            return self.getRatingByGameType(self.game.game_type)
        except AttributeError:
            return 0
        
class FICSPlayers (GObject.GObject):
    #__gsignals__ = {
    #    'FICSPlayerEntered' : (SIGNAL_RUN_FIRST, None, (object,)),
    #    'FICSPlayerExited' : (SIGNAL_RUN_FIRST, None, (object,))
    #}
    __gsignals__ = {
        'FICSPlayerEntered' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'FICSPlayerExited' : (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }
    
    def __init__ (self, connection):
        GObject.GObject.__init__(self)
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
        log.debug("%s" % player,
            extra={"task": (self.connection.username, "player_disconnected")})
        if player in self:
            player = self[player]
            player.online = False
            player.status = IC_STATUS_OFFLINE
            if not player.adjournment and not player.keep_after_logout and \
                    player.name not in self.connection.notify_users:
                del self[player]
            else:
                log.debug("Not removing %s" % player, extra={"task":
                    (self.connection.username, "player_disconnected")})
            self.emit('FICSPlayerExited', player)
    
#    def onFinger (self, fm, finger):
#        player = FICSPlayer(finger.getName())
#        if player in self:
#            self[player].finger = finger
#            # TODO: merge ratings and titles from finger object into ficsplayer object

class FICSMatch (GObject.GObject):
    def __init__ (self, minutes, inc, rated, game_type):
        assert minutes is None or type(minutes) is int, type(minutes)
        assert inc is None or type(inc) is int, inc
        assert type(rated) is bool, rated
        assert game_type is None or game_type is GAME_TYPES_BY_FICS_NAME["wild"] \
            or game_type in GAME_TYPES.values(), game_type
        GObject.GObject.__init__(self)
        self.minutes = minutes
        self.inc = inc
        self.rated = rated
        self.game_type = game_type
    
    def __repr__ (self):
        text = "%s %s" % (self.minutes, self.inc)
        text += " %s" % ("rated" if self.rated else "unrated")
        text += " %s" % self.game_type.display_text
        return text

    @property
    def display_rated (self):
        if self.rated: return _("Rated")
        else: return _("Unrated")

    @property
    def display_timecontrol (self):
        t = ""
        if self.minutes is not None:
            t = _("%d min") % self.minutes
        if self.inc is not None and self.inc != 0:
            t += _(" + %d sec") % self.inc
        return t

    @property
    def sortable_time (self):
        gainminutes = (self.inc*60)-1 if self.inc != None and self.inc > 0 else 0
        return self.minutes*60 + gainminutes
    
def get_soughtmatch_tooltip_text (sought):
    text = "%s" % sought.player.name
    text += "%s" % sought.player.display_titles(long=True)
    if not sought.player.isGuest():
        text += " (%d)" % sought.player_rating
    text += "\n%s %s" % (sought.display_rated, sought.game_type.display_text)
    text += "\n" + sought.display_timecontrol
    if sought.color:
        text += "\n" + _("%(player)s plays %(color)s") \
            % {"player": sought.player.name,
               "color": _("white") if sought.color == "white" else _("black")} 
    return text

class FICSSoughtMatch (FICSMatch):
    def __init__ (self, index, player, minutes, inc, rated, color, game_type):
        assert index is None or type(index) is int, index
        assert isinstance(player, FICSPlayer), player
        FICSMatch.__init__(self, minutes, inc, rated, game_type)
        self.index = index
        self.player = player
        self.color = color  # self.player plays color
    
    def __hash__ (self):
        return self.index

    def __eq__ (self, sought):
        if type(self) == type(sought) and hash(self) == hash(sought):
            return True
        else:
            return False
    
    def __ne__ (self, sought):
        return not self == sought
    
    def __repr__ (self):
        text = "%s" % self.index
        text += " %s" % self.player.name
        text += " %s" % FICSMatch.__repr__(self)        
        return text
    
    @property
    def player_rating (self):
        """
        This returns self.player's rating for the type of match being sought.
        If self.player doesn't have a rating for the type of match being
        sought, this returns 0. If the match is untimed we use self.player's
        standard time-control rating if they have one.
        """
        game_type = self.game_type
        if game_type == GAME_TYPES['untimed']:
            game_type = GAME_TYPES['standard']
        return self.player.getRatingByGameType(game_type)
        
def get_challenge_tooltip_text (challenge):
    text = get_soughtmatch_tooltip_text(challenge)
    if challenge.adjourned:
        text += "\n" + _("This is a continuation of an adjourned match")
    return text

class FICSChallenge (FICSSoughtMatch):
    def __init__ (self, index, player, minutes, inc, rated, color, game_type,
                  adjourned=False):
        FICSSoughtMatch.__init__(self, index, player, minutes, inc, rated,
                                 color, game_type)
        self.adjourned = adjourned

class FICSChallenges (GObject.GObject):
    __gsignals__ = {
        'FICSChallengeIssued' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'FICSChallengeRemoved' : (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }
    
    def __init__ (self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
        self.challenges = {}
        
    def start (self):
        self.connection.om.connect("onChallengeAdd", self.onChallengeIssued)
        self.connection.om.connect("onChallengeRemove", self.onChallengeRemoved)
        self.connection.bm.connect("playGameCreated", self.onPlayingGame)
        
    def __getitem__ (self, index):
        if not type(index) == int: raise TypeError
        return self.challenges[index]

    def __setitem__ (self, index, challenge):
        if not type(index) == int: raise TypeError
        if not isinstance(challenge, FICSSoughtMatch): raise TypeError
        if index in self:
            log.warning("FICSChallenges: not overwriting challenge %s" %
                        repr(challenge))
            return
        self.challenges[index] = challenge
        self.emit('FICSChallengeIssued', challenge)
    
    def __delitem__ (self, index):
        if not type(index) == int: raise TypeError
        try:
            challenge = self.challenges[index]
        except KeyError:
            return
        del self.challenges[index]
        self.emit('FICSChallengeRemoved', challenge)
        
    def __contains__ (self, index):
        if not type(index) == int: raise TypeError
        if index in self.challenges:
            return True
        else:
            return False
    
    def clear (self):
        challenges = self.challenges.copy()
        for key in challenges:
            del self[key]
        
    def onChallengeIssued (self, om, challenge):
        self[challenge.index] = challenge
        
    def onChallengeRemoved (self, om, index):
        del self[index]
        
    def onPlayingGame (self, bm, game):
        self.clear()

def get_rating_range_display_text (rmin=0, rmax=9999):
    assert type(rmin) is type(int()) and rmin >= 0 and rmin <= 9999, rmin
    assert type(rmax) is type(int()) and rmax >= 0 and rmax <= 9999, rmax
    if rmin > 0:
        text = "%d" % rmin
        if rmax == 9999:
            text += "↑"
        else:
            text += "-%d" % rmax
    elif rmax != 9999:
        text = "%d↓" % rmax
    else:
        text = None
    return text

def get_seek_tooltip_text (seek):
    text = get_soughtmatch_tooltip_text(seek)
    rrtext = get_rating_range_display_text(seek.rmin, seek.rmax)
    if rrtext:
        text += "\n%s: %s" % (_("Opponent Rating"), rrtext)
    if not seek.automatic:
        text += "\n%s" % _("Manual Accept")
    return text

class FICSSeek (FICSSoughtMatch):
    def __init__ (self, index, player, minutes, inc, rated, color, game_type,
                  rmin=0, rmax=9999, automatic=True, formula=False):
        FICSSoughtMatch.__init__(self, index, player, minutes, inc, rated,
                                 color, game_type)
        self.rmin = rmin  # minimum rating one has to accept this seek
        self.rmax = rmax  # maximum rating one has to accept this seek
        self.automatic = automatic  # if True, auto accept; otherwise, manual accept
        self.formula = formula  # players' formula will be used to screen responses

class FICSSeeks (GObject.GObject):
    __gsignals__ = {
        'FICSSeekCreated' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'FICSSeekRemoved' : (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }
    
    def __init__ (self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
        self.seeks = {}
        
    def start (self):
        self.connection.glm.connect("addSeek", self.onAddSeek)
        self.connection.glm.connect("removeSeek", self.onRemoveSeek)
        self.connection.glm.connect("clearSeeks", self.onClearSeeks)
        self.connection.bm.connect("curGameEnded", self.onCurGameEnded)
    
    def __getitem__ (self, index):
        if not type(index) == int: raise TypeError
        return self.seeks[index]

    def __setitem__ (self, index, seek):
        if not type(index) == int: raise TypeError
        if not isinstance(seek, FICSSoughtMatch): raise TypeError
        if index in self:
            log.warning("FICSSeeks: not overwriting seek %s" % repr(seek))
            return
        self.seeks[index] = seek
        self.emit('FICSSeekCreated', seek)
    
    def __delitem__ (self, index):
        if not type(index) == int: raise TypeError
        try:
            seek = self.seeks[index]
        except KeyError:
            return
        del self.seeks[index]
        self.emit('FICSSeekRemoved', seek)
        
    def __contains__ (self, index):
        if not type(index) == int: raise TypeError
        if index in self.seeks:
            return True
        else:
            return False
    
    def clear (self):        
        seeks = self.seeks.copy()
        for key in seeks:
            del self[key]
        
    def onAddSeek (self, glm, seek):
        self[seek.index] = seek
        
    def onRemoveSeek (self, glm, index):
        del self[index]
    
    def onClearSeeks (self, glm):
        self.clear()
        
    def onCurGameEnded (self, bm, game):
        self.connection.glm.refresh_seeks()
    
class FICSBoard (object):
    def __init__ (self, wms, bms, fen=None, pgn=None):
        assert type(wms) is int, wms
        assert type(bms) is int, bms
        self.wms = wms
        self.bms = bms
#        assert fen != None or pgn != None
        self.fen = fen
        self.pgn = pgn

class FICSGame (FICSMatch):
    def __init__ (self, wplayer, bplayer, gameno=None,
                  game_type=None, rated=False, minutes=None, inc=None, result=None,
                  reason=None, board=None, private=False):
        assert isinstance(wplayer, FICSPlayer), wplayer
        assert isinstance(bplayer, FICSPlayer), bplayer
        assert gameno is None or type(gameno) is int, gameno
        assert result is None or type(result) is int, result
        assert reason is None or type(reason) is int, reason
        assert board is None or isinstance(board, FICSBoard), board
        assert type(private) is bool, private
        FICSMatch.__init__(self, minutes, inc, rated, game_type)
        self.wplayer = wplayer
        self.bplayer = bplayer
        self.gameno = gameno
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
        if self.minutes != None:
            r += ", minutes=%i" % self.minutes
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
    private = GObject.property(get_private, set_private)
        
    @property
    def display_text (self):
        text = ""
        gametype = self.game_type
        if gametype is not None:
            text += gametype.display_text
            if self.private:
                text += " (" + _("Private") + ")"
        return text
    
    def update (self, game):
        if self.rated != game.rated:
            self.rated = game.rated
        if self.private != game.private:
            self.private = game.private
        if game.minutes is not None and self.minutes != game.minutes:
            self.minutes = game.minutes
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
    def __init__ (self, wplayer, bplayer, our_color=None, length=None, time=None,
                  rated=False, game_type=None, private=False, minutes=None,
                  inc=None, result=None, reason=None, board=None):
        assert our_color is None or our_color in (WHITE, BLACK), our_color
        assert length is None or type(length) is int, length
        assert time is None or type(time) is datetime.datetime, time        
        FICSGame.__init__(self, wplayer, bplayer, rated=rated, private=private,
            game_type=game_type, minutes=minutes, inc=inc, result=result,
            reason=reason, board=board)
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

class FICSGames (GObject.GObject):
    __gsignals__ = {
        'FICSGameCreated' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'FICSGameEnded' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'FICSAdjournedGameRemoved' : (GObject.SignalFlags.RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.GObject.__init__(self)
        self.games = {}
        self.games_by_gameno = {}
        self.adjourned_games = {}
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
        if isinstance(value, FICSAdjournedGame):        
            self.adjourned_games[hash(value)] = value
            
    def __delitem__ (self, game):
        if not isinstance(game, FICSGame): raise TypeError, (repr(game), type(game))
        if game in self:
            del self.games[hash(game)]
        if game.gameno in self.games_by_gameno:
            del self.games_by_gameno[game.gameno]
        if game in self.adjourned_games:
            del self.adjourned_games[hash(game)]
            
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
        return self.games_by_gameno[gameno]
    
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
        for game in self.adjourned_games.values():
            if game not in adjournments:
                del self[game]
                game.opponent.adjournment = False
                self.emit("FICSAdjournedGameRemoved", game)
    
    def onCurGameEnded (self, bm, game):
        for adjourned_game in self.adjourned_games.values():
            for player in (game.wplayer, game.bplayer):
                if player == adjourned_game.opponent:
                    del self[adjourned_game]
                    adjourned_game.opponent.adjournment = False
                    self.emit("FICSAdjournedGameRemoved", adjourned_game)
