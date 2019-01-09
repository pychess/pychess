# -*- coding: utf-8 -*-
import asyncio
import datetime
from gi.repository import GLib, GObject

from pychess.compat import create_task
from pychess.System.Log import log
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.Utils.const import ADJOURNED, WHITE, BLACK, UNSUPPORTED

from pychess.ic import RATING_TYPES, IC_STATUS_PLAYING, IC_STATUS_OFFLINE, IC_STATUS_UNKNOWN, \
    IC_STATUS_AVAILABLE, IC_STATUS_IDLE, IC_STATUS_EXAMINING, IC_STATUS_NOT_AVAILABLE, \
    IC_STATUS_BUSY, IC_STATUS_RUNNING_SIMUL_MATCH, IC_STATUS_IN_TOURNAMENT, \
    TITLE_TYPE_DISPLAY_TEXTS, TITLE_TYPE_DISPLAY_TEXTS_SHORT, TYPE_BLITZ, TYPE_STANDARD, \
    TYPE_ATOMIC, TYPE_LIGHTNING, TYPE_BUGHOUSE, TYPE_CRAZYHOUSE, TYPE_LOSERS, TYPE_SUICIDE, \
    TYPE_WILD, GAME_TYPES_BY_RATING_TYPE, TYPE_UNREGISTERED, TYPE_COMPUTER, TYPE_ADMINISTRATOR, \
    DEVIATION_NONE, DEVIATION_ESTIMATED, DEVIATION_PROVISIONAL, GAME_TYPES_BY_FICS_NAME, \
    GAME_TYPES, TYPE_GRAND_MASTER, TYPE_INTERNATIONAL_MASTER, TYPE_FIDE_MASTER, \
    TYPE_WOMAN_GRAND_MASTER, TYPE_WOMAN_INTERNATIONAL_MASTER, TYPE_WOMAN_FIDE_MASTER


class AlreadyExistException(Exception):
    pass


def make_sensitive_if_available(button, player):
    if player.isAvailableForGame():
        button.set_property("sensitive", True)
        button.set_property("tooltip-text", "")
    else:
        button.set_property("sensitive", False)
        button.set_property("tooltip-text", _("%(player)s is %(status)s") %
                            {"player": player.name, "status": player.display_status.lower()})


def make_sensitive_if_playing(button, player):
    status = player.display_status.lower()
    if player.status == IC_STATUS_PLAYING:
        button.set_property("sensitive", True)
    else:
        button.set_property("sensitive", False)
        if player.status != IC_STATUS_OFFLINE:
            status = _("not playing")
    button.set_property("tooltip-text", _("%(player)s is %(status)s") %
                        {"player": player.name, "status": status})


def get_player_tooltip_text(player, show_status=True):
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


def player_id(name):
    """ Two players are equal if the first 11 characters of their name match.
        This is to facilitate matching players from output of commands like the 'games'
        command which only return the first 11 characters of a player's name """
    return name[0:11].lower()


