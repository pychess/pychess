from math import e

from pychess.ic.FICSObjects import (
    FICSChallenge,
    get_seek_tooltip_text,
    get_challenge_tooltip_text,
)
from pychess.perspectives.fics.ParrentListSection import ParrentListSection
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.widgets.SpotGraph import SpotGraph

__title__ = _("Seek Graph")

__icon__ = addDataPrefix("glade/manseek.svg")

__desc__ = _("Handle seeks on graphical way")

YMARKS = (800, 1600, 2400)
# YLOCATION = lambda y: min(y / 3000., 3000)
XMARKS = (5, 15)
# XLOCATION = lambda x: e**(-6.579 / (x + 1))


def YLOCATION(y):
    return min(y / 3000.0, 3000)


def XLOCATION(x):
    return e ** (-6.579 / (x + 1))


# This is used to convert increment time to minutes. With a GAME_LENGTH on
# 40, a game on two minutes and twelve secconds will be placed at the same
# X location as a game on 2+12*40/60 = 10 minutes
GAME_LENGTH = 40


class Sidepanel(ParrentListSection):
    def load(self, widgets, connection, lounge):
        self.widgets = widgets
        self.connection = connection

        __widget__ = lounge.seek_graph

        self.graph = SpotGraph()

        for rating in YMARKS:
            self.graph.addYMark(YLOCATION(rating), str(rating))
        for mins in XMARKS:
            self.graph.addXMark(XLOCATION(mins), str(mins) + _(" min"))

        self.widgets["graphDock"].add(self.graph)
        self.graph.show()
        self.graph.connect("spotClicked", self.onSpotClicked)

        self.connection.seeks.connect("FICSSeekCreated", self.onAddSought)
        self.connection.seeks.connect("FICSSeekRemoved", self.onRemoveSought)
        self.connection.challenges.connect("FICSChallengeIssued", self.onAddSought)
        self.connection.challenges.connect("FICSChallengeRemoved", self.onRemoveSought)
        self.connection.bm.connect("playGameCreated", self.onPlayingGame)
        self.connection.bm.connect("curGameEnded", self.onCurGameEnded)

        return __widget__

    def onSpotClicked(self, graph, name):
        self.connection.bm.play(name)

    def onAddSought(self, manager, sought):
        log.debug(
            "%s" % sought, extra={"task": (self.connection.username, "onAddSought")}
        )
        x_loc = XLOCATION(
            float(sought.minutes) + float(sought.inc) * GAME_LENGTH / 60.0
        )
        y_loc = YLOCATION(float(sought.player_rating))
        if (sought.rated) and ("(C)" in sought.player.long_name()):
            type_ = 2
        elif not (sought.rated) and ("(C)" in sought.player.long_name()):
            type_ = 3
        elif sought.rated:
            type_ = 0
        else:
            type_ = 1

        if isinstance(sought, FICSChallenge):
            tooltip_text = get_challenge_tooltip_text(sought)
        else:
            tooltip_text = get_seek_tooltip_text(sought)
        self.graph.addSpot(sought.index, tooltip_text, x_loc, y_loc, type_)

    def onRemoveSought(self, manager, sought):
        log.debug(
            "%s" % sought, extra={"task": (self.connection.username, "onRemoveSought")}
        )
        self.graph.removeSpot(sought.index)

    def onPlayingGame(self, bm, game):
        self.widgets["seekGraphContent"].set_sensitive(False)

    def onCurGameEnded(self, bm, game):
        self.widgets["seekGraphContent"].set_sensitive(True)
