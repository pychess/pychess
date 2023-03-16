# Authors: Jonas Thiem

import re

from gi.repository import Gtk, GObject, Pango

from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import ARTIFICIAL

__title__ = _("Engines")

__icon__ = addDataPrefix("glade/panel_engineoutput.svg")
white = addDataPrefix("glade/panel_engineoutput.svg")

__desc__ = _(
    "The engine output panel shows the thinking output of chess engines (computer players) during a game"
)


class Sidepanel:
    def load(self, gmwidg):
        # Specify whether the panel should have a horizontal layout:
        horizontal = True

        if horizontal:
            self.box = Gtk.HBox()
        else:
            self.box = Gtk.VBox()
        __widget__ = self.box

        # Use two engine output widgets for each player color:
        self.output_white = EngineOutput(True)
        self.output_black = EngineOutput(False)
        if horizontal:
            self.output_separator = Gtk.VSeparator()
        else:
            self.output_separator = Gtk.HSeparator()

        self.output_noengines = Gtk.TextView()
        self.output_noengines.get_buffer().set_text(
            _("No chess engines (computer players) are participating in this game.")
        )
        self.output_noengines.set_editable(False)
        self.output_noengines.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        __widget__.pack_start(self.output_noengines, True, True, 0)
        __widget__.show_all()

        self.boardview = gmwidg.board.view

        self.model_cids = [
            self.boardview.model.connect_after("game_changed", self.game_changed),
            self.boardview.model.connect_after("players_changed", self.players_changed),
            self.boardview.model.connect_after("game_started", self.game_started),
            self.boardview.model.connect_after(
                "game_terminated", self.on_game_terminated
            ),
        ]
        return __widget__

    def on_game_terminated(self, model):
        for cid in self.model_cids:
            self.boardview.model.disconnect(cid)

    def updateVisibleOutputs(self, model):
        # Check which players participate and update which views are visible
        # gotplayers = False
        if model is None:
            return
        # gotEnginePlayers = False
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
                if self.output_white not in self.box.get_children():
                    # Remove black output and separator first
                    # to ensure proper ordering:
                    if self.output_black in self.box.get_children():
                        self.box.remove(self.output_black)
                        self.box.remove(self.output_separator)
                    self.box.pack_start(self.output_white, True, True, 0)
                    self.output_white.clear()
                    self.output_white.show_all()
                self.output_white.setTitle(model.players[0].name)
            else:
                if self.output_white in self.box.get_children():
                    self.box.remove(self.output_white)
                    self.box.remove(self.output_separator)

            # Add white engine info if black engine is participating:
            if gotBlackEngine:
                if self.output_black not in self.box.get_children():
                    if gotWhiteEngine:
                        self.box.pack_start(self.output_separator, False, True, 0)
                        self.output_separator.show()
                    self.box.pack_start(self.output_black, True, True, 0)
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
            if self.output_noengines not in self.box.get_children():
                self.box.pack_start(self.output_noengines, True, True, 0)
        return

    def players_changed(self, model):
        log.debug("engineOutputPanel.players_changed: starting")
        self.updateVisibleOutputs(model)
        log.debug("engineOutputPanel.players_changed: returning")
        return

    def game_started(self, model):
        self.updateVisibleOutputs(model)
        return

    def game_changed(self, model, ply):
        self.updateVisibleOutputs(model)
        return


