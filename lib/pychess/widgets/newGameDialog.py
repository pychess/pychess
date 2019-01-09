# -*- coding: UTF-8 -*-

import os.path
import gettext
import locale

from math import pi
from operator import attrgetter
from itertools import groupby
from io import StringIO

from gi.repository import Gdk, Gtk, GLib, GObject
from gi.repository import GtkSource

from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.Utils.GameModel import GameModel
from pychess.Utils.SetupModel import SetupModel, SetupPlayer
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import NORMALCHESS, VARIANTS_BLINDFOLD, FISCHERRANDOMCHESS, \
    VARIANTS_ODDS, VARIANTS_SHUFFLE, VARIANTS_OTHER, VARIANTS_OTHER_NONSTANDARD, VARIANTS_ASEAN, \
    WHITE, BLACK, UNSUPPORTED, ARTIFICIAL, LOCAL, reprCord, reprFile, W_OO, W_OOO, B_OO, B_OOO, \
    FAN_PIECES, reprSign, FEN_START, WAITING_TO_START

from pychess.compat import create_task
from pychess.Utils.repr import localReprSign
from pychess.Utils.lutils.ldata import FILE
from pychess.Utils.lutils.LBoard import LBoard
from pychess.System import uistuff
from pychess.System.Log import log
from pychess.System.protoopen import splitUri
from pychess.System import conf
from pychess.System.prefix import getDataPrefix, isInstalled, addDataPrefix
from pychess.Players.engineNest import discoverer
from pychess.Players.Human import Human
from pychess.widgets import ImageMenu
from pychess.widgets import mainwindow
from pychess.widgets.BoardControl import BoardControl
from pychess.Savers import fen, pgn
from pychess.Savers.ChessFile import LoadingError
from pychess.Variants import variants
from pychess.Variants.normal import NormalBoard
from pychess.perspectives import perspective_manager
from pychess.perspectives.games import enddir

# ===============================================================================
# We init most dialog icons global to make them accessibly to the
# Background.Taskers so they have a similar look.
# ===============================================================================
big_time = get_pixbuf("glade/stock_alarm.svg")
big_people = load_icon(48, "stock_people", "system-users")
iwheels = load_icon(24, "gtk-execute", "system-run")
ipeople = load_icon(24, "stock_people", "system-users")
inotebook = load_icon(24, "stock_notebook", "computer")

weather_icons = ("clear", "clear-night", "few-clouds", "few-clouds-night",
                 "fog", "overcast", "severe-alert", "showers-scattered",
                 "showers", "storm")
skillToIcon = {}
# Used by TaskerManager. Put here to help synchronization
skillToIconLarge = {}
for i, icon in enumerate(weather_icons, start=1):
    skillToIcon[2 * i - 1] = get_pixbuf("glade/16x16/weather-%s.png" % icon)
    skillToIcon[2 * i] = get_pixbuf("glade/16x16/weather-%s.png" % icon)
    skillToIconLarge[2 * i - 1] = get_pixbuf("glade/48x48/weather-%s.png" % icon)
    skillToIconLarge[2 * i] = get_pixbuf("glade/48x48/weather-%s.png" % icon)

playerItems = []
analyzerItems = []
allEngineItems = []


def createPlayerUIGlobals(discoverer):
    global playerItems
    global analyzerItems
    global allEngineItems

    playerItems = []
    analyzerItems = []
    allEngineItems = []

    for variantClass in variants.values():
        playerItems += [[(ipeople, _("Human Being"))]]
    for engine in discoverer.getEngines():
        name = engine["name"]
        c = discoverer.getCountry(engine)
        path = addDataPrefix("flags/%s.png" % c)

        if c and os.path.isfile(path):
            flag_icon = get_pixbuf(path)
        else:
            path = addDataPrefix("flags/unknown.png")
            flag_icon = get_pixbuf(path)

        allEngineItems.append((flag_icon, name))

        for variant in discoverer.getEngineVariants(engine):
            playerItems[variant] += [(flag_icon, name)]

        if discoverer.is_analyzer(engine):
            analyzerItems.append((flag_icon, name))


discoverer.connect("all_engines_discovered", createPlayerUIGlobals)

COPY, CLEAR, PASTE, INITIAL = 2, 3, 4, 5

# ===============================================================================
# GameInitializationMode is the super class of new game dialogs. Dialogs include
# the standard new game dialog, the load file dialog, the enter notation dialog
# and the setup position dialog.
# ===============================================================================


