
# Authors: Jonas Thiem

import re

import gtk, gobject

from pychess.System import uistuff
from pychess.System.glock import glock_connect
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import ARTIFICIAL

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
        self.output_separator = gtk.HSeparator()
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
                self.output_white.attachEngine(model.players[0].engine)
            if model.players[1].__type__ == ARTIFICIAL:
                gotBlackEngine = True
                self.output_black.attachEngine(model.players[1].engine)
        
        # First, detach from old engines:
        if not gotBlackEngine:
            self.output_black.detachEngine()
        if not gotWhiteEngine:
            self.output_white.detachEngine()
        
        if gotBlackEngine or gotWhiteEngine:
            # Remove "no engines" label:
            if self.output_noengines in self.box.get_children():
                self.box.remove(self.output_noengines)

            # Add white engine info if white engine is participating:
            if gotWhiteEngine:
                if not self.output_white in self.box.get_children():
                    # Remove black output and separator first
                    # to ensure proper ordering:
                    if self.output_black in self.box.get_children():
                        self.box.remove(self.output_black)
                        self.box.remove(self.output_separator)
                    self.box.pack_start(self.output_white)
                    self.output_white.clear()
                    self.output_white.show_all()
                self.output_white.setTitle(model.players[0].name)
            else:
                if self.output_white in self.box.get_children():
                    self.box.remove(self.output_white)
                    self.box.remove(self.output_separator)
            
            # Add white engine info if black engine is participating:
            if gotBlackEngine:
                if not self.output_black in self.box.get_children():
                    if gotWhiteEngine:
                        self.box.pack_start(self.output_separator)
                        self.output_separator.show()
                    self.box.pack_start(self.output_black)
                    self.output_black.clear()
                    self.output_black.show_all()
                self.output_black.setTitle(model.players[1].name)
            else:
                if self.output_black in self.box.get_children():
                    self.box.remove(self.output_black)
                    self.box.remove(self.output_separator)
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

        self.attached_engine = None  # engine attached to which we listen
        self.white = white
        self.clear_on_output = False  # next thinking line belongs to new move

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

        # scroll down on new output:
        uistuff.keepDown(self.output_container)
 
        # Text field for output:
        self.output = gtk.TextView()
        self.output_container.add(self.output)
        self.output.set_editable(False)
        self.output.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        
        # Add all sub widgets to ourselves:
        self.pack_start(self.title_hbox, False)
        self.pack_start(self.output_container, True)

    def append (self, line):
        # See if we want to append or simply set:
        if self.output.get_buffer().get_char_count() > 0:
            # We have old content, append
            self.output.get_buffer().insert(self.output.get_buffer().
            get_end_iter(), "\n" + line)
        else:
            # Set contents directly
            self.output.get_buffer().set_text(line)

    def parseInfoLine (self, line):
        if self.clear_on_output == True:
            self.clear_on_output = False
            self.clear()

        # FIXME: do more sophisticated parsing here:
        if line.startswith("info "):
            # UCI info line
            self.append(line[len("info "):])
        else:
            # CECP/Winboard/GNUChess info line
            self.append(line)

    def parseLines (self, engine, lines):
        for line in lines:
            # Clean up the line a bit:
            line = line.strip(" \r\t\n")

            # GNU Chess/CECP/Winboard engine thinking output lines:
            if re.match( r'^[0-9]+\. ', line, re.I):
                self.parseInfoLine(line)

            # UCI engine thinking output lines:
            if re.match( r'^info (.*) pv [a-h][0-9][a-h][0-9](.*)$', line,
            re.I):
                if line.find("depth") != -1 and line.find("score") != -1:
                    self.parseInfoLine(line)

            # We want to clear on the next output info line
            # when a move arrived, so that for every move
            # we freshly fill our thinking output:

            # CECP/Winboard oldstyle move line, long algebraeic notation:
            if re.match( r'^move +[a-h][0-9][a-h][0-9]$', line, re.I):
                self.clear_on_output = True

            # CECP/Winboard newstyle move line, SAN notation:
            if re.match( r'^move +[QKNB]?[a-h]?x?[a-h][0-9]\+?#?$',
            line, re.I):
                self.clear_on_output = True

            # CECP/Winboard newstyle move line, SAN castling:
            if re.match( r'^move +(O-O-O|O-O)$', line, re.I):
                self.clear_on_output = True

            # CECP/Winboard newstyle move line, long algebraeic notation:
            if re.match( r'^[a-h][0-9][a-h][0-9]$', line, re.I):
                self.clear_on_output = True

            # CECP/Winboard newstyle move line, SAN notation:
            if re.match( r'^[QKNB]?[a-h]?x?[a-h][0-9]\+?#?$', line, re.I):
                self.clear_on_output = True

            # CECP/Winboard newstyle move line, SAN castling:
            if re.match( r'^(O-O-O|O-O)$', line, re.I):
                self.clear_on_output = True

            # UCI move line:
            if re.match( r'^bestmove +[a-h][0-9][a-h][0-9]$', line, re.I):
                self.clear_on_output = True
        return

    def clear (self):
        self.output.get_buffer().set_text("")
        return

    def setTitle (self, title):
        self.title_label.set_text(title)
        return

    def attachEngine (self, engine):
        # Attach an engine for line listening
        if not self.attached_engine is None:
            if self.attached_engine == engine:
                # We are already attached to this engine
                return
            # Detach from previous engine
            self.attached_engine.disconnect(self.attached_handler_id)
        # Attach to new engine:
        log.debug("Attaching " + self.__str__() + " to engine " + engine.__str__())
        self.attached_engine = engine
        self.attached_handler_id = engine.connect("line", self.parseLines)
        return

    def detachEngine (self):
        # Detach from attached engine
        if not self.attached_engine is None:
            log.debug("Detaching " + self.__str__() + " from engine " + self.attached_engine.__str__())
            self.attached_engine.disconnect(self.attached_handler_id)
            self.attached_engine = None

    def __repr__(self):
        color = "black"
        if self.white:
            color = "white"
        return "Engine Output " + color + " #" + id(self).__str__() + " (engine: " + self.attached_engine.__str__()
 