class EngineOutput(Gtk.VBox):
    def __init__(self, white=True):
        GObject.GObject.__init__(self)

        self.attached_engine = None  # engine attached to which we listen
        self.white = white
        self.clear_on_output = False  # next thinking line belongs to new move

        # Title bar:
        self.title_label = Gtk.Label()
        self.title_color = Gtk.Image()

        self.title_hbox = Gtk.HBox()
        # self.title_hbox.pack_start(self.title_color, False)
        self.title_hbox.pack_start(self.title_color, False, False, 0)
        # self.title_hbox.pack_start(self.title_label, True, True)
        self.title_hbox.pack_start(self.title_label, True, True, 0)

        # Set black or white player icon in front:
        if white is True:
            self.title_color.set_from_file(addDataPrefix("glade/white.png"))
        else:
            self.title_color.set_from_file(addDataPrefix("glade/black.png"))

        # output scrolled window container:
        self.output_container = Gtk.ScrolledWindow()
        self.output_container.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )

        # scroll down on new output: -- not reliable with multilines added
        # uistuff.keepDown(self.output_container)

        # scroll down on new output: -- brute force variant
        def changed(vadjust):
            vadjust.set_value(vadjust.get_upper() - vadjust.get_page_size())

        self.output_container.get_vadjustment().connect("changed", changed)

        # Text field for output:
        self.output = Gtk.TextView()
        self.output_container.add(self.output)
        self.output.set_editable(False)
        self.output.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.tag_bold = self.output.get_buffer().create_tag(
            "bold", weight=Pango.Weight.BOLD
        )
        self.tag_color = self.output.get_buffer().create_tag(
            "color", foreground="#0033ff"
        )

        # Add all sub widgets to ourselves:
        # self.pack_start(self.title_hbox, False)
        # self.pack_start(self.output_container, True)
        self.pack_start(self.title_hbox, False, False, 0)
        self.pack_start(self.output_container, True, True, 0)

        # Precompile regexes we want to use:
        self.re_thinking_line_cecp = re.compile(r"^[0-9]+\.? +\-?[0-9]+ +")
        self.re_thinking_line_uci = re.compile(
            r"^info (.*) pv [a-hA-H][0-9][a-hA-H][0-9](.*)$"
        )
        self.re_move_line_cecp_alg = re.compile(
            r"^(move +)?[a-hA-H][0-9][a-hA-H][0-9]$"
        )
        self.re_move_line_cecp_san = re.compile(
            r"^(move +)?([QKNB]?[a-hA-H]?[xX@]?[a-hA-H][0-9]\+?#?|[oO]-[oO]-[oO]|[oO]-[oO])$"
        )
        self.re_move_line_uci = re.compile(
            r"^bestmove +[a-hA-H][0-9][a-hA-H][0-9]( .*)?$"
        )
        self.re_extract_cecp_all = re.compile(
            r"^([0-9]+)\.? +(\-?[0-9]+) +([0-9]+).?([0-9]*) ([^ ].*)$"
        )
        self.re_extract_uci_depth = re.compile(r"depth +([0-9]+) +")
        self.re_extract_uci_score = re.compile(r"score cp +(-?[0-9]+) +")
        self.re_extract_uci_score_mate_other = re.compile(r"score +mate +([0-9]+) +")
        self.re_extract_uci_score_mate_us = re.compile(r"score +mate +\-([0-9]+) +")
        self.re_extract_uci_score_lowerbound = re.compile(r"score +lowerbound +")
        self.re_extract_uci_score_upperbound = re.compile(r"score +upperbound +")
        self.re_extract_uci_pv = re.compile(r"pv +([a-hA-HoO].*[^ ]) *$")
        self.re_extract_uci_nps = re.compile(r"nps +([0-9]+) +")

    def _del(self):
        self.detachEngine()

    def appendNewline(self):
        # Start a new line if text output isn't empty:
        if self.output.get_buffer().get_char_count() > 0:
            # We have old content, append newline
            self.output.get_buffer().insert(
                self.output.get_buffer().get_end_iter(), "\n"
            )

    def append(self, line, tag=None):
        # Append a specific string with the given formatting:
        # oldenditer = self.output.get_buffer().get_end_iter()
        self.output.get_buffer().insert(self.output.get_buffer().get_end_iter(), line)
        if tag is not None:
            enditer = self.output.get_buffer().get_end_iter()
            startiter = enditer.copy()
            startiter.backward_chars(len(line))
            self.output.get_buffer().apply_tag(tag, startiter, enditer)

    def appendThinking(self, depth, score, pv, nps):
        # Append a formatted thinking line:
        self.appendNewline()
        self.append(depth.__str__() + ". ", self.tag_color)
        self.append("Score: ", self.tag_bold)
        self.append(score.__str__() + " ")
        self.append("PV: ", self.tag_bold)
        self.append(pv.__str__() + " ")
        if nps != "":
            self.append("NPS: ", self.tag_bold)
            self.append(nps.__str__())

    def parseInfoLine(self, line):
        # Parse an identified info line and add it to our output:
        if self.clear_on_output is True:
            self.clear_on_output = False
            self.clear()

        # Clean up line first:
        while line.find("  ") != -1:
            line = line.replace("  ", " ")

        depth = "?"
        score = "?"
        pv = "?"
        nps = ""
        infoFound = False

        # do more sophisticated parsing here:
        if line.startswith("info "):
            # UCI info line
            # always end with a space to faciliate searching:
            line = line + " "

            # parse depth:
            result = self.re_extract_uci_depth.search(line)
            if result:
                depth = result.group(1)

            # parse score:
            result = self.re_extract_uci_score.search(line)
            if result:
                score = result.group(1)
            else:
                result = self.re_extract_uci_score_mate_other.search(line)
                if result:
                    score = "winning in " + result.group(1) + " moves"
                else:
                    result = self.re_extract_uci_score_mate_us.search(line)
                    if result:
                        score = "losing in " + result.group(1) + " moves"
                    else:
                        if self.re_extract_uci_score_lowerbound.search(line):
                            score = "lowerbound"
                        elif self.re_extract_uci_score_upperbound.search(line):
                            score = "upperbound"
            # parse pv:
            result = self.re_extract_uci_pv.search(line)
            if result:
                infoFound = True
                pv = result.group(1)

            # parse nps:
            result = self.re_extract_uci_nps.search(line)
            if result:
                infoFound = True
                nps = result.group(1)
        else:
            # CECP/Winboard/GNUChess info line
            # parse all information in one go:
            result = self.re_extract_cecp_all.match(line)
            if not result:
                return
            infoFound = True
            depth = result.group(1)
            score = result.group(2)
            time = result.group(3)
            nodes = result.group(4)
            pv = result.group(5)

            nps = str(int(int(nodes) / (int(time) / 100))) if int(time) > 0 else ""
            # Clean pv of unwanted chars:
        pv = re.sub("[^a-z^A-Z^0-9^ ^x^@^?]", "", pv)

        # If we found useful information, show it:
        if infoFound:
            self.appendThinking(depth, score, pv, nps)

    def parseLine(self, engine, line):
        # Clean up the line a bit:
        line = line.strip(" \r\t\n")
        line = line.replace("\t", " ")

        # PARSING THINKING OUTPUT (roughly, simply identifies the lines):

        # GNU Chess/CECP/Winboard engine thinking output lines:
        if self.re_thinking_line_cecp.match(line):
            self.parseInfoLine(line)

        # UCI engine thinking output lines:
        if self.re_thinking_line_uci.match(line):
            if line.find("depth") != -1 and line.find("score") != -1:
                self.parseInfoLine(line)

        # PARSE MOVE LINES (roughly, we merely identify them):

        # We want to clear on the next output info line
        # when a move arrived, so that for every move
        # we freshly fill our thinking output:

        # CECP/Winboard move line, long algebraeic notation:
        if self.re_move_line_cecp_alg.match(line):
            self.clear_on_output = True

        # CECP/Winboard move line, SAN notation:
        if self.re_move_line_cecp_san.match(line):
            self.clear_on_output = True

        # UCI move line:
        if self.re_move_line_uci.match(line):
            self.clear_on_output = True
        return

    def clear(self):
        self.output.get_buffer().set_text("")
        return

    def setTitle(self, title):
        self.title_label.set_text(title)
        return

    def attachEngine(self, engine):
        # Attach an engine for line listening
        if self.attached_engine is not None:
            if self.attached_engine == engine:
                # We are already attached to this engine
                return
            # Detach from previous engine
            self.attached_engine.disconnect(self.attached_handler_id)
        # Attach to new engine:
        log.debug(
            "Attaching " + self.__str__() + " to engine " + engine.__str__(),
            extra={"task": engine.defname},
        )
        self.attached_engine = engine
        self.attached_handler_id = engine.connect("line", self.parseLine)
        return

    def detachEngine(self):
        # Detach from attached engine
        if self.attached_engine is not None:
            log.debug(
                "Detaching "
                + self.__str__()
                + " from engine "
                + self.attached_engine.__str__(),
                extra={"task": self.attached_engine.defname},
            )
            self.attached_engine.disconnect(self.attached_handler_id)
            self.attached_engine = None

    def __repr__(self):
        color = "black"
        if self.white:
            color = "white"
        return "Engine Output " + color + " #" + id(self).__str__()


#    def __str__(self):
#        return repr(self) + " (engine: " + self.attached_engine.__str__() + ")"