class _GameInitializationMode:
    @classmethod
    def _ensureReady(cls):
        if not hasattr(_GameInitializationMode, "superhasRunInit"):
            _GameInitializationMode._init()
            _GameInitializationMode.superhasRunInit = True
        if not hasattr(cls, "hasRunInit"):
            cls._init()
            cls.hasRunInit = True
        cls.widgets["newgamedialog"].resize(1, 1)

    @classmethod
    def _init(cls):
        cls.white = get_pixbuf("glade/white.png")
        cls.black = get_pixbuf("glade/black.png")

        cls.widgets = uistuff.GladeWidgets("newInOut.glade")
        cls.widgets["newgamedialog"].set_transient_for(mainwindow())

        def on_exchange_players(widget, button_event):
            white = cls.widgets["whitePlayerCombobox"].get_active()
            black = cls.widgets["blackPlayerCombobox"].get_active()
            whiteLevel = cls.widgets["skillSlider1"].get_value()
            blackLevel = cls.widgets["skillSlider2"].get_value()
            cls.widgets["whitePlayerCombobox"].set_active(black)
            cls.widgets["blackPlayerCombobox"].set_active(white)
            cls.widgets["skillSlider1"].set_value(blackLevel)
            cls.widgets["skillSlider2"].set_value(whiteLevel)

        cls.widgets["whitePlayerButton"].set_image(Gtk.Image.new_from_pixbuf(cls.white))
        cls.widgets["whitePlayerButton"].connect("button-press-event", on_exchange_players)
        cls.widgets["blackPlayerButton"].set_image(Gtk.Image.new_from_pixbuf(cls.black))
        cls.widgets["blackPlayerButton"].connect("button-press-event", on_exchange_players)

        uistuff.createCombo(cls.widgets["whitePlayerCombobox"], name="whitePlayerCombobox")
        uistuff.createCombo(cls.widgets["blackPlayerCombobox"], name="blackPlayerCombobox")

        cls.widgets["playersIcon"].set_from_pixbuf(big_people)
        cls.widgets["timeIcon"].set_from_pixbuf(big_time)

        def on_playerCombobox_changed(widget, skill_hbox, skill_level):
            position = widget.get_active()
            skill_hbox.props.visible = position > 0
            if position > 0:
                tree_iter = widget.get_active_iter()
                if tree_iter is not None:
                    engine_name = widget.get_model()[tree_iter][1]
                    engine = discoverer.getEngineByName(engine_name)
                    if engine:
                        pref_level = engine.get("level")
                        if pref_level:
                            skill_level.set_value(pref_level)

        cls.widgets["whitePlayerCombobox"].connect("changed", on_playerCombobox_changed, cls.widgets["skillHbox1"], cls.widgets["skillSlider1"])
        cls.widgets["blackPlayerCombobox"].connect("changed", on_playerCombobox_changed, cls.widgets["skillHbox2"], cls.widgets["skillSlider2"])
        cls.widgets["whitePlayerCombobox"].set_active(0)
        cls.widgets["blackPlayerCombobox"].set_active(1)

        def on_skill_changed(scale, image):
            image.set_from_pixbuf(skillToIcon[int(scale.get_value())])

        cls.widgets["skillSlider1"].connect("value-changed", on_skill_changed, cls.widgets["skillIcon1"])
        cls.widgets["skillSlider2"].connect("value-changed", on_skill_changed, cls.widgets["skillIcon2"])
        cls.widgets["skillSlider1"].set_value(3)
        cls.widgets["skillSlider2"].set_value(3)

        cls.__initTimeRadio("ngblitz", cls.widgets["blitzRadio"], cls.widgets["configImageBlitz"], 5, 0, 0)
        cls.__initTimeRadio("ngrapid", cls.widgets["rapidRadio"], cls.widgets["configImageRapid"], 15, 5, 0)
        cls.__initTimeRadio("ngnormal", cls.widgets["normalRadio"], cls.widgets["configImageNormal"], 45, 15, 0)
        cls.__initTimeRadio("ngclassical", cls.widgets["classicalRadio"], cls.widgets["configImageClassical"], 3, 0, 40)

        cls.__initVariantRadio("ngvariant1", cls.widgets["playVariant1Radio"], cls.widgets["configImageVariant1"])
        cls.__initVariantRadio("ngvariant2", cls.widgets["playVariant2Radio"], cls.widgets["configImageVariant2"])

        def updateCombos(*args):
            if cls.widgets["playNormalRadio"].get_active():
                variant = NORMALCHESS
            elif cls.widgets["playVariant1Radio"].get_active():
                variant = conf.get("ngvariant1")
            else:
                variant = conf.get("ngvariant2")
            variant1 = conf.get("ngvariant1")
            cls.widgets["playVariant1Radio"].set_tooltip_text(variants[variant1].__desc__)
            variant2 = conf.get("ngvariant2")
            cls.widgets["playVariant2Radio"].set_tooltip_text(variants[variant2].__desc__)
            data = [(item[0], item[1]) for item in playerItems[variant]]
            uistuff.updateCombo(cls.widgets["blackPlayerCombobox"], data)
            uistuff.updateCombo(cls.widgets["whitePlayerCombobox"], data)

        discoverer.connect_after("all_engines_discovered", updateCombos)
        updateCombos(discoverer)

        conf.notify_add("ngvariant1", updateCombos)
        conf.notify_add("ngvariant2", updateCombos)
        cls.widgets["playNormalRadio"].connect("toggled", updateCombos)
        cls.widgets["playNormalRadio"].set_tooltip_text(variants[NORMALCHESS].__desc__)
        cls.widgets["playVariant1Radio"].connect("toggled", updateCombos)
        variant1 = conf.get("ngvariant1")
        cls.widgets["playVariant1Radio"].set_tooltip_text(variants[variant1].__desc__)
        cls.widgets["playVariant2Radio"].connect("toggled", updateCombos)
        variant2 = conf.get("ngvariant2")
        cls.widgets["playVariant2Radio"].set_tooltip_text(variants[variant2].__desc__)

        # The "variant" has to come before players, because the engine positions
        # in the user comboboxes can be different in different variants
        for key in ("whitePlayerCombobox", "blackPlayerCombobox",
                    "skillSlider1", "skillSlider2", "notimeRadio",
                    "blitzRadio", "rapidRadio", "normalRadio", "classicalRadio",
                    "playNormalRadio", "playVariant1Radio", "playVariant2Radio"):
            uistuff.keep(cls.widgets[key], key)

        # We don't want the dialog to deallocate when closed. Rather we hide
        # it on respond
        cls.widgets["newgamedialog"].connect("delete_event", lambda *a: True)

    @classmethod
    def __initTimeRadio(cls, id, radiobutton, configImage, defmin, defgain, defmoves):
        minSpin = Gtk.SpinButton()
        minSpin.set_adjustment(Gtk.Adjustment(1, 0, 240, 1))
        setattr(cls, "%s_min" % id, minSpin)
        uistuff.keep(minSpin, "%s min" % id)
        movesSpin = Gtk.SpinButton()
        movesSpin.set_adjustment(Gtk.Adjustment(0, 0, 60, 20))
        setattr(cls, "%s_moves" % id, movesSpin)
        uistuff.keep(movesSpin, "%s moves" % id)
        gainSpin = Gtk.SpinButton()
        gainSpin.set_adjustment(Gtk.Adjustment(0, -60, 60, 1))
        setattr(cls, "%s_gain" % id, gainSpin)
        uistuff.keep(gainSpin, "%s gain" % id)

        table = Gtk.Table(2, 2)
        table.props.row_spacing = 3
        table.props.column_spacing = 12
        label = Gtk.Label(label=_("Minutes:"))
        label.props.xalign = 0
        table.attach(label, 0, 1, 0, 1)
        table.attach(minSpin, 1, 2, 0, 1)
        label = Gtk.Label(label=_("Moves:") if defmoves > 0 else _("Gain:"))
        label.props.xalign = 0
        table.attach(label, 0, 1, 1, 2)
        if defmoves > 0:
            table.attach(movesSpin, 1, 2, 1, 2)
        else:
            table.attach(gainSpin, 1, 2, 1, 2)
        alignment = Gtk.Alignment.new(1, 1, 1, 1)
        alignment.set_padding(6, 6, 12, 12)
        alignment.add(table)
        ImageMenu.switchWithImage(configImage, alignment)

        def updateString(spin):
            # Elements of the clock
            minutes = minSpin.get_value_as_int()
            gain = gainSpin.get_value_as_int()
            moves = movesSpin.get_value_as_int()

            # Duration of the game
            def calculate_duration(ref_moves):
                if moves > 0:
                    return int(2 * minutes * ref_moves / moves)
                else:
                    return max(0, int(2 * minutes + ref_moves * gain / 30))

            duration_20 = calculate_duration(20)
            duration_40 = calculate_duration(40)
            duration_60 = calculate_duration(60)

            # Determination of the caption
            def get_game_name():
                """ https://www.fide.com/fide/handbook.html?id=171&view=article """
                if defmoves > 0:
                    return _("Classical")
                if duration_60 <= 20:  # 10 minutes per player
                    return _("Blitz")
                if duration_60 < 120:  # 60 minutes per player
                    return _("Rapid")
                return _("Normal")

            if moves > 0:
                radiobutton.set_label(_("%(name)s %(minutes)d min / %(moves)d moves %(duration)s") % {
                    'name': get_game_name(),
                    'minutes': minutes,
                    'moves': moves,
                    'duration': ("(%d')" % duration_40) if duration_40 > 0 else ""
                })
            elif gain != 0:
                radiobutton.set_label(
                    _("%(name)s %(minutes)d min %(sign)s %(gain)d sec/move %(duration)s") % {
                        'name': get_game_name(),
                        'minutes': minutes,
                        'sign': "+" if gain > 0 else "–",
                        'gain': abs(gain),
                        'duration': ("(%d')" % duration_40) if duration_40 > 0 else ""
                    })
            else:
                radiobutton.set_label(_("%(name)s %(minutes)d min %(duration)s") % {
                    'name': get_game_name(),
                    'minutes': minutes,
                    'duration': ("(%d')" % duration_40) if duration_40 > 0 else ""
                })

            # Determination of the tooltip
            if duration_20 > 0 and duration_60 > 0 and duration_20 != duration_60:
                radiobutton.set_tooltip_text(_("Estimated duration : %(min)d - %(max)d minutes") % ({
                    "min": min(duration_20, duration_60),
                    "max": max(duration_20, duration_60)}
                ))
            else:
                radiobutton.set_tooltip_text("")

        minSpin.connect("value-changed", updateString)
        movesSpin.connect("value-changed", updateString)
        gainSpin.connect("value-changed", updateString)
        updateString(None)

    @classmethod
    def __initVariantRadio(cls, confid, radiobutton, configImage):
        model = Gtk.TreeStore(str)
        treeview = Gtk.TreeView(model)
        treeview.set_headers_visible(False)
        treeview.append_column(Gtk.TreeViewColumn(None,
                                                  Gtk.CellRendererText(),
                                                  text=0))
        alignment = Gtk.Alignment.new(1, 1, 1, 1)
        alignment.set_padding(6, 6, 12, 12)
        alignment.add(treeview)
        ImageMenu.switchWithImage(configImage, alignment)

        groupNames = {VARIANTS_BLINDFOLD: _("Blindfold"),
                      VARIANTS_ODDS: _("Odds"),
                      VARIANTS_SHUFFLE: _("Shuffle"),
                      VARIANTS_OTHER: _("Other (standard rules)"),
                      VARIANTS_OTHER_NONSTANDARD:
                      _("Other (non standard rules)"),
                      VARIANTS_ASEAN: _("Asian variants"), }

        specialVariants = [v
                           for v in variants.values()
                           if v != NormalBoard and v.variant not in UNSUPPORTED
                           ]
        specialVariants = sorted(specialVariants,
                                 key=attrgetter("variant_group"))
        groups = groupby(specialVariants, attrgetter("variant_group"))
        pathToVariant = {}
        variantToPath = {}
        for i, (id, group) in enumerate(groups):
            iter = model.append(None, (groupNames[id], ))
            for variant in group:
                subiter = model.append(iter, (variant.name, ))
                path = model.get_path(subiter)
                pathToVariant[path.to_string()] = variant.variant
                variantToPath[variant.variant] = path.to_string()
            treeview.expand_row(Gtk.TreePath(i), True)

        selection = treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.BROWSE)

        def selfunc(selection, store, path, path_selected, data):
            return path.get_depth() > 1

        selection.set_select_function(selfunc, None)
        variant = conf.get(confid)
        if variant in variantToPath:
            selection.select_path(variantToPath[variant])

        def callback(selection):
            model, iter = selection.get_selected()
            if iter:
                radiobutton.set_label("%s" % model.get(iter, 0) + _(" chess"))
                path = model.get_path(iter)
                variant = pathToVariant[path.to_string()]
                conf.set(confid, variant)

        selection.connect("changed", callback)
        callback(selection)

    @classmethod
    def _generalRun(cls, callback, validate):
        def onResponse(dialog, response):
            if response == COPY:
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                clipboard.set_text(cls.get_fen(), -1)
                # print("put clipboard:", clipboard.wait_for_text())
                return
            elif response == CLEAR:
                cls.board_control.emit("action", "SETUP", None, True)
                cls.ini_widgets(True)
                # print("clear")
                return
            elif response == PASTE:
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                text = clipboard.wait_for_text()
                # print("got clipboard:", text)
                if text is None or len(text.split()) < 2:
                    return
                try:
                    lboard = cls.setupmodel.variant(setup=text).board
                    cls.ini_widgets(lboard.asFen())
                    cls.board_control.emit("action", "SETUP", None, text)
                except SyntaxError as e:
                    d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.WARNING,
                                          buttons=Gtk.ButtonsType.OK,
                                          message_format=e.args[0])
                    if len(e.args) > 1:
                        d.format_secondary_text(e.args[1])
                    d.connect("response", lambda d, a: d.hide())
                    d.show()
                return
            elif response == INITIAL:
                lboard = cls.setupmodel.variant(setup=FEN_START).board
                cls.ini_widgets(lboard.asFen())
                cls.board_control.emit("action", "SETUP", None, FEN_START)
                return
            elif response != Gtk.ResponseType.OK:
                cls.widgets["newgamedialog"].hide()
                cls.widgets["newgamedialog"].disconnect(handlerId)
                return

            if hasattr(cls, "board_control"):
                cls.board_control.emit("action", "CLOSE", None, None)

            # Find variant
            if cls.widgets["playNormalRadio"].get_active():
                variant_index = NORMALCHESS
            elif cls.widgets["playVariant1Radio"].get_active():
                variant_index = conf.get("ngvariant1")
            else:
                variant_index = conf.get("ngvariant2")
            variant = variants[variant_index]

            # Find time
            if cls.widgets["notimeRadio"].get_active():
                secs = 0
                incr = 0
                moves = 0
            elif cls.widgets["blitzRadio"].get_active():
                secs = cls.ngblitz_min.get_value_as_int() * 60
                incr = cls.ngblitz_gain.get_value_as_int()
                moves = 0
            elif cls.widgets["rapidRadio"].get_active():
                secs = cls.ngrapid_min.get_value_as_int() * 60
                incr = cls.ngrapid_gain.get_value_as_int()
                moves = 0
            elif cls.widgets["normalRadio"].get_active():
                secs = cls.ngnormal_min.get_value_as_int() * 60
                incr = cls.ngnormal_gain.get_value_as_int()
                moves = 0
            elif cls.widgets["classicalRadio"].get_active():
                secs = cls.ngclassical_min.get_value_as_int() * 60
                incr = 0
                moves = cls.ngclassical_moves.get_value_as_int()

            # Find players
            player0combo = cls.widgets["whitePlayerCombobox"]
            player0 = player0combo.get_active()

            tree_iter = player0combo.get_active_iter()
            if tree_iter is not None:
                model = player0combo.get_model()
                name0 = model[tree_iter][1]

            diffi0 = int(cls.widgets["skillSlider1"].get_value())

            player1combo = cls.widgets["blackPlayerCombobox"]
            player1 = player1combo.get_active()

            tree_iter = player1combo.get_active_iter()
            if tree_iter is not None:
                model = player1combo.get_model()
                name1 = model[tree_iter][1]

            diffi1 = int(cls.widgets["skillSlider2"].get_value())

            # Prepare players
            playertups = []
            for i, playerno, name, diffi, color in ((0, player0, name0, diffi0, WHITE),
                                                    (1, player1, name1, diffi1, BLACK)):
                if playerno > 0:
                    engine = discoverer.getEngineByName(name)
                    playertups.append((ARTIFICIAL, discoverer.initPlayerEngine,
                                       [engine, color, diffi, variant, secs,
                                        incr, moves], name))
                else:
                    if not playertups or playertups[0][0] != LOCAL:
                        name = conf.get("firstName")
                    else:
                        name = conf.get("secondName")
                    playertups.append((LOCAL, Human, (color, name), name))

            # Set forcePonderOff initPlayerEngine param True in engine-engine games
            if playertups[0][0] == ARTIFICIAL and playertups[1][
                    0] == ARTIFICIAL:
                playertups[0][2].append(True)
                playertups[1][2].append(True)

            timemodel = TimeModel(secs, incr, moves=moves)
            gamemodel = GameModel(timemodel, variant)

            if not validate(gamemodel):
                return
            else:
                cls.widgets["newgamedialog"].hide()
                cls.widgets["newgamedialog"].disconnect(handlerId)
                callback(gamemodel, playertups[0], playertups[1])

        handlerId = cls.widgets["newgamedialog"].connect("response",
                                                         onResponse)
        cls.widgets["newgamedialog"].show()

    @classmethod
    def _hideOthers(cls):
        for extension in ("loadsidepanel", "enterGameNotationSidePanel",
                          "setupPositionSidePanel"):
            cls.widgets[extension].hide()
        for button in ("copy_button", "clear_button", "paste_button", "initial_button"):
            cls.widgets[button].hide()