class FICSPlayer(GObject.GObject):
    __gsignals__ = {'ratings_changed': (GObject.SignalFlags.RUN_FIRST, None, (int, object))}

    def __init__(self,
                 name,
                 online=False,
                 status=IC_STATUS_UNKNOWN,
                 game=None,
                 titles=None):
        assert isinstance(name, str), name
        assert isinstance(online, bool), online
        GObject.GObject.__init__(self)
        self.player_id = player_id(name)
        self.name = name
        self.online = online
        self._status = status
        self.status = status
        self.game = None
        self.adjournment = False
        self.ratings = [0 for ratingtype in RATING_TYPES]
        self.deviations = [DEVIATION_NONE for ratingtype in RATING_TYPES]
        if titles is None:
            self.titles = set()
        else:
            self.titles = titles

    def long_name(self, game_type=None):
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

    def get_online(self):
        return self._online

    def set_online(self, online):
        self._online = online

    online = GObject.property(get_online, set_online)

    @property
    def display_online(self):
        if self.online:
            return _("Online")
        else:
            return _("Offline")

    def get_status(self):
        return self._status

    def set_status(self, status):
        self._previous_status = self._status
        self._status = status
    status = GObject.property(get_status, set_status)

    def restore_previous_status(self):
        self.status = self._previous_status

    @property
    def display_status(self):
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

    def get_game(self):
        return self._game

    def set_game(self, game):
        if game is not None and not isinstance(game, FICSMatch):
            raise TypeError(type(game))
        self._game = game

    game = GObject.property(get_game, set_game)

    def get_titles(self):
        return self._titles

    def set_titles(self, titles):
        self._titles = titles

    titles = GObject.property(get_titles, set_titles)

    def display_titles(self, long=False):
        title = ""
        for item in self.titles:
            if long:
                title += " (" + TITLE_TYPE_DISPLAY_TEXTS[item] + ")"
            else:
                title += " (" + TITLE_TYPE_DISPLAY_TEXTS_SHORT[item] + ")"
        return title

    @property
    def blitz(self):
        return self.ratings[TYPE_BLITZ]

    @property
    def standard(self):
        return self.ratings[TYPE_STANDARD]

    @property
    def lightning(self):
        return self.ratings[TYPE_LIGHTNING]

    @property
    def atomic(self):
        return self.ratings[TYPE_ATOMIC]

    @property
    def bughouse(self):
        return self.ratings[TYPE_BUGHOUSE]

    @property
    def crazyhouse(self):
        return self.ratings[TYPE_CRAZYHOUSE]

    @property
    def losers(self):
        return self.ratings[TYPE_LOSERS]

    @property
    def suicide(self):
        return self.ratings[TYPE_SUICIDE]

    @property
    def wild(self):
        return self.ratings[TYPE_WILD]

    def __eq__(self, player):
        if isinstance(self, type(player)) and self.player_id == player.player_id:
            return True
        else:
            return False

    def __hash__(self):
        return hash(self.player_id)

    def __repr__(self):
        rep = "name='%s'" % (self.name + self.display_titles())
        rep += ", id=%s" % (id(self))
        rep += ", online=%s" % repr(self.online)
        rep += ", adjournment=%s" % repr(self.adjournment)
        rep += ", status=%i" % self.status
        game = self.game
        if game is not None:
            rep += ", game.gameno=%d" % game.gameno
            rep += ", game.rated=%s" % game.rated
            rep += ", game.private=" + repr(game.private)
        else:
            rep += ", game=None"
        for rating_type in RATING_TYPES:
            if rating_type in self.ratings:
                rep += ", %s=%s" % \
                    (GAME_TYPES_BY_RATING_TYPE[rating_type].display_text,
                     repr(self.ratings[rating_type]))
        return "<FICSPlayer " + rep + ">"

    def isAvailableForGame(self):
        if self.status in \
            (IC_STATUS_PLAYING, IC_STATUS_BUSY, IC_STATUS_OFFLINE,
             IC_STATUS_RUNNING_SIMUL_MATCH, IC_STATUS_NOT_AVAILABLE,
             IC_STATUS_EXAMINING, IC_STATUS_IN_TOURNAMENT):
            return False
        else:
            return True

    def isObservable(self):
        return self.status == IC_STATUS_EXAMINING or \
            (self.status == IC_STATUS_PLAYING and
             self.game is not None and not self.game.private and self.game.supported)

    def isGuest(self):
        return TYPE_UNREGISTERED in self.titles

    def isComputer(self):
        return TYPE_COMPUTER in self.titles

    def isAdmin(self):
        return TYPE_ADMINISTRATOR in self.titles

    def isTitled(self):
        return (
            TYPE_GRAND_MASTER in self.titles) or (
            TYPE_INTERNATIONAL_MASTER in self.titles) or (
            TYPE_FIDE_MASTER in self.titles) or (
            TYPE_WOMAN_GRAND_MASTER in self.titles) or (
            TYPE_WOMAN_INTERNATIONAL_MASTER in self.titles) or (
            TYPE_WOMAN_FIDE_MASTER in self.titles)

    @classmethod
    def getIconByRating(cls, rating, size=16):
        assert isinstance(rating, int), "rating not an int: %s" % str(rating)
        if rating >= 1900:
            return get_pixbuf("glade/16x16/weather-storm.png")
        elif rating >= 1600:
            return get_pixbuf("glade/16x16/weather-showers.png")
        elif rating >= 1300:
            return get_pixbuf("glade/16x16/weather-overcast.png")
        elif rating >= 1000:
            return get_pixbuf("glade/16x16/weather-few-clouds.png")
        else:
            return get_pixbuf("glade/16x16/weather-clear.png")

    def getIcon(self, size=16, gametype=None):
        assert isinstance(size, int), "size not an int: %s" % str(size)
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

    def getMarkup(self, gametype=None, big=True, long_titles=True):
        markup = "<b>%s</b>" % self.name
        if self.isGuest():
            markup += self.display_titles(long=long_titles)
        else:
            if gametype:
                rating = self.getRatingByGameType(gametype)
            else:
                rating = self.getStrength()
            if rating < 1:
                rating = _("Unrated")
            markup += " (%s)" % rating

            if self.display_titles() != "":
                markup += self.display_titles(long=long_titles)

        if big:
            markup = "<big>" + markup + "</big>"

        return markup

    def getRatingMean(self):
        ratingtotal = 0
        numratings = 0
        for ratingtype in RATING_TYPES:
            try:
                if self.ratings[ratingtype] == 0:
                    continue
            except IndexError:
                print(ratingtype, RATING_TYPES, self.ratings)
                continue
            if self.deviations[ratingtype] == DEVIATION_NONE:
                ratingtotal += self.ratings[ratingtype] * 3
                numratings += 3
            elif self.deviations[ratingtype] == DEVIATION_ESTIMATED:
                ratingtotal += self.ratings[ratingtype] * 2
                numratings += 2
            elif self.deviations[ratingtype] == DEVIATION_PROVISIONAL:
                ratingtotal += self.ratings[ratingtype] * 1
                numratings += 1
        return numratings > 0 and ratingtotal // numratings or 0

    # FIXME: this isn't very accurate because of inflated standard ratings
    # and deflated lightning ratings and needs work
    # IDEA: use rank in addition to rating to determine strength
    def getStrength(self):
        if self.deviations[TYPE_BLITZ] == DEVIATION_NONE:
            return self.ratings[TYPE_BLITZ]
        elif self.deviations[TYPE_LIGHTNING] == DEVIATION_NONE:
            return self.ratings[TYPE_LIGHTNING]
        else:
            return self.getRatingMean()

    def getRatingByGameType(self, game_type):
        try:
            return self.ratings[game_type.rating_type]
        except KeyError:
            return 0
        except IndexError:
            return 0

    def getRatingForCurrentGame(self):
        try:
            return self.getRatingByGameType(self.game.game_type)
        except AttributeError:
            return 0


