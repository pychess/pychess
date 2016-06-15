from __future__ import absolute_import

import math
import random

from gi.repository import Gtk, Pango, GObject

from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.System import uistuff, conf
from pychess.System.idle_add import idle_add
from pychess.Utils.GameModel import GameModel
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import LOCAL, ARTIFICIAL, WHITE, BLACK, NORMALCHESS
from pychess.Variants import variants
from pychess.ic import ICLogon
from pychess.widgets.ionest import game_handler
from pychess.widgets import newGameDialog

from .Background import giveBackground
from .ToggleComboBox import ToggleComboBox


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

    def packTaskers(self, *widgets):
        self.widgets = widgets

        for widget in widgets:
            widget.connect(
                "size-allocate",
                lambda *a: self.get_window().invalidate_rect(self.get_allocation(), False))
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
        combo = ToggleComboBox("colortoggle")
        combo.addItem(_("White"), get_pixbuf("glade/white.png"))
        combo.addItem(_("Black"), get_pixbuf("glade/black.png"))
        combo.addItem(_("Random"), get_pixbuf("glade/random.png"))
        combo.setMarkup("<b>", "</b>")
        widgets["colorDock"].add(combo)
        uistuff.keep(combo, "newgametasker_colorcombo")
        widgets['yourColorLabel'].set_mnemonic_widget(combo)

        # We need to wait until after engines have been discovered, to init the
        # playerCombos. We use connect_after to make sure, that newGameDialog
        # has also had time to init the constants we share with them.
        self.playerCombo = ToggleComboBox("playertoggle")
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

    @idle_add
    def __initPlayerCombo(self, discoverer, widgets):
        combo = self.playerCombo
        combo.update(newGameDialog.smallPlayerItems[0])
        if combo.active < 0:
            combo.label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            combo.setMarkup("<b>", "</b>")
            combo.active = 1
            uistuff.keep(self.playerCombo, "newgametasker_playercombo")

            def on_playerCombobox_changed(widget, event):
                widgets["skillSlider"].props.visible = widget.active > 0

            combo.connect("changed", on_playerCombobox_changed)

            uistuff.keep(widgets["skillSlider"], "taskerSkillSlider")
            widgets["skillSlider"].set_no_show_all(True)
            on_playerCombobox_changed(self.playerCombo, None)

    def openDialogClicked(self, button):
        newGameDialog.NewGameMode.run()

    def startClicked(self, button):
        color = self.widgets["colorDock"].get_child().active
        if color == 2:
            color = random.choice([WHITE, BLACK])
        opponent = self.widgets["opponentDock"].get_child().active
        difficulty = int(self.widgets["skillSlider"].get_value())

        gamemodel = GameModel(TimeModel(5 * 60, 0))

        name = conf.get("firstName", _("You"))
        player0tup = (LOCAL, Human, (color, name), name)
        if opponent == 0:
            name = conf.get("secondName", _("Guest"))
            player1tup = (LOCAL, Human, (1 - color, name), name)
        else:
            engine = discoverer.getEngineN(opponent - 1)
            name = discoverer.getName(engine)
            player1tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                          (engine, 1 - color, difficulty,
                           variants[NORMALCHESS], 5 * 60, 0), name)

        if color == WHITE:
            game_handler.generalStart(gamemodel, player0tup, player1tup)
        else:
            game_handler.generalStart(gamemodel, player1tup, player0tup)

big_start = load_icon(48, "stock_init", "gnome-globe", "applications-internet")


class InternetGameTasker(Gtk.Alignment):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.widgets = uistuff.GladeWidgets("taskers.glade")
        tasker = self.widgets["internetGameTasker"]
        tasker.unparent()
        self.add(tasker)

        def asGuestCallback(check):
            names = ICLogon.get_user_names()
            self.widgets["usernameEntry"].set_text(names[1]
                                                   if check.get_active() else names[0])
            self.widgets["passwordLabel"].set_sensitive(not check.get_active())
            self.widgets["passwordEntry"].set_sensitive(not check.get_active())

        self.widgets["asGuestCheck"].connect("toggled", asGuestCallback)

        uistuff.keep(self.widgets["asGuestCheck"], "asGuestCheck")

        as_guest = self.widgets["asGuestCheck"]

        def user_name_get_value(entry):
            names = ICLogon.get_user_names()
            if as_guest.get_active():
                text = "%s|%s" % (names[0], entry.get_text())
            else:
                text = "%s|%s" % (entry.get_text(), names[1])
            return text

        def user_name_set_value(entry, value):
            names = ICLogon.get_user_names(value=value)
            if as_guest.get_active():
                entry.set_text(names[1])
            else:
                entry.set_text(names[0])

        uistuff.keep(self.widgets["usernameEntry"], "usernameEntry",
                     user_name_get_value, user_name_set_value)
        uistuff.keep(self.widgets["passwordEntry"], "passwordEntry")

        self.widgets["connectButton"].connect("clicked", self.connectClicked)
        self.widgets["opendialog2"].connect("clicked", self.openDialogClicked)

        self.widgets["startIcon"].set_from_pixbuf(big_start)

    def openDialogClicked(self, button):
        ICLogon.run()

    def connectClicked(self, button):
        asGuest = self.widgets["asGuestCheck"].get_active()
        username = self.widgets["usernameEntry"].get_text()
        password = self.widgets["passwordEntry"].get_text()

        ICLogon.run()
        if not ICLogon.dialog.connection:
            ICLogon.dialog.widgets["logOnAsGuest"].set_active(asGuest)
            ICLogon.dialog.widgets["nameEntry"].set_text(username)
            ICLogon.dialog.widgets["passEntry"].set_text(password)
            ICLogon.dialog.widgets["connectButton"].clicked()