# ###############################################################################
# NewGameMode                                                                  #
# ###############################################################################


class NewGameMode(_GameInitializationMode):
    @classmethod
    def _init(cls):
        # We have to override this, so the GameInitializationMode init method
        # isn't called twice
        pass

    @classmethod
    def run(cls):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return

        def _validate(gamemodel):
            return True

        cls._hideOthers()
        cls.widgets["newgamedialog"].set_title(_("New Game"))

        def _callback(gamemodel, p0, p1):
            perspective = perspective_manager.get_perspective("games")
            create_task(perspective.generalStart(gamemodel, p0, p1))

        cls._generalRun(_callback, _validate)

# ###############################################################################
# SetupPositionExtension                                                       #
# ###############################################################################


class SetupPositionExtension(_GameInitializationMode):
    board_control = None

    @classmethod
    def _init(cls):
        def callback(widget, allocation):
            cls.widgets["setupPositionFrame"].set_size_request(
                523, allocation.height - 4)

        cls.widgets["setupPositionSidePanel"].connect_after("size-allocate",
                                                            callback)

        cls.castl = set()

        cls.white = Gtk.Image.new_from_pixbuf(cls.white)
        cls.black = Gtk.Image.new_from_pixbuf(cls.black)
        cls.widgets["side_button"].set_image(cls.white)

        cls.widgets["side_button"].connect("toggled", cls.side_button_toggled)
        cls.widgets["rotate_button"].connect("button-press-event", cls.rotate_button_pressed)
        cls.widgets["moveno_spin"].connect("value-changed",
                                           cls.moveno_spin_changed)
        cls.widgets["fifty_spin"].connect("value-changed",
                                          cls.fifty_spin_changed)

        cls.widgets["woo"].connect("toggled", cls.castl_toggled, W_OO)
        cls.widgets["wooo"].connect("toggled", cls.castl_toggled, W_OOO)
        cls.widgets["boo"].connect("toggled", cls.castl_toggled, B_OO)
        cls.widgets["booo"].connect("toggled", cls.castl_toggled, B_OOO)

        ep_store = Gtk.ListStore(str)
        ep_store.append(["-"])
        for f in reprFile:
            ep_store.append([f])
        epcombo = cls.widgets["ep_combo"]
        epcombo.set_name("ep_combo")
        epcombo.set_model(ep_store)
        renderer_text = Gtk.CellRendererText()
        cls.widgets["ep_combo"].pack_start(renderer_text, True)
        cls.widgets["ep_combo"].add_attribute(renderer_text, "text", 0)
        cls.widgets["ep_combo"].set_active(0)
        cls.widgets["ep_combo"].connect("changed", cls.ep_combo_changed)

        cls.widgets["playNormalRadio"].connect("toggled", cls.fen_changed)
        cls.widgets["playVariant1Radio"].connect("toggled", cls.fen_changed)
        cls.widgets["playVariant2Radio"].connect("toggled", cls.fen_changed)

    @classmethod
    def side_button_toggled(cls, button):
        if button.get_active():
            button.set_image(cls.black)
        else:
            button.set_image(cls.white)
        cls.fen_changed()

    @classmethod
    def rotate_button_pressed(self, widget, button_event):
        view = self.board_control.view
        if view.rotation:
            view.rotation = 0
        else:
            view.rotation = pi

    @classmethod
    def fen_changed(cls, *args):
        cls.widgets["fen_entry"].set_text(cls.get_fen())

    @classmethod
    def game_changed(cls, model, ply):
        GLib.idle_add(cls.fen_changed)

    @classmethod
    def ep_combo_changed(cls, combo):
        cls.fen_changed()

    @classmethod
    def moveno_spin_changed(cls, spin):
        cls.fen_changed()

    @classmethod
    def fifty_spin_changed(cls, spin):
        cls.fen_changed()

    @classmethod
    def castl_toggled(cls, button, castl):
        lboard = cls.setupmodel.boards[-1].board
        # TODO: this doesn't work at all
        if lboard.variant == FISCHERRANDOMCHESS:
            if castl == W_OO:
                cast_letter = reprCord[lboard.ini_rooks[0][1]][0].upper()
            elif castl == W_OOO:
                cast_letter = reprCord[lboard.ini_rooks[0][0]][0].upper()
            elif castl == B_OO:
                cast_letter = reprCord[lboard.ini_rooks[1][1]][0]
            elif castl == B_OOO:
                cast_letter = reprCord[lboard.ini_rooks[1][0]][0]
        else:
            if castl == W_OO:
                cast_letter = "K"
            elif castl == W_OOO:
                cast_letter = "Q"
            elif castl == B_OO:
                cast_letter = "k"
            elif castl == B_OOO:
                cast_letter = "q"

        if button.get_active():
            cls.castl.add(cast_letter)
        else:
            cls.castl.discard(cast_letter)
        cls.fen_changed()

    @classmethod
    def get_fen(cls):
        # Find variant
        if cls.widgets["playNormalRadio"].get_active():
            variant_index = NORMALCHESS
        elif cls.widgets["playVariant1Radio"].get_active():
            variant_index = conf.get("ngvariant1")
        else:
            variant_index = conf.get("ngvariant2")
        variant = variants[variant_index]

        pieces = cls.setupmodel.boards[-1].as_fen(variant.variant)

        side = "b" if cls.widgets["side_button"].get_active() else "w"
        castl = "".join(sorted(cls.castl)) if cls.castl else "-"

        ep = "-"
        rank = "3" if side == "b" else "6"
        tree_iter = cls.widgets["ep_combo"].get_active_iter()
        if tree_iter is not None:
            model = cls.widgets["ep_combo"].get_model()
            ep = model[tree_iter][0]
        ep = ep if ep == "-" else ep + rank

        fifty = cls.widgets["fifty_spin"].get_value_as_int()
        moveno = cls.widgets["moveno_spin"].get_value_as_int()

        parts = (pieces, side, castl, ep, fifty, moveno)
        return "%s %s %s %s %s %s" % parts

    @classmethod
    def ini_widgets(cls, setup, lboard=None):
        if lboard is None:
            lboard = cls.setupmodel.variant(setup=setup).board
        cls.widgets["side_button"].set_active(False if lboard.color == WHITE
                                              else True)
        cls.widgets["fifty_spin"].set_value(lboard.fifty)
        cls.widgets["moveno_spin"].set_value(lboard.plyCount // 2 + 1)
        ep = lboard.enpassant
        cls.widgets["ep_combo"].set_active(0 if ep is None else FILE(ep) + 1)
        cls.widgets["woo"].set_active(lboard.castling & W_OO)
        cls.widgets["wooo"].set_active(lboard.castling & W_OOO)
        cls.widgets["boo"].set_active(lboard.castling & B_OO)
        cls.widgets["booo"].set_active(lboard.castling & B_OOO)

    @classmethod
    def run(cls, fenstr, variant):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return

        cls._hideOthers()
        for button in ("copy_button", "clear_button", "paste_button", "initial_button"):
            cls.widgets[button].show()
        cls.widgets["newgamedialog"].set_title(_("Setup Position"))
        cls.widgets["setupPositionSidePanel"].show()

        cls.setupmodel = SetupModel()
        cls.board_control = BoardControl(cls.setupmodel,
                                         {},
                                         setup_position=True)
        cls.setupmodel.curplayer = SetupPlayer(cls.board_control)
        cls.setupmodel.connect("game_changed", cls.game_changed)

        child = cls.widgets["setupBoardDock"].get_child()
        if child is not None:
            cls.widgets["setupBoardDock"].remove(child)
        cls.widgets["setupBoardDock"].add(cls.board_control)
        cls.board_control.show_all()
        if fenstr is not None:
            lboard = LBoard(variant)
            lboard.applyFen(fenstr)
            cls.setupmodel.boards = [cls.setupmodel.variant(setup=fenstr, lboard=lboard)]
            cls.setupmodel.variations = [cls.setupmodel.boards]
            cls.ini_widgets(fenstr, lboard)
        else:
            fenstr = cls.get_fen()
            cls.ini_widgets(True)
        cls.widgets["fen_entry"].set_text(fenstr)

        cls.setupmodel.start()
        cls.board_control.emit("action", "SETUP", None, fenstr)

        def _validate(gamemodel):
            try:
                fenstr = cls.get_fen()
                cls.setupmodel.variant(setup=fenstr)
                return True
            except (AssertionError, LoadingError, SyntaxError) as e:
                d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.WARNING,
                                      buttons=Gtk.ButtonsType.OK,
                                      message_format=e.args[0])
                if len(e.args) > 1:
                    d.format_secondary_text(e.args[1])
                d.connect("response", lambda d, a: d.hide())
                d.show()
                return False

        def _callback(gamemodel, p0, p1):
            text = cls.get_fen()
            perspective = perspective_manager.get_perspective("games")
            create_task(perspective.generalStart(
                gamemodel, p0, p1, (StringIO(text), fen, 0, -1)))

        cls._generalRun(_callback, _validate)