class FICSPlayers(GObject.GObject):
    __gsignals__ = {
        'FICSPlayerEntered': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'FICSPlayerExited': (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.players = {}
        self.players_cids = {}
        self.connection = connection

    def start(self):
        #        self.connection.fm.connect("fingeringFinished", self.onFinger)
        pass

    def __getitem__(self, name):
        if not isinstance(name, str):
            raise TypeError("%s" % name)
        if name in self.players:
            return self.players[name]
        else:
            raise KeyError

    def __setitem__(self, key, value):
        """ key must be str and value must be FICSPlayer object """
        if not isinstance(key, str):
            raise TypeError
        if not isinstance(value, FICSPlayer):
            raise TypeError
        if value.player_id in self.players:
            raise AlreadyExistException

        self.players[value.player_id] = value
        self.players_cids[value.player_id] = value.connect(
            "notify::online", self.online_changed)

    def __delitem__(self, name):
        if not isinstance(name, str):
            raise TypeError
        if name in self.players:
            player = self.players[name]
            if name in self.players_cids:
                if player.handler_is_connected(self.players_cids[name]):
                    player.disconnect(self.players_cids[name])
                del self.players_cids[name]
            del self.players[name]

    def __contains__(self, name):
        if not isinstance(name, str):
            raise TypeError
        if name in self.players:
            return True
        else:
            return False

    def keys(self):
        return self.players.keys()

    def items(self):
        return self.players.items()

    def values(self):
        return self.players.values()

    def online_changed(self, player, prop):
        if player.online:
            GLib.idle_add(self.emit,
                          "FICSPlayerEntered",
                          [player, ],
                          priority=GLib.PRIORITY_LOW)

    # This method is a temporary hack until ChatWindow/ChatManager are
    # converted to use FICSPlayer references rather than player's names
    def get_online_playernames(self):
        names = []
        players = list(self.values())
        for player in players:
            if player.online:
                names.append(player.name)
        return names

    def get(self, name):
        key = player_id(name)
        if key in self:
            player = self[key]
        else:
            player = FICSPlayer(name)
            try:
                self[key] = player
            except AlreadyExistException:
                player = self[key]
        return player

    def player_disconnected(self, name):
        # log.debug("%s" % player,
        #    extra={"task": (self.connection.username, "player_disconnected")})
        key = player_id(name)
        if key in self:
            player = self[key]
            player.online = False
            player.status = IC_STATUS_OFFLINE
            if not player.adjournment and player.name not in self.connection.notify_users:
                del self[player.player_id]
            else:
                log.debug("Not removing %s" % player,
                          extra={"task": (self.connection.username,
                                          "player_disconnected")})
            GLib.idle_add(self.emit,
                          'FICSPlayerExited',
                          player,
                          priority=GLib.PRIORITY_LOW)
        else:
            log.debug("Not removing %s (it's not in FICSPlayers)" % name,
                      extra={"task": (self.connection.username,
                                      "player_disconnected")})
    #    def onFinger (self, fm, finger):
    #        player = player_id(finger.getName())
    #        if player in self:
    #            self[player].finger = finger
    #            # TODO: merge ratings and titles from finger object into ficsplayer object


class FICSMatch(GObject.GObject):
    def __init__(self, minutes, inc, rated, game_type):
        assert minutes is None or isinstance(minutes, int), type(minutes)
        assert inc is None or isinstance(inc, int), inc
        assert isinstance(rated, bool), rated
        assert game_type is None or game_type is GAME_TYPES_BY_FICS_NAME["wild"] \
            or game_type in GAME_TYPES.values(), game_type
        GObject.GObject.__init__(self)
        self.minutes = minutes
        self.inc = inc
        self.rated = rated
        self.game_type = game_type

    def __repr__(self):
        text = "%s %s" % (self.minutes, self.inc)
        text += " %s" % ("rated" if self.rated else "unrated")
        text += " %s" % self.game_type.display_text
        return text

    @property
    def display_rated(self):
        if self.rated:
            return _("Rated")
        else:
            return _("Unrated")

    @property
    def display_timecontrol(self):
        tim = ""
        if self.minutes is not None:
            tim = _("%d min") % self.minutes
        if self.inc is not None and self.inc != 0:
            tim += _(" + %d sec") % self.inc
        return tim

    @property
    def sortable_time(self):
        # http://www.freechess.org/Help/HelpFiles/etime.html
        etime = self.minutes + int(round(self.inc * 2. / 3.))
        return etime


def get_soughtmatch_tooltip_text(sought):
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


class FICSSoughtMatch(FICSMatch):
    def __init__(self, index, player, minutes, inc, rated, color, game_type):
        assert index is None or isinstance(index, int), index
        assert isinstance(player, FICSPlayer), player
        FICSMatch.__init__(self, minutes, inc, rated, game_type)
        self.index = index
        self.player = player
        self.color = color  # self.player plays color

    def __hash__(self):
        return self.index

    def __eq__(self, sought):
        if isinstance(self, type(sought)) and hash(self) == hash(sought):
            return True
        else:
            return False

    def __ne__(self, sought):
        return not self == sought

    def __repr__(self):
        text = "%s" % self.index
        text += " %s" % self.player.name
        text += " %s" % FICSMatch.__repr__(self)
        return text

    @property
    def player_rating(self):
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


def get_challenge_tooltip_text(challenge):
    text = get_soughtmatch_tooltip_text(challenge)
    if challenge.adjourned:
        text += "\n" + _("This is a continuation of an adjourned match")
    return text


class FICSChallenge(FICSSoughtMatch):
    def __init__(self,
                 index,
                 player,
                 minutes,
                 inc,
                 rated,
                 color,
                 game_type,
                 adjourned=False):
        FICSSoughtMatch.__init__(self, index, player, minutes, inc, rated,
                                 color, game_type)
        self.adjourned = adjourned


class FICSChallenges(GObject.GObject):
    __gsignals__ = {
        'FICSChallengeIssued': (GObject.SignalFlags.RUN_FIRST, None,
                                (object, )),
        'FICSChallengeRemoved': (GObject.SignalFlags.RUN_FIRST, None,
                                 (object, ))
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
        self.challenges = {}

    def start(self):
        self.connection.om.connect("onChallengeAdd", self.onChallengeIssued)
        self.connection.om.connect("onChallengeRemove",
                                   self.onChallengeRemoved)
        self.connection.bm.connect("playGameCreated", self.onPlayingGame)

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError
        return self.challenges[index]

    def __setitem__(self, index, challenge):
        if not isinstance(index, int):
            raise TypeError
        if not isinstance(challenge, FICSSoughtMatch):
            raise TypeError
        if index in self:
            log.warning("FICSChallenges: not overwriting challenge %s" %
                        repr(challenge))
            return
        self.challenges[index] = challenge
        self.emit('FICSChallengeIssued', challenge)

    def __delitem__(self, index):
        if not isinstance(index, int):
            raise TypeError
        try:
            challenge = self.challenges[index]
        except KeyError:
            return
        del self.challenges[index]
        self.emit('FICSChallengeRemoved', challenge)

    def __contains__(self, index):
        if not isinstance(index, int):
            raise TypeError
        if index in self.challenges:
            return True
        else:
            return False

    def clear(self):
        challenges = self.challenges.copy()
        for key in challenges:
            del self[key]

    def onChallengeIssued(self, om, challenge):
        self[challenge.index] = challenge

    def onChallengeRemoved(self, om, index):
        del self[index]

    def onPlayingGame(self, bm, game):
        self.clear()


def get_rating_range_display_text(rmin=0, rmax=9999):
    assert isinstance(rmin, type(int())) and rmin >= 0 and rmin <= 9999, rmin
    assert isinstance(rmax, type(int())) and rmax >= 0 and rmax <= 9999, rmax
    if rmin > 0:
        text = "%d" % rmin
        if rmax == 9999:
            text += u"↑"
        else:
            text += "-%d" % rmax
    elif rmax != 9999:
        text = u"%d↓" % rmax
    else:
        text = None
    return text


def get_seek_tooltip_text(seek):
    text = get_soughtmatch_tooltip_text(seek)
    rrtext = get_rating_range_display_text(seek.rmin, seek.rmax)
    if rrtext:
        text += "\n%s: %s" % (_("Opponent Rating"), rrtext)
    if not seek.automatic:
        text += "\n%s" % _("Manual Accept")
    return text


class FICSSeek(FICSSoughtMatch):
    def __init__(self,
                 index,
                 player,
                 minutes,
                 inc,
                 rated,
                 color,
                 game_type,
                 rmin=0,
                 rmax=9999,
                 automatic=True,
                 formula=False):
        FICSSoughtMatch.__init__(self, index, player, minutes, inc, rated,
                                 color, game_type)
        self.rmin = rmin  # minimum rating one has to accept this seek
        self.rmax = rmax  # maximum rating one has to accept this seek
        self.automatic = automatic  # if True, auto accept; otherwise, manual accept
        self.formula = formula  # players' formula will be used to screen responses


class FICSSeeks(GObject.GObject):
    __gsignals__ = {
        'FICSSeekCreated': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'FICSSeekRemoved': (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
        self.seeks = {}

    def start(self):
        self.connection.glm.connect("addSeek", self.onAddSeek)
        self.connection.glm.connect("removeSeek", self.onRemoveSeek)
        self.connection.glm.connect("clearSeeks", self.onClearSeeks)
        self.connection.bm.connect("curGameEnded", self.onCurGameEnded)

    def __getitem__(self, index):
        if not isinstance(index, int):
            raise TypeError
        return self.seeks[index]

    def __setitem__(self, index, seek):
        if not isinstance(index, int):
            raise TypeError
        if not isinstance(seek, FICSSoughtMatch):
            raise TypeError
        if index in self:
            log.warning("FICSSeeks: not overwriting seek %s" % repr(seek))
            return
        self.seeks[index] = seek
        self.emit('FICSSeekCreated', seek)

    def __delitem__(self, index):
        if not isinstance(index, int):
            raise TypeError
        try:
            seek = self.seeks[index]
        except KeyError:
            return
        del self.seeks[index]
        self.emit('FICSSeekRemoved', seek)

    def __contains__(self, index):
        if not isinstance(index, int):
            raise TypeError
        if index in self.seeks:
            return True
        else:
            return False

    def clear(self):
        seeks = self.seeks.copy()
        for key in seeks:
            del self[key]

    def onAddSeek(self, glm, seek):
        self[seek.index] = seek

    def onRemoveSeek(self, glm, index):
        del self[index]

    def onClearSeeks(self, glm):
        self.clear()

    def onCurGameEnded(self, bm, game):
        self.connection.glm.refresh_seeks()


class FICSBoard:
    def __init__(self, wms, bms, fen=None, pgn=None):
        assert isinstance(wms, int), wms
        assert isinstance(bms, int), bms
        self.wms = wms
        self.bms = bms
        #        assert fen != None or pgn != None
        self.fen = fen
        self.pgn = pgn

    def __repr__(self):
        rep = "wms=%s\nbms=%s\npgn=%s" % (self.wms, self.bms, self.pgn)
        return rep


class FICSGame(FICSMatch):
    def __init__(self,
                 wplayer,
                 bplayer,
                 gameno=None,
                 game_type=None,
                 rated=False,
                 minutes=None,
                 inc=None,
                 result=None,
                 reason=None,
                 board=None,
                 private=False,
                 relation=None):
        assert isinstance(wplayer, FICSPlayer), wplayer
        assert isinstance(bplayer, FICSPlayer), bplayer
        assert gameno is None or isinstance(gameno, int), gameno
        assert result is None or isinstance(result, int), result
        assert reason is None or isinstance(reason, int), reason
        assert board is None or isinstance(board, FICSBoard), board
        assert isinstance(private, bool), private
        FICSMatch.__init__(self, minutes, inc, rated, game_type)
        self.wplayer = wplayer
        self.bplayer = bplayer
        self.gameno = gameno
        self.result = result
        self.reason = reason
        self.board = board
        self.private = private
        self.relation = relation

        # move(style12) message queue feeded by BoardManager, consumed by balck and white ICPlayer
        self.move_queue = asyncio.Queue()

    def __hash__(self):
        return hash(":".join((self.wplayer.name[0:11].lower(
        ), self.bplayer.name[0:11].lower(), str(self.gameno))))

    def __eq__(self, game):
        if isinstance(game, FICSGame) and hash(self) == hash(game):
            return True
        else:
            return False

    def __repr__(self):
        rep = "<FICSGame wplayer=%s, bplayer=%s" % \
            (repr(self.wplayer), repr(self.bplayer))
        if self.gameno is not None:
            rep += ", gameno=%d" % self.gameno
        rep += ", game_type=%s" % self.game_type
        rep += self.rated and ", rated=True" or ", rated=False"
        if self.minutes is not None:
            rep += ", minutes=%i" % self.minutes
        if self.inc is not None:
            rep += ", inc=%i" % self.inc
        if self.result is not None:
            rep += ", result=%i" % self.result
        if self.reason is not None:
            rep += ", reason=%i" % self.reason
        rep += ", private=%s>" % repr(self.private)
        return rep

    def get_private(self):
        return self._private

    def set_private(self, private):
        self._private = private

    private = GObject.property(get_private, set_private)

    @property
    def display_text(self):
        text = ""
        gametype = self.game_type
        if gametype is not None:
            text += gametype.display_text
            if self.private:
                text += " (" + _("Private") + ")"
        return text

    def update(self, game):
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
                (self.game_type is not None and
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
            return not GAME_TYPES[
                self.game_type.fics_name].variant_type in UNSUPPORTED
        else:
            return False


class FICSAdjournedGame(FICSGame):
    def __init__(self,
                 wplayer,
                 bplayer,
                 our_color=None,
                 length=None,
                 time=None,
                 rated=False,
                 game_type=None,
                 private=False,
                 minutes=None,
                 inc=None,
                 result=ADJOURNED,
                 reason=None,
                 board=None,
                 relation=None,
                 gameno=None):
        assert our_color is None or our_color in (WHITE, BLACK), our_color
        assert length is None or isinstance(length, int), length
        assert time is None or isinstance(time, datetime.datetime), time
        FICSGame.__init__(self,
                          wplayer,
                          bplayer,
                          rated=rated,
                          private=private,
                          game_type=game_type,
                          minutes=minutes,
                          inc=inc,
                          result=result,
                          reason=reason,
                          board=board,
                          relation=relation,
                          gameno=gameno)
        self.our_color = our_color
        self.length = length
        self.time = time
        self.wrating = ""
        self.brating = ""

    def __repr__(self):
        rep = FICSGame.__repr__(self)[0:-1]
        rep = rep.replace("<FICSGame", "<FICSAdjournedGame")
        if self.our_color is not None:
            rep += ", our_color=%i" % self.our_color
        if self.length is not None:
            rep += ", length=%i" % self.length
        if self.time is not None:
            rep += ", time=%s" % self.display_time
        return rep + ">"

    @property
    def display_time(self):
        if self.time is not None:
            return self.time.isoformat(' ')[0:16]

    @property
    def opponent(self):
        if self.our_color == WHITE:
            return self.bplayer
        elif self.our_color == BLACK:
            return self.wplayer


class FICSHistoryGame(FICSGame):
    def __init__(self,
                 wplayer,
                 bplayer,
                 time=None,
                 rated=False,
                 game_type=None,
                 private=False,
                 minutes=None,
                 inc=None,
                 result=None,
                 reason=None,
                 board=None,
                 relation=None,
                 wrating=None,
                 brating=None,
                 gameno=None,
                 history_no=None):
        assert time is None or isinstance(time, datetime.datetime), time
        FICSGame.__init__(self,
                          wplayer,
                          bplayer,
                          rated=rated,
                          private=private,
                          game_type=game_type,
                          minutes=minutes,
                          inc=inc,
                          result=result,
                          reason=reason,
                          board=board,
                          relation=relation,
                          gameno=gameno)
        self.time = time
        self.wrating = wrating
        self.brating = brating
        self.history_no = history_no

    def __hash__(self):
        return hash(":".join((self.wplayer.name[0:11].lower(
        ), self.bplayer.name[0:11].lower(), str(self.history_no), str(
            self.time))))

    @property
    def display_time(self):
        if self.time is not None:
            return self.time.isoformat(' ')[0:16]


class FICSJournalGame(FICSGame):
    def __init__(self,
                 wplayer,
                 bplayer,
                 our_color=None,
                 time=None,
                 rated=False,
                 game_type=None,
                 private=False,
                 minutes=None,
                 inc=None,
                 result=None,
                 reason=None,
                 board=None,
                 relation=None,
                 wrating=None,
                 brating=None,
                 gameno=None,
                 journal_no=None):
        assert our_color is None or our_color in (WHITE, BLACK), our_color
        assert time is None or isinstance(time, datetime.datetime), time
        FICSGame.__init__(self,
                          wplayer,
                          bplayer,
                          rated=rated,
                          private=private,
                          game_type=game_type,
                          minutes=minutes,
                          inc=inc,
                          result=result,
                          reason=reason,
                          board=board,
                          relation=relation,
                          gameno=gameno)
        self.wrating = wrating
        self.brating = brating
        self.journal_no = journal_no

    def __hash__(self):
        return hash(":".join((self.wplayer.name[0:11].lower(),
                              self.bplayer.name[0:11].lower(),
                              str(self.journal_no), )))

    @property
    def display_time(self):
        return _("Unknown")


class FICSGames(GObject.GObject):
    __gsignals__ = {
        'FICSGameCreated': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'FICSGameEnded': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'FICSAdjournedGameRemoved': (GObject.SignalFlags.RUN_FIRST, None,
                                     (object, )),
        'FICSHistoryGameRemoved': (GObject.SignalFlags.RUN_FIRST, None,
                                   (object, )),
        'FICSJournalGameRemoved': (GObject.SignalFlags.RUN_FIRST, None,
                                   (object, )),
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.games = {}
        self.games_by_gameno = {}
        self.adjourned_games = {}
        self.history_games = {}
        self.journal_games = {}
        self.connection = connection

    def start(self):
        self.connection.adm.connect("onAdjournmentsList",
                                    self.onAdjournmentsList)
        self.connection.adm.connect("onHistoryList", self.onHistoryList)
        self.connection.adm.connect("onJournalList", self.onJournalList)
        self.connection.bm.connect("curGameEnded", self.onCurGameEnded)

    def __getitem__(self, game):
        if not isinstance(game, FICSGame):
            raise TypeError("Not a FICSGame: %s" % repr(game))
        if hash(game) in self.games:
            return self.games[hash(game)]
        else:
            raise KeyError

    def __setitem__(self, key, value):
        """ key and value must be the same game """
        if not isinstance(key, FICSGame):
            raise TypeError
        if not isinstance(value, FICSGame):
            raise TypeError
        if key != value:
            raise Exception("Not the same: %s %s" % (repr(key), repr(value)))
        if hash(value) in self.games:
            raise Exception("%s already exists in %s" %
                            (repr(value), repr(self)))
        self.games[hash(value)] = value
        self.games_by_gameno[value.gameno] = value
        if isinstance(value, FICSAdjournedGame):
            self.adjourned_games[hash(value)] = value
        elif isinstance(value, FICSHistoryGame):
            self.history_games[hash(value)] = value
        elif isinstance(value, FICSJournalGame):
            self.journal_games[hash(value)] = value

    def __delitem__(self, game):
        if not isinstance(game, FICSGame):
            raise TypeError(repr(game), type(game))
        if game in self:
            del self.games[hash(game)]
        if game.gameno in self.games_by_gameno:
            del self.games_by_gameno[game.gameno]
        if game in self.adjourned_games:
            del self.adjourned_games[hash(game)]
        elif game in self.history_games:
            del self.history_games[hash(game)]
        elif game in self.journal_games:
            del self.journal_games[hash(game)]

    def __contains__(self, game):
        if not isinstance(game, FICSGame):
            raise TypeError
        if hash(game) in self.games:
            return True
        else:
            return False

    def keys(self):
        return self.games.keys()

    def items(self):
        return self.games.items()

    def values(self):
        return self.games.values()

    def get_game_by_gameno(self, gameno):
        if not isinstance(gameno, int):
            raise TypeError
        return self.games_by_gameno[gameno]

    def get(self, game, create=True, emit=True):
        # TODO: lock
        if game in self:
            self[game].update(game)
            game = self[game]
        elif create:
            self[game] = game
            if emit:
                self.emit("FICSGameCreated", [game, ])
        else:
            raise KeyError
        return game

    def game_ended(self, game):
        if game in self:
            if not game.move_queue.empty():
                @asyncio.coroutine
                def coro(game):
                    # we have to give a chance to ICPlayer
                    # to process the latest move(style12) message
                    # and remove game from game list panel also
                    yield from asyncio.sleep(0)
                    game = self[game]
                    self.emit("FICSGameEnded", game)
                    del self[game]
                create_task(coro(game))
            else:
                game = self[game]
                self.emit("FICSGameEnded", game)
                del self[game]

    def onAdjournmentsList(self, adm, adjournments):
        for game in self.adjourned_games.values():
            if game not in adjournments:
                del self[game]
                game.opponent.adjournment = False
                self.emit("FICSAdjournedGameRemoved", game)

    def onHistoryList(self, adm, history):
        for game in self.history_games.values():
            if game not in history:
                del self[game]
                self.emit("FICSHistoryGameRemoved", game)

    def onJournalList(self, adm, journal):
        for game in self.journal_games.values():
            if game not in journal:
                del self[game]
                self.emit("FICSJournalGameRemoved", game)

    def onCurGameEnded(self, bm, game):
        for adjourned_game in self.adjourned_games.values():
            for player in (game.wplayer, game.bplayer):
                if player == adjourned_game.opponent:
                    del self[adjourned_game]
                    adjourned_game.opponent.adjournment = False
                    self.emit("FICSAdjournedGameRemoved", adjourned_game)

        for game in self.history_games.values():
            del self[game]
            self.emit("FICSHistoryGameRemoved", game)
        self.connection.adm.queryHistory()
