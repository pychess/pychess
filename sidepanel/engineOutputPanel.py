
from math import e
from random import randint
from sys import maxint

import gtk, gobject
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.glock import glock_connect
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, DRAW, RUNNING, WHITEWON, BLACKWON, ARTIFICIAL
from pychess.Utils.lutils import leval

__title__ = _("Engines")

__icon__ = addDataPrefix("glade/panel_engineoutput.svg")
white = addDataPrefix("glade/panel_engineoutput.svg")

__desc__ = _("The engine output panel shows the thinking output of chess engines (computer players) during a game")

class Sidepanel:
    
    def load (self, gmwidg):
        __widget__ = gtk.VBox()
        self.box = __widget__

        # Use two engine output widgets for each player color:
        self.output_white = EngineOutput(True)
        self.output_black = EngineOutput(False)
        self.output_noengines = gtk.TextView()
        self.output_noengines.get_buffer().set_text(
        _("No chess engines (computer players) are participating in this game."))
        self.output_noengines.set_editable(False)
        self.output_noengines.set_wrap_mode(gtk.WRAP_WORD_CHAR)

        __widget__.pack_start(self.output_noengines)
        __widget__.show_all()
        
        self.boardview = gmwidg.board.view
        
        glock_connect(self.boardview.model, "game_changed", self.game_changed)
        glock_connect(self.boardview.model, "players_changed", self.players_changed)
        glock_connect(self.boardview.model, "game_started", self.game_changed)
        
        return __widget__

    def updateVisibleOutputs (self, model):
        # Check which players participate and update which views are visible
        gotplayers = False

        gotEnginePlayers = False
        gotWhiteEngine = False
        gotBlackEngine = False
        if len(model.players) > 0:
            if model.players[0].__type__ == ARTIFICIAL:
                gotWhiteEngine = True
            if model.players[1].__type__ == ARTIFICIAL:
                gotBlackEngine = True
        
        if gotBlackEngine or gotWhiteEngine:
            # Remove "no engines" label:
            if self.output_noengines in self.box.get_children():
                self.box.remove(self.output_noengines)

            # Add white engine info if white engine is participating:
            if gotWhiteEngine:
                if not self.output_white in self.box.get_children():
                    # Remove black output first to ensure proper ordering:
                    if self.output_black in self.box.get_children():
                        self.box.remove(self.output_black)
                    self.box.pack_start(self.output_white)
                    self.output_white.clear()
                    self.output_white.show_all()
                self.output_white.setTitle(model.players[0].name)
            else:
                if self.output_white in self.box.get_children():
                    self.box.remove(self.output_white)
            
            # Add white engine info if black engine is participating:
            if gotBlackEngine:
                if not self.output_black in self.box.get_children():
                    self.box.pack_start(self.output_black)
                    self.output_black.clear()
                    self.output_black.show_all()
                self.output_black.setTitle(model.players[1].name)
            else:
                if self.output_black in self.box.get_children():
                    self.box.remove(self.output_black)
        else:
            # Show "no engines" label
            if self.output_white in self.box.get_children():
                self.box.remove(self.output_white)
            if self.output_black in self.box.get_children():
                self.box.remove(self.output_black)
            if not self.output_noengine in self.box.get_children():
                self.box.pack_start(self.output_noengine)
        return

    def players_changed (self, model):
        self.updateVisibleOutputs(model)
        return

    def game_started (self, model):   
        self.updateVisibleOutputs(model)
        return

    def game_changed (self, model):
        self.updateVisibleOutputs(model)
        return

class EngineOutput (gtk.VBox):
    def __init__(self, white=True):
        gtk.VBox.__init__(self)

        self.white = white

        # Title bar:
        self.title_label = gtk.Label()
        self.title_color = gtk.Image()

        self.title_hbox = gtk.HBox()
        self.title_hbox.pack_start(self.title_color, False)
        self.title_hbox.pack_start(self.title_label, True, True)

        # Set black or white player icon in front:
        if white == True:
            self.title_color.set_from_file(addDataPrefix("glade/white.png"))
        else:
            self.title_color.set_from_file(addDataPrefix("glade/black.png"))
        
        # output scrolled window container:
        self.output_container = gtk.ScrolledWindow()
        self.output_container.set_policy(gtk.POLICY_NEVER,
        gtk.POLICY_AUTOMATIC)
 
        # Text field for output:
        self.output = gtk.TextView()
        self.output_container.add(self.output)
        self.output.set_editable(False)
        self.output.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        
        # Add all sub widgets to ourselves:
        self.pack_start(self.title_hbox, False)
        self.pack_start(self.output_container, True)
    
    def clear (self):
        self.output.get_buffer().set_text(_(" "))
        return

    def setTitle (self, title):
        self.title_label.set_text(title)
        return
 
