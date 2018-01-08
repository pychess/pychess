import asyncio
import math
import random
from os.path import basename
from urllib.request import urlopen
from urllib.parse import unquote

from gi.repository import Gtk, GObject, Pango

from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.System import uistuff, conf
from pychess.Utils.GameModel import GameModel
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import LOCAL, ARTIFICIAL, WHITE, BLACK, NORMALCHESS
from pychess.Variants import variants
from pychess.ic import ICLogon
from pychess.widgets import newGameDialog
from pychess.widgets.Background import giveBackground
from pychess.widgets.RecentChooser import recent_manager, recent_menu
from pychess.perspectives import perspective_manager
from pychess.perspectives.games import get_open_dialog
from pychess.perspectives.learn.PuzzlesPanel import PUZZLES, start_puzzle_from


class TaskerManager(Gtk.Table):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.border = 20
        giveBackground(self)
        self.connect("draw", self.expose)
        # self.set_homogeneous(True)

    def expose(self, widget, ctx):
        cairo_win = widget.get_window().cairo_create()

        for widget in self.widgets:
            x_loc = widget.get_allocation().x
            y_loc = widget.get_allocation().y
            width = widget.get_allocation().width
            height = widget.get_allocation().height

            cairo_win.move_to(x_loc - self.border, y_loc)
            cairo_win.curve_to(x_loc - self.border, y_loc - self.border / 2.,
                               x_loc - self.border / 2., y_loc - self.border, x_loc,
                               y_loc - self.border)
            cairo_win.line_to(x_loc + width, y_loc - self.border)
            cairo_win.curve_to(x_loc + width + self.border / 2., y_loc - self.border,
                               x_loc + width + self.border, y_loc - self.border / 2.,
                               x_loc + width + self.border, y_loc)
            cairo_win.line_to(x_loc + width + self.border, y_loc + height)
            cairo_win.curve_to(x_loc + width + self.border, y_loc + height + self.border / 2.,
                               x_loc + width + self.border / 2., y_loc + height + self.border,
                               x_loc + width, y_loc + height + self.border)
            cairo_win.line_to(x_loc, y_loc + height + self.border)
            cairo_win.curve_to(x_loc - self.border / 2., y_loc + height + self.border,
                               x_loc - self.border, y_loc + height + self.border / 2.,
                               x_loc - self.border, y_loc + height)

            style_ctxt = self.get_style_context()
            bgcolor = style_ctxt.lookup_color("p_bg_color")[1]
            darkcolor = style_ctxt.lookup_color("p_dark_color")[1]

            cairo_win.set_source_rgba(bgcolor.red, bgcolor.green, bgcolor.blue,
                                      bgcolor.alpha)
            cairo_win.fill()

            cairo_win.rectangle(x_loc - self.border, y_loc + height - 30,
                                width + self.border * 2, 30)
            cairo_win.set_source_rgba(darkcolor.red, darkcolor.green, darkcolor.blue,
                                      darkcolor.alpha)
            cairo_win.fill()

    def calcSpacings(self, n):
        """ Will yield ranges like
            ((.50,.50),)
            ((.66,.33), (.33,.66))
            ((.75,.25), (.50,.50), (.25,.75))
            ((.80,.20), (.60,.40), (.40,.60), (.20,.80))
            Used to create the centering in the table """

        first = next = (n) / float(n + 1)
        for i in range(n):
            yield (next, 1 - next)
            next = first - (1 - next)

    def on_size_allocate(self, widget, allocation):
        window = self.get_window()
        if window is not None:
            window.invalidate_rect(self.get_allocation(), False)

    def packTaskers(self, *widgets):
        self.widgets = widgets

        for widget in widgets:
            widget.connect("size-allocate", self.on_size_allocate)
        root = math.sqrt(len(widgets))
        # Calculate number of rows
        rows = int(math.ceil(root))
        # Calculate number of filled out rows
        rrows = int(math.floor(root))
        # Calculate number of cols in filled out rows
        cols = int(math.ceil(len(widgets) / float(rows)))

        # Calculate spacings

        vspac = [s[0] for s in self.calcSpacings(rows)]
        hspac = [s[0] for s in self.calcSpacings(cols)]

        # Clear and set up new size

        for child in self.get_children():
            self.remove(child)

        self.props.n_columns = cols
        self.props.n_rows = rows

        # Add filled out rows

        for row in range(rows):
            for col in range(cols):
                widget = widgets[row * cols + col]
                alignment = Gtk.Alignment.new(hspac[col], vspac[row], 0, 0)
                alignment.add(widget)
                self.attach(alignment, col, col + 1, row, row + 1)
        return

        # Add last row

        if rows > rrows:
            lastrow = Gtk.HBox()
            # Calculate number of widgets in last row
            numw = len(widgets) - cols * rrows
            hspac = [s[0] for s in self.calcSpacings(numw)]
            for col, widget in enumerate(widgets[-numw:]):
                alignment = Gtk.Alignment.new(hspac[col], vspac[-1], 0, 0)
                alignment.add(widget)
                alignment.set_padding(self.border, self.border, self.border,
                                      self.border)
                lastrow.pack_start(alignment, True, True, 0)

            self.attach(lastrow, 0, cols, rrows, rrows + 1)


