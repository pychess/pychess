import math
import random
from os.path import basename
from urllib.request import urlopen
from urllib.parse import unquote

from gi.repository import Gtk, GObject, Pango

from pychess.compat import create_task
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.System import uistuff, conf
from pychess.Utils.GameModel import GameModel
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import LOCAL, ARTIFICIAL, WHITE, BLACK, NORMALCHESS, LECTURE, LESSON, PUZZLE, ENDGAME
from pychess.Variants import variants
from pychess.ic import ICLogon
from pychess.widgets import newGameDialog
from pychess.widgets.Background import giveBackground
from pychess.widgets.RecentChooser import recent_manager, recent_menu
from pychess.perspectives import perspective_manager
from pychess.perspectives.games import get_open_dialog
from pychess.perspectives.learn.LecturesPanel import LECTURES, start_lecture_from
from pychess.perspectives.learn.EndgamesPanel import ENDGAMES, start_endgame_from
from pychess.perspectives.learn.LessonsPanel import LESSONS, start_lesson_from
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
tasker_widgets = uistuff.GladeWidgets("taskers.glade")


class NewGameTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = widgets = tasker_widgets
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
            # Just to make sphinx happy...
            try:
                pix = newGameDialog.skillToIconLarge[int(scale.get_value())]
                widgets["skillImage"].set_from_pixbuf(pix)
            except TypeError:
                pass

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

        name = conf.get("firstName")
        player0tup = (LOCAL, Human, (color, name), name)
        if opponent == 0:
            name = conf.get("secondName")
            player1tup = (LOCAL, Human, (1 - color, name), name)
        else:
            engine = discoverer.getEngineByName(engine)
            name = discoverer.getName(engine)
            player1tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                          (engine, 1 - color, difficulty,
                           variants[NORMALCHESS], 5 * 60, 0), name)

        perspective = perspective_manager.get_perspective("games")
        if color == WHITE:
            create_task(perspective.generalStart(gamemodel, player0tup, player1tup))
        else:
            create_task(perspective.generalStart(gamemodel, player1tup, player0tup))


big_start = load_icon(48, "stock_init", "gnome-globe", "applications-internet")


class InternetGameTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = tasker_widgets
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
        self.ics_combo.set_active(conf.get("ics_combo"))

        self.widgets["connectButton"].connect("clicked", self.connectClicked)
        self.widgets["opendialog2"].connect("clicked", self.openDialogClicked)

        self.widgets["startIcon"].set_from_pixbuf(big_start)

        uistuff.keep(self.widgets["ics_combo"], "ics_combo")
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
        self.widgets = tasker_widgets
        tasker = self.widgets["learnTasker"]
        tasker.unparent()
        self.add(tasker)

        startButton = self.widgets["learnButton"]
        startButton.set_name("learnButton")

        categorystore = Gtk.ListStore(int, str)

        learn_mapping = {
            LECTURE: (_("Lectures"), LECTURES),
            LESSON: (_("Lessons"), LESSONS),
            PUZZLE: (_("Puzzles"), PUZZLES),
            ENDGAME: (_("Endgames"), ENDGAMES),
        }
        for key, value in learn_mapping.items():
            categorystore.append([key, value[0]])

        self.category_combo = self.widgets["category_combo"]
        self.category_combo.set_model(categorystore)
        renderer = Gtk.CellRendererText()
        self.category_combo.pack_start(renderer, True)
        self.category_combo.add_attribute(renderer, "text", 1)

        self.learnstore = Gtk.ListStore(str, str)
        self.learn_combo = self.widgets["learn_combo"]
        self.learn_combo.set_model(self.learnstore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("width-chars", 30)
        renderer_text.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.learn_combo.pack_start(renderer_text, True)
        self.learn_combo.add_attribute(renderer_text, "text", 1)
        self.learn_combo.set_active(0)

        def on_category_changed(combo):
            tree_iter = combo.get_active_iter()
            if tree_iter is None:
                return
            else:
                model = combo.get_model()
                self.category = model[tree_iter][0]

                self.learnstore.clear()
                if self.category == LECTURE:
                    for file_name, title, author in LECTURES:
                        self.learnstore.append([file_name, title])
                elif self.category == LESSON:
                    for file_name, title, author in LESSONS:
                        self.learnstore.append([file_name, title])
                elif self.category == PUZZLE:
                    for file_name, title, author in PUZZLES:
                        self.learnstore.append([file_name, title])
                elif self.category == ENDGAME:
                    for pieces, title in ENDGAMES:
                        self.learnstore.append([pieces, title])

                learn = conf.get("learncombo%s" % self.category)
                self.learn_combo.set_active(learn)

                def on_learn_changed(combo):
                    tree_iter = combo.get_active_iter()
                    if tree_iter is None:
                        return
                    else:
                        model = combo.get_model()
                        newlearn = model.get_path(tree_iter)[0]
                        conf.set("learncombo%s" % self.category, newlearn)
                self.learn_combo.connect("changed", on_learn_changed)

        self.category_combo.connect("changed", on_category_changed)
        self.category = conf.get("categorycombo")
        self.category_combo.set_active(self.category)

        uistuff.keep(self.widgets["category_combo"], "categorycombo")

        self.widgets["opendialog4"].connect("clicked", self.openDialogClicked)
        self.widgets["learnButton"].connect("clicked", self.learnClicked)

    def openDialogClicked(self, button):
        perspective = perspective_manager.get_perspective("learn")
        perspective.activate()

    def learnClicked(self, button):
        perspective = perspective_manager.get_perspective("learn")
        perspective.activate()

        tree_iter = self.learn_combo.get_active_iter()
        if tree_iter is None:
            return
        else:
            model = self.learn_combo.get_model()
            source = model[tree_iter][0]

        if self.category == LECTURE:
            start_lecture_from(source)
        elif self.category == LESSON:
            start_lesson_from(source)
        elif self.category == PUZZLE:
            start_puzzle_from(source)
        elif self.category == ENDGAME:
            start_endgame_from(source)


class DatabaseTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = tasker_widgets
        tasker = self.widgets["databaseTasker"]
        tasker.unparent()
        self.add(tasker)

        startButton = self.widgets["openButton"]
        startButton.set_name("openButton")

        liststore = Gtk.ListStore(str, str)

        self.recent_combo = self.widgets["recent_combo"]
        self.recent_combo.set_model(liststore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("width-chars", 30)
        renderer_text.set_property("ellipsize", Pango.EllipsizeMode.END)
        self.recent_combo.pack_start(renderer_text, True)
        self.recent_combo.add_attribute(renderer_text, "text", 1)

        self.on_recent_menu_changed(recent_manager, liststore)
        recent_manager.connect("changed", self.on_recent_menu_changed, liststore)

        self.widgets["opendialog3"].connect("clicked", self.openDialogClicked)
        self.widgets["openButton"].connect("clicked", self.openClicked)

    def on_recent_menu_changed(self, manager, liststore):
        liststore.clear()
        # Just to make sphinx happy...
        try:
            for uri in recent_menu.get_uris():
                liststore.append((uri, basename(unquote(uri)), ))
        except TypeError:
            pass
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