# ###############################################################################
# EnterNotationExtension                                                       #
# ###############################################################################


class EnterNotationExtension(_GameInitializationMode):
    @classmethod
    def _init(cls):
        def callback(widget, allocation):
            cls.widgets["enterGameNotationFrame"].set_size_request(
                223, allocation.height - 4)

        cls.widgets["enterGameNotationSidePanel"].connect_after(
            "size-allocate", callback)

        flags = []
        if isInstalled():
            path = gettext.find("pychess")
        else:
            path = gettext.find("pychess", localedir=addDataPrefix("lang"))
        if path:
            default_locale = locale.getdefaultlocale()
            if default_locale[0] is not None:
                loc = locale.getdefaultlocale()[0][-2:].lower()
                flags.append(addDataPrefix("flags/%s.png" % loc))

        flags.append(addDataPrefix("flags/us.png"))

        cls.ib = ImageButton(flags)
        cls.widgets["imageButtonDock"].add(cls.ib)
        cls.ib.show()

        cls.sourcebuffer = GtkSource.Buffer()
        sourceview = GtkSource.View.new_with_buffer(cls.sourcebuffer)
        sourceview.set_tooltip_text(_(
            "Type or paste PGN game or FEN positions here"))
        cls.widgets["scrolledwindow6"].add(sourceview)
        sourceview.show()

        # Pgn format does not allow tabulator
        sourceview.set_insert_spaces_instead_of_tabs(True)
        sourceview.set_wrap_mode(Gtk.WrapMode.WORD)

        man = GtkSource.LanguageManager()
        # Init new version
        if hasattr(man.props, 'search_path'):
            try:
                path = os.path.join(getDataPrefix(),
                                    "gtksourceview-3.0/language-specs")
                man.props.search_path = man.props.search_path + [path]
                if 'pgn' in man.get_language_ids():
                    lang = man.get_language('pgn')
                    cls.sourcebuffer.set_language(lang)
                else:
                    log.warning("Unable to load pgn syntax-highlighting.")
                cls.sourcebuffer.set_highlight_syntax(True)
            except NotImplementedError:
                # Python 2.7.3 in Ubuntu 12.04
                log.warning("Unable to load pgn syntax-highlighting.")
        # Init old version
        else:
            os.environ["XDG_DATA_DIRS"] = getDataPrefix() + ":/usr/share/"
            man = GtkSource.LanguageManager()
            for lang in man.get_available_languages():
                if lang.get_name() == "PGN":
                    cls.sourcebuffer.set_language(lang)
                    break
            else:
                log.warning("Unable to load pgn syntax-highlighting.")
            cls.sourcebuffer.set_highlight(True)

    @classmethod
    def run(cls):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return

        cls._hideOthers()
        cls.widgets["newgamedialog"].set_title(_("Enter Game"))
        cls.widgets["enterGameNotationSidePanel"].show()

        def _get_text():
            text = cls.sourcebuffer.get_text(cls.sourcebuffer.get_start_iter(),
                                             cls.sourcebuffer.get_end_iter(),
                                             False)

            # Test if the ImageButton has two layers and is set on the local language
            if len(cls.ib.surfaces) == 2 and cls.ib.current == 0:
                # 2 step used to avoid backtranslating
                # (local and english piece letters can overlap)
                for i, sign in enumerate(localReprSign[1:]):
                    if sign.strip():
                        text = text.replace(sign, FAN_PIECES[0][i + 1])
                for i, sign in enumerate(FAN_PIECES[0][1:7]):
                    text = text.replace(sign, reprSign[i + 1])
                text = str(text)

            # First we try if it's just a FEN string
            parts_no = len(text.split())
            if text.strip() == "":
                text = FEN_START
                loadType = fen
            elif parts_no > 0 and text.split()[0].count("/") == 7:
                loadType = fen
            else:
                # patch default human player names on demand...
                player0combo = cls.widgets["whitePlayerCombobox"]
                player0 = player0combo.get_active()
                if player0 == 0 and '[White "' not in text:
                    name = '[White "%s"]' % conf.get("firstName")
                    text = "%s\n%s" % (name, text)

                player1combo = cls.widgets["blackPlayerCombobox"]
                player1 = player1combo.get_active()
                if player1 == 0 and '[Black "' not in text:
                    name = '[Black "%s"]' % conf.get("secondName")
                    text = "%s\n%s" % (name, text)

                loadType = pgn

            return text, loadType

        def _validate(gamemodel):
            try:
                text, loadType = _get_text()
                chessfile = loadType.load(StringIO(text))
                chessfile.loadToModel(chessfile.games[0], -1, model=gamemodel)
                gamemodel.status = WAITING_TO_START
                return True
            except LoadingError as e:
                d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.WARNING,
                                      buttons=Gtk.ButtonsType.OK,
                                      message_format=e.args[0])
                d.format_secondary_text(e.args[1])
                d.connect("response", lambda d, a: d.hide())
                d.show()
                return False

        def _callback(gamemodel, p0, p1):
            text, loadType = _get_text()
            perspective = perspective_manager.get_perspective("games")
            create_task(perspective.generalStart(
                gamemodel, p0, p1, (StringIO(text), loadType, 0, -1)))

        cls._generalRun(_callback, _validate)