tasker = TaskerManager()


class NewGameTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = widgets = uistuff.GladeWidgets("taskers.glade")
        tasker = widgets["newGameTasker"]
        tasker.unparent()
        self.add(tasker)

        startButton = self.widgets["startButton"]
        startButton.set_name("startButton")
        combo = Gtk.ComboBox()
        uistuff.createCombo(combo, [
            (get_pixbuf("glade/white.png"), _("White")),
            (get_pixbuf("glade/black.png"), _("Black")),
            (get_pixbuf("glade/random.png"), _("Random"))])
        widgets["colorDock"].add(combo)
        if combo.get_active() < 0:
            combo.set_active(0)
        uistuff.keep(combo, "newgametasker_colorcombo")
        widgets['yourColorLabel'].set_mnemonic_widget(combo)

        # We need to wait until after engines have been discovered, to init the
        # playerCombos. We use connect_after to make sure, that newGameDialog
        # has also had time to init the constants we share with them.
        self.playerCombo = Gtk.ComboBox()
        widgets["opponentDock"].add(self.playerCombo)
        discoverer.connect_after("all_engines_discovered",
                                 self.__initPlayerCombo, widgets)
        widgets['opponentLabel'].set_mnemonic_widget(self.playerCombo)

        def on_skill_changed(scale):
            pix = newGameDialog.skillToIconLarge[int(scale.get_value())]
            widgets["skillImage"].set_from_pixbuf(pix)

        widgets["skillSlider"].connect("value-changed", on_skill_changed)
        on_skill_changed(widgets["skillSlider"])

        widgets["startButton"].connect("clicked", self.startClicked)
        self.widgets["opendialog1"].connect("clicked", self.openDialogClicked)

    def __initPlayerCombo(self, discoverer, widgets):
        combo = self.playerCombo
        uistuff.createCombo(combo, newGameDialog.playerItems[0])
        if combo.get_active() < 0:
            combo.set_active(1)
            uistuff.keep(self.playerCombo, "newgametasker_playercombo")

            def on_playerCombobox_changed(widget):
                widgets["skillSlider"].props.visible = widget.get_active() > 0

            combo.connect("changed", on_playerCombobox_changed)

            uistuff.keep(widgets["skillSlider"], "taskerSkillSlider")
            widgets["skillSlider"].set_no_show_all(True)
            on_playerCombobox_changed(self.playerCombo)

    def openDialogClicked(self, button):
        newGameDialog.NewGameMode.run()

    def startClicked(self, button):
        color = self.widgets["colorDock"].get_child().get_active()
        if color == 2:
            color = random.choice([WHITE, BLACK])

        opp = self.widgets["opponentDock"].get_child()
        tree_iter = opp.get_active_iter()
        if tree_iter is not None:
            model = opp.get_model()
            engine = model[tree_iter][1]

        opponent = self.widgets["opponentDock"].get_child().get_active()
        difficulty = int(self.widgets["skillSlider"].get_value())

        gamemodel = GameModel(TimeModel(5 * 60, 0))

        name = conf.get("firstName", _("You"))
        player0tup = (LOCAL, Human, (color, name), name)
        if opponent == 0:
            name = conf.get("secondName", _("Guest"))
            player1tup = (LOCAL, Human, (1 - color, name), name)
        else:
            engine = discoverer.getEngineByName(engine)
            name = discoverer.getName(engine)
            player1tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                          (engine, 1 - color, difficulty,
                           variants[NORMALCHESS], 5 * 60, 0), name)

        perspective = perspective_manager.get_perspective("games")
        if color == WHITE:
            asyncio.async(perspective.generalStart(gamemodel, player0tup, player1tup))
        else:
            asyncio.async(perspective.generalStart(gamemodel, player1tup, player0tup))


big_start = load_icon(48, "stock_init", "gnome-globe", "applications-internet")


class InternetGameTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = uistuff.GladeWidgets("taskers.glade")
        tasker = self.widgets["internetGameTasker"]
        tasker.unparent()
        self.add(tasker)

        if ICLogon.dialog is None:
            ICLogon.dialog = ICLogon.ICLogon()

        liststore = Gtk.ListStore(str)
        liststore.append(["FICS"])
        liststore.append(["ICC"])
        self.ics_combo = self.widgets["ics_combo"]
        self.ics_combo.set_model(liststore)
        renderer_text = Gtk.CellRendererText()
        self.ics_combo.pack_start(renderer_text, True)
        self.ics_combo.add_attribute(renderer_text, "text", 0)
        self.ics_combo.connect("changed", ICLogon.dialog.on_ics_combo_changed)
        self.ics_combo.set_active(conf.get("ics_combo", 0))

        self.widgets["connectButton"].connect("clicked", self.connectClicked)
        self.widgets["opendialog2"].connect("clicked", self.openDialogClicked)

        self.widgets["startIcon"].set_from_pixbuf(big_start)

        uistuff.keep(self.widgets["ics_combo"], "icsCombo")
        uistuff.keep(self.widgets["autoLogin"], "autoLogin")

    def openDialogClicked(self, button):
        ICLogon.run()

    def connectClicked(self, button):
        ICLogon.run()
        if not ICLogon.dialog.connection:
            ICLogon.dialog.widgets["connectButton"].clicked()


class LearnTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = uistuff.GladeWidgets("taskers.glade")
        tasker = self.widgets["learnTasker"]
        tasker.unparent()
        self.add(tasker)

        startButton = self.widgets["learnButton"]
        startButton.set_name("learnButton")

        liststore = Gtk.ListStore(str, str)

        for file_name, title in PUZZLES:
            liststore.append([file_name, title])

        self.puzzle_combo = self.widgets["puzzle_combo"]
        self.puzzle_combo.set_model(liststore)
        renderer_text = Gtk.CellRendererText()
        self.puzzle_combo.pack_start(renderer_text, True)
        self.puzzle_combo.add_attribute(renderer_text, "text", 1)
        # TODO: save latest selected
        # self.puzzle_combo.connect("changed", ???)
        self.puzzle_combo.set_active(conf.get("puzzle_combo", 0))

        self.widgets["opendialog4"].connect("clicked", self.openDialogClicked)
        self.widgets["learnButton"].connect("clicked", self.learnClicked)

    def openDialogClicked(self, button):
        perspective = perspective_manager.get_perspective("learn")
        perspective.activate()

    def learnClicked(self, button):
        perspective = perspective_manager.get_perspective("learn")
        perspective.activate()

        tree_iter = self.puzzle_combo.get_active_iter()
        if tree_iter is None:
            return
        else:
            model = self.puzzle_combo.get_model()
            filename = model[tree_iter][0]

        print(filename)
        start_puzzle_from(filename)


class DatabaseTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = uistuff.GladeWidgets("taskers.glade")
        tasker = self.widgets["databaseTasker"]
        tasker.unparent()
        self.add(tasker)

        startButton = self.widgets["openButton"]
        startButton.set_name("openButton")

        liststore = Gtk.ListStore(str, str)

        self.recent_combo = self.widgets["recent_combo"]
        self.recent_combo.set_model(liststore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("max-width-chars", 40)
        renderer_text.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.recent_combo.pack_start(renderer_text, True)
        self.recent_combo.add_attribute(renderer_text, "text", 1)

        self.on_recent_menu_changed(recent_manager, liststore)
        recent_manager.connect("changed", self.on_recent_menu_changed, liststore)

        self.widgets["opendialog3"].connect("clicked", self.openDialogClicked)
        self.widgets["openButton"].connect("clicked", self.openClicked)

    def on_recent_menu_changed(self, manager, liststore):
        liststore.clear()
        for uri in recent_menu.get_uris():
            liststore.append((uri, basename(unquote(uri)), ))
        self.recent_combo.set_active(0)

    def openDialogClicked(self, button):
        dialog = get_open_dialog()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filenames = dialog.get_filenames()
        else:
            filenames = None

        dialog.destroy()

        if filenames is not None:
            for filename in filenames:
                if filename.lower().endswith(".fen"):
                    newGameDialog.loadFileAndRun(filename)
                else:
                    perspective = perspective_manager.get_perspective("database")
                    perspective.open_chessfile(filename)

    def openClicked(self, button):
        if self.widgets["createNew"].get_active():
            perspective = perspective_manager.get_perspective("database")
            perspective.create_database()

        else:
            tree_iter = self.recent_combo.get_active_iter()
            if tree_iter is None:
                return
            else:
                model = self.recent_combo.get_model()
                uri = model[tree_iter][0]

            try:
                urlopen(unquote(uri)).close()
                perspective = perspective_manager.get_perspective("database")
                perspective.open_chessfile(unquote(uri))
                recent_manager.add_item(uri)
            except (IOError, OSError):
                # shomething wrong whit the uri
                recent_manager.remove_item(uri)


new_game_tasker, internet_game_tasker, database_tasker, learn_tasker = \
    NewGameTasker(), InternetGameTasker(), DatabaseTasker(), LearnTasker()
tasker.packTaskers(new_game_tasker, database_tasker, internet_game_tasker, learn_tasker)