class ImageButton(Gtk.Button):
    def __init__(self, image_paths):
        GObject.GObject.__init__(self)

        self.surfaces = [Gtk.Image().new_from_file(path)
                         for path in image_paths]
        self.current = 0

        self.image = self.surfaces[self.current]
        self.image.show()
        self.add(self.image)

        self.connect("clicked", self.on_clicked)

    def on_clicked(self, button):
        self.current = (self.current + 1) % len(self.surfaces)
        self.remove(self.image)
        self.image = self.surfaces[self.current]
        self.image.show()
        self.add(self.image)


def createRematch(gamemodel):
    """ If gamemodel contains only LOCAL or ARTIFICIAL players, this starts a
        new game, based on the info in gamemodel """

    if gamemodel.timed:
        secs = gamemodel.timemodel.intervals[0][WHITE]
        gain = gamemodel.timemodel.gain
        moves = gamemodel.timemodel.moves
    else:
        secs = 0
        gain = 0
        moves = 0
    newgamemodel = GameModel(TimeModel(secs, gain), variant=gamemodel.variant)

    wp = gamemodel.players[WHITE]
    bp = gamemodel.players[BLACK]

    if wp.__type__ == LOCAL:
        player1tup = (wp.__type__, wp.__class__, (BLACK, repr(wp)), repr(wp))
        if bp.__type__ == LOCAL:
            player0tup = (bp.__type__, bp.__class__,
                          (WHITE, repr(wp)), repr(bp))
        else:
            engine = discoverer.getEngineByMd5(bp.md5)
            player0tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                          (engine, WHITE, bp.strength, gamemodel.variant, secs,
                           gain, moves), repr(bp))
    else:
        player0tup = (bp.__type__, bp.__class__, (WHITE, repr(bp)), repr(bp))
        engine = discoverer.getEngineByMd5(wp.md5)
        player1tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                      (engine, BLACK, wp.strength, gamemodel.variant, secs,
                       gain), repr(wp))

    perspective = perspective_manager.get_perspective("games")
    create_task(perspective.generalStart(newgamemodel, player0tup, player1tup))


def loadFileAndRun(uri):
    parts = splitUri(uri)
    uri = parts[1] if len(parts) == 2 else parts[0]
    loader = enddir[uri[uri.rfind(".") + 1:]]
    timemodel = TimeModel(0, 0)
    gamemodel = GameModel(timemodel)
    white_name = _("White")
    black_name = _("Black")
    p0 = (LOCAL, Human, (WHITE, white_name), white_name)
    p1 = (LOCAL, Human, (BLACK, black_name), black_name)
    perspective = perspective_manager.get_perspective("games")
    create_task(perspective.generalStart(gamemodel, p0, p1, (uri, loader, 0, -1)))
