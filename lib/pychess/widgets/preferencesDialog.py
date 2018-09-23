# -*- coding: UTF-8 -*-

""" :Description: This module facilitates configurable object that the end user can
    customise such as which chess setor board colours to use or the ability to turn on/off
    various sidepanel facilities such as hints, comments engine analysis etc. It also allows
    the user to setup and use customised sounds or no sounds at all for a variety of in game
    events such as running out of time or piece movement events etc.
"""

import os
from os import listdir
from os.path import isdir, isfile, splitext

import sys
from xml.dom import minidom
from urllib.request import url2pathname, pathname2url
from urllib.parse import unquote

from gi.repository import Gtk, GdkPixbuf, Gdk

from pychess.compat import create_task
from pychess.System.prefix import addDataPrefix
from pychess.System import conf, gstreamer, uistuff
from pychess.Players.engineNest import discoverer
from pychess.Utils import book
from pychess.Utils.const import HINT, SPY, SOUND_MUTE, SOUND_BEEP, SOUND_URI, SOUND_SELECT, COUNT_OF_SOUNDS
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.gfx import Pieces
from pychess.widgets import mainwindow
from pychess.widgets.Background import newTheme
from pychess.perspectives import perspective_manager


firstRun = True

general_tab = None
hint_tab = None
theme_tab = None
sound_tab = None
save_tab = None


def run(widgets):
    global firstRun
    if firstRun:
        initialize(widgets)
        firstRun = False
    else:
        widgets["preferences_dialog"].show()
        widgets["preferences_dialog"].present()


def initialize(widgets):
    """ :Description: Initialises the various tabs for each section of configurable artifacts
    """
    global general_tab
    general_tab = GeneralTab(widgets)

    # All side panels can be show/hide from View menu now, so no need to do the same from preferences
    # We can re enable this after implementing install/uninstall functionality in the future...
    # PanelTab(widgets)

    uistuff.keepWindowSize("preferencesdialog", widgets["preferences_dialog"])

    notebook = widgets["preferences_notebook"]

    def switch_page(widget, page, page_num):
        global hint_tab, theme_tab, sound_tab, save_tab

        if page_num == 1 and hint_tab is None:
            hint_tab = HintTab(widgets)
        elif page_num == 3 and theme_tab is None:
            theme_tab = ThemeTab(widgets)
        elif page_num == 4 and sound_tab is None:
            sound_tab = SoundTab(widgets)
        elif page_num == 5 and save_tab is None:
            save_tab = SaveTab(widgets)

    notebook.connect("switch_page", switch_page)

    def delete_event(widget, _):
        widgets["preferences_dialog"].hide()
        return True

    widgets["preferences_dialog"].connect("delete-event", delete_event)
    widgets["preferences_dialog"].connect(
        "key-press-event",
        lambda w, e: w.event(Gdk.Event(Gdk.EventType.DELETE)) if e.keyval == Gdk.KEY_Escape else None)

# General initing


class GeneralTab:
    def __init__(self, widgets):

        # Give to uistuff.keeper
        for key in conf.DEFAULTS["General"]:
            # widgets having special getter/setter
            if key in ("ana_combobox", "inv_ana_combobox", "pieceTheme", "board_style", "board_frame"):
                continue

            try:
                if widgets[key] is not None:
                    uistuff.keep(widgets[key], key)
            except AttributeError:
                print("GeneralTab AttributeError", key, conf.DEFAULTS["General"][key])
            except TypeError:
                print("GeneralTab TypeError", key, conf.DEFAULTS["General"][key])

# Hint initing


def anal_combo_get_value(combobox):
    engine = list(discoverer.getAnalyzers())[combobox.get_active()]
    return engine.get("md5")


def anal_combo_set_value(combobox, value, show_arrow_check, analyzer_type):
    engine = discoverer.getEngineByMd5(value)
    if engine is None:
        combobox.set_active(0)
        # This return saves us from the None-engine being used
        # in later code  -Jonas Thiem
        return
    else:
        try:
            index = list(discoverer.getAnalyzers()).index(engine)
        except ValueError:
            index = 0
        combobox.set_active(index)

    from pychess.widgets.gamewidget import widgets
    perspective = perspective_manager.get_perspective("games")
    for gmwidg in perspective.gamewidgets:
        spectators = gmwidg.gamemodel.spectators
        md5 = engine.get('md5')

        if analyzer_type in spectators and \
                spectators[analyzer_type].md5 != md5:
            gmwidg.gamemodel.remove_analyzer(analyzer_type)
            create_task(gmwidg.gamemodel.start_analyzer(analyzer_type))
            if not widgets[show_arrow_check].get_active():
                gmwidg.gamemodel.pause_analyzer(analyzer_type)


class HintTab:
    def __init__(self, widgets):
        self.widgets = widgets

        # Opening book
        path = conf.get("opening_file_entry")
        conf.set("opening_file_entry", path)

        book_chooser_dialog = Gtk.FileChooserDialog(
            _("Select book file"), mainwindow(), Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.OK))
        book_chooser_button = Gtk.FileChooserButton.new_with_dialog(
            book_chooser_dialog)

        filter = Gtk.FileFilter()
        filter.set_name(_("Opening books"))
        filter.add_pattern("*.bin")
        book_chooser_dialog.add_filter(filter)
        book_chooser_button.set_filename(path)

        self.widgets["bookChooserDock"].add(book_chooser_button)
        book_chooser_button.show()

        def select_new_book(button):
            new_book = book_chooser_dialog.get_filename()
            if new_book:
                conf.set("opening_file_entry", new_book)
                book.path = new_book
            else:
                # restore the original
                book_chooser_dialog.set_filename(path)

        book_chooser_button.connect("file-set", select_new_book)

        def on_opening_check_toggled(check):
            self.widgets["opening_hbox"].set_sensitive(check.get_active())

        self.widgets["opening_check"].connect_after("toggled",
                                                    on_opening_check_toggled)

        uistuff.keep(self.widgets["book_depth_max"], "book_depth_max")

        # Endgame
        egtb_path = conf.get("egtb_path")
        conf.set("egtb_path", egtb_path)

        egtb_chooser_dialog = Gtk.FileChooserDialog(
            _("Select Gaviota TB path"), mainwindow(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.OK))
        egtb_chooser_button = Gtk.FileChooserButton.new_with_dialog(
            egtb_chooser_dialog)
        egtb_chooser_button.set_current_folder(egtb_path)

        self.widgets["egtbChooserDock"].add(egtb_chooser_button)
        egtb_chooser_button.show()

        def select_egtb(button):
            new_directory = egtb_chooser_dialog.get_filename()
            if new_directory != egtb_path:
                conf.set("egtb_path", new_directory)

        egtb_chooser_button.connect("current-folder-changed", select_egtb)

        def on_endgame_check_toggled(check):
            self.widgets["endgame_hbox"].set_sensitive(check.get_active())

        self.widgets["endgame_check"].connect_after("toggled",
                                                    on_endgame_check_toggled)

        # Analyzing engines
        from pychess.widgets import newGameDialog
        data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
        uistuff.createCombo(widgets["ana_combobox"], data, name="ana_combobox")
        uistuff.createCombo(widgets["inv_ana_combobox"], data, name="inv_ana_combobox")

        def update_analyzers_store(discoverer):
            data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
            uistuff.updateCombo(widgets["ana_combobox"], data)
            uistuff.updateCombo(widgets["inv_ana_combobox"], data)

        discoverer.connect_after("all_engines_discovered",
                                 update_analyzers_store)
        update_analyzers_store(discoverer)

        # Save, load and make analyze combos active

        conf.set("ana_combobox", conf.get("ana_combobox"))
        conf.set("inv_ana_combobox", conf.get("inv_ana_combobox"))

        def on_analyzer_check_toggled(check):
            self.widgets["analyzers_vbox"].set_sensitive(check.get_active())
            from pychess.widgets.gamewidget import widgets
            perspective = perspective_manager.get_perspective("games")
            if len(perspective.gamewidgets) != 0:
                if check.get_active():
                    for gmwidg in perspective.gamewidgets:
                        create_task(gmwidg.gamemodel.restart_analyzer(HINT))
                        if not widgets["hint_mode"].get_active():
                            gmwidg.gamemodel.pause_analyzer(HINT)
                else:
                    for gmwidg in perspective.gamewidgets:
                        gmwidg.gamemodel.remove_analyzer(HINT)

        self.widgets["analyzers_vbox"].set_sensitive(widgets["analyzer_check"].get_active())
        self.widgets["analyzer_check"].connect_after("toggled", on_analyzer_check_toggled)

        def on_invanalyzer_check_toggled(check):
            self.widgets["inv_analyzers_vbox"].set_sensitive(check.get_active())
            perspective = perspective_manager.get_perspective("games")
            if len(perspective.gamewidgets) != 0:
                if check.get_active():
                    for gmwidg in perspective.gamewidgets:
                        create_task(gmwidg.gamemodel.restart_analyzer(SPY))
                        if not widgets["spy_mode"].get_active():
                            gmwidg.gamemodel.pause_analyzer(SPY)
                else:
                    for gmwidg in perspective.gamewidgets:
                        gmwidg.gamemodel.remove_analyzer(SPY)

        self.widgets["inv_analyzers_vbox"].set_sensitive(widgets["inv_analyzer_check"].get_active())
        self.widgets["inv_analyzer_check"].connect_after("toggled", on_invanalyzer_check_toggled)

        # Give widgets to keeper

        uistuff.keep(
            self.widgets["ana_combobox"], "ana_combobox", anal_combo_get_value,
            lambda combobox, value: anal_combo_set_value(combobox, value, "hint_mode", HINT))
        uistuff.keep(
            self.widgets["inv_ana_combobox"], "inv_ana_combobox",
            anal_combo_get_value,
            lambda combobox, value: anal_combo_set_value(combobox, value, "spy_mode", SPY))

        uistuff.keep(self.widgets["max_analysis_spin"], "max_analysis_spin")
        uistuff.keep(self.widgets["infinite_analysis"], "infinite_analysis")


# Sound initing

# Setup default sounds
EXT = "wav" if sys.platform == "win32" else "ogg"

for i in range(COUNT_OF_SOUNDS):
    if not conf.hasKey("soundcombo%d" % i):
        conf.set("soundcombo%d" % i, SOUND_URI)

if not conf.hasKey("sounduri0"):
    conf.set("sounduri0",
             "file:" + pathname2url(addDataPrefix("sounds/move1.%s" % EXT)))
if not conf.hasKey("sounduri1"):
    conf.set("sounduri1",
             "file:" + pathname2url(addDataPrefix("sounds/check1.%s" % EXT)))
if not conf.hasKey("sounduri2"):
    conf.set("sounduri2",
             "file:" + pathname2url(addDataPrefix("sounds/capture1.%s" % EXT)))
if not conf.hasKey("sounduri3"):
    conf.set("sounduri3",
             "file:" + pathname2url(addDataPrefix("sounds/start1.%s" % EXT)))
if not conf.hasKey("sounduri4"):
    conf.set("sounduri4",
             "file:" + pathname2url(addDataPrefix("sounds/win1.%s" % EXT)))
if not conf.hasKey("sounduri5"):
    conf.set("sounduri5",
             "file:" + pathname2url(addDataPrefix("sounds/lose1.%s" % EXT)))
if not conf.hasKey("sounduri6"):
    conf.set("sounduri6",
             "file:" + pathname2url(addDataPrefix("sounds/draw1.%s" % EXT)))
if not conf.hasKey("sounduri7"):
    conf.set("sounduri7",
             "file:" + pathname2url(addDataPrefix("sounds/obs_mov.%s" % EXT)))
if not conf.hasKey("sounduri8"):
    conf.set("sounduri8",
             "file:" + pathname2url(addDataPrefix("sounds/obs_end.%s" % EXT)))
if not conf.hasKey("sounduri9"):
    conf.set("sounduri9",
             "file:" + pathname2url(addDataPrefix("sounds/alarm.%s" % EXT)))
if not conf.hasKey("sounduri10"):
    conf.set("sounduri10",
             "file:" + pathname2url(addDataPrefix("sounds/invalid.%s" % EXT)))
if not conf.hasKey("sounduri11"):
    conf.set("sounduri11",
             "file:" + pathname2url(addDataPrefix("sounds/success.%s" % EXT)))
if not conf.hasKey("sounduri12"):
    conf.set("sounduri12",
             "file:" + pathname2url(addDataPrefix("sounds/choice.%s" % EXT)))


class SoundTab:

    SOUND_DIRS = (addDataPrefix("sounds"), "/usr/share/sounds",
                  "/usr/local/share/sounds", os.path.expanduser("~"))

    actionToKeyNo = {
        "aPlayerMoves": 0,
        "aPlayerChecks": 1,
        "aPlayerCaptures": 2,
        "gameIsSetup": 3,
        "gameIsWon": 4,
        "gameIsLost": 5,
        "gameIsDrawn": 6,
        "observedMoves": 7,
        "oberservedEnds": 8,
        "shortOnTime": 9,
        "invalidMove": 10,
        "puzzleSuccess": 11,
        "variationChoice": 12,
    }

    _player = None
    useSounds = conf.get("useSounds")

    soundcombo = []
    sounduri = []
    for i in range(COUNT_OF_SOUNDS):
        soundcombo.append(conf.get("soundcombo%s" % i))
        sounduri.append(conf.get("sounduri%s" % i))

    @classmethod
    def getPlayer(cls):
        if not cls._player:
            cls._player = gstreamer.sound_player
        return cls._player

    @classmethod
    def playAction(cls, action):
        if not cls.useSounds:
            return

        if isinstance(action, str):
            key_no = cls.actionToKeyNo[action]
        else:
            key_no = action
        typ = cls.soundcombo[key_no]
        if typ == SOUND_BEEP:
            sys.stdout.write("\a")
            sys.stdout.flush()
        elif typ == SOUND_URI:
            uri = cls.sounduri[key_no]
            if not os.path.isfile(url2pathname(uri[5:])):
                conf.set("soundcombo%d" % key_no, SOUND_MUTE)
                return
            cls.getPlayer().play(uri)

    def __init__(self, widgets):

        # Init open dialog

        opendialog = Gtk.FileChooserDialog(
            _("Open Sound File"), mainwindow(), Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.ACCEPT))

        for dir in self.SOUND_DIRS:
            if os.path.isdir(dir):
                opendialog.set_current_folder(dir)
                break

        soundfilter = Gtk.FileFilter()
        soundfilter.set_name(_("Sound files"))
        soundfilter.add_mime_type("audio/%s" % EXT)
        soundfilter.add_pattern("*.%s" % EXT)
        opendialog.add_filter(soundfilter)

        # Get combo icons

        icons = ((_("No sound"), "audio-volume-muted", "audio-volume-muted"),
                 (_("Beep"), "stock_bell", "audio-x-generic"),
                 (_("Select sound file..."), "gtk-open", "document-open"))

        items = []
        for level, stock, altstock in icons:
            image = load_icon(16, stock, altstock)
            items += [(image, level)]

        audioIco = load_icon(16, "audio-x-generic")

        # Set-up combos

        def callback(combobox, index):
            if combobox.get_active() == SOUND_SELECT:
                if opendialog.run() == Gtk.ResponseType.ACCEPT:
                    uri = opendialog.get_uri()
                    model = combobox.get_model()
                    conf.set("sounduri%d" % index, uri)
                    self.sounduri[index] = uri
                    label = unquote(os.path.split(uri)[1])
                    if len(model) == 3:
                        model.append([audioIco, label])
                    else:
                        model.set(model.get_iter((3, )), 1, label)
                    combobox.set_active(3)
                else:
                    combobox.set_active(conf.get("soundcombo%d" % index))
                opendialog.hide()

        for i in range(COUNT_OF_SOUNDS):
            combo = widgets["sound%dcombo" % i]
            uistuff.createCombo(combo, items, name="soundcombo%d" % i)
            combo.connect("changed", callback, i)

            label = widgets["soundlabel%d" % i]
            label.props.mnemonic_widget = combo

            uri = conf.get("sounduri%d" % i)
            if os.path.isfile(url2pathname(uri[5:])):
                model = combo.get_model()
                model.append([audioIco, unquote(os.path.split(uri)[1])])

        for i in range(COUNT_OF_SOUNDS):
            if conf.get("soundcombo%d" % i) == SOUND_URI and \
                    not os.path.isfile(url2pathname(conf.get("sounduri%d" % i)[5:])):
                conf.set("soundcombo%d" % i, SOUND_MUTE)
            uistuff.keep(widgets["sound%dcombo" % i], "soundcombo%d" % i)

        # Init play button

        def playCallback(button, index):
            SoundTab.playAction(index)

        for i in range(COUNT_OF_SOUNDS):
            button = widgets["sound%dbutton" % i]
            button.connect("clicked", playCallback, i)

        # Init 'use sound" checkbutton

        def checkCallBack(*args):
            checkbox = widgets["useSounds"]
            widgets["sounds_frame"].set_property("sensitive", checkbox.get_active())
            self.useSounds = conf.get("useSounds")

        conf.notify_add("useSounds", checkCallBack)
        widgets["useSounds"].set_active(True)
        uistuff.keep(widgets["useSounds"], "useSounds")
        checkCallBack()

        if not self.getPlayer().ready:
            widgets["useSounds"].set_sensitive(False)
            widgets["useSounds"].set_active(False)

# Panel initing


class PanelTab:
    def __init__(self, widgets):
        # Put panels in trees
        self.widgets = widgets
        persp = perspective_manager.get_perspective("games")
        sidePanels = persp.sidePanels
        dockLocation = persp.dockLocation

        saved_panels = []
        xmlOK = os.path.isfile(dockLocation)
        if xmlOK:
            doc = minidom.parse(dockLocation)
            for elem in doc.getElementsByTagName("panel"):
                saved_panels.append(elem.getAttribute("id"))

        store = Gtk.ListStore(bool, GdkPixbuf.Pixbuf, str, object)
        for panel in sidePanels:
            checked = True if not xmlOK else panel.__name__ in saved_panels
            panel_icon = get_pixbuf(panel.__icon__, 32)
            text = "<b>%s</b>\n%s" % (panel.__title__, panel.__desc__)
            store.append((checked, panel_icon, text, panel))

        self.tv = widgets["panels_treeview"]
        self.tv.set_model(store)

        self.widgets['panel_about_button'].connect('clicked', self.panel_about)
        self.widgets['panel_enable_button'].connect('toggled',
                                                    self.panel_toggled)
        self.tv.get_selection().connect('changed', self.selection_changed)

        pixbuf = Gtk.CellRendererPixbuf()
        pixbuf.props.yalign = 0
        pixbuf.props.ypad = 3
        pixbuf.props.xpad = 3
        self.tv.append_column(Gtk.TreeViewColumn("Icon",
                                                 pixbuf,
                                                 pixbuf=1,
                                                 sensitive=0))

        uistuff.appendAutowrapColumn(self.tv, "Name", markup=2, sensitive=0)

        widgets['preferences_notebook'].connect("switch-page", self.__on_switch_page)
        widgets["preferences_dialog"].connect("show", self.__on_show_window)
        widgets["preferences_dialog"].connect("hide", self.__on_hide_window)

    def selection_changed(self, treeselection):
        store, iter = self.tv.get_selection().get_selected()
        self.widgets['panel_enable_button'].set_sensitive(bool(iter))
        self.widgets['panel_about_button'].set_sensitive(bool(iter))

        if iter:
            active = self.tv.get_model().get(iter, 0)[0]
            self.widgets['panel_enable_button'].set_active(active)

    def panel_about(self, button):
        store, iter = self.tv.get_selection().get_selected()
        assert iter  # The button should only be clickable when we have a selection
        path = store.get_path(iter)
        panel = store[path][3]

        d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.INFO,
                              buttons=Gtk.ButtonsType.CLOSE)
        d.set_markup("<big><b>%s</b></big>" % panel.__title__)
        text = panel.__about__ if hasattr(
            panel, '__about__') else _('Undescribed panel')
        d.format_secondary_text(text)
        d.run()
        d.hide()

    def panel_toggled(self, button):
        store, iter = self.tv.get_selection().get_selected()
        assert iter  # The button should only be clickable when we have a selection
        path = store.get_path(iter)
        active = button.get_active()
        if store[path][0] == active:
            return

        store[path][0] = active
        self.__set_panel_active(store[path][3], active)

    def __set_panel_active(self, panel, active):
        name = panel.__name__

        from pychess.widgets.pydock import EAST

        persp = perspective_manager.get_perspective("games")
        if active:
            leaf = persp.notebooks["board"].get_parent().get_parent()
            leaf.dock(persp.docks[name][1], EAST, persp.docks[name][0], name)
            panel.menu_item.show()
        else:
            try:
                persp.notebooks[name].get_parent().get_parent().undock(persp.notebooks[name])
                panel.menu_item.hide()
            except AttributeError:
                # A new panel appeared in the panels directory
                leaf = persp.notebooks["board"].get_parent().get_parent()
                leaf.dock(persp.docks[name][1], EAST, persp.docks[name][0], name)

    def showit(self):
        from pychess.widgets.gamewidget import showDesignGW
        showDesignGW()

    def hideit(self):
        from pychess.widgets.gamewidget import hideDesignGW
        hideDesignGW()

    def __on_switch_page(self, notebook, page, page_num):
        if notebook.get_nth_page(page_num) == self.widgets['sidepanels']:
            self.showit()
        else:
            self.hideit()

    def __on_show_window(self, widget):
        notebook = self.widgets['preferences_notebook']
        page_num = notebook.get_current_page()
        if notebook.get_nth_page(page_num) == self.widgets['sidepanels']:
            self.showit()

    def __on_hide_window(self, widget):
        self.hideit()


# Theme initing

board_items = [(None, "colors only")]
boards_path = addDataPrefix("boards")
board_items += [(get_pixbuf(os.path.join(boards_path, b), 24), b[:-6]) for b in listdir(boards_path) if b.endswith("_d.png")]


class ThemeTab:
    """ :Description: Allows the setting of various user specific chess
        sets and board colours
    """
    def __init__(self, widgets):
        self.widgets = widgets

        # Font chooser
        font = conf.get("movetextFont")
        font_button = Gtk.FontButton.new_with_font(font)
        demo_text = "♔a1 ♕f8 ♖h8 ♗g7 ♘g2 Ka1 Qf8 Rh8 Bg7 Ng2"
        font_button.set_preview_text(demo_text)
        self.widgets["fontChooserDock"].add(font_button)
        font_button.show()

        def select_font(button):
            conf.set("movetextFont", button.get_font_name())
        font_button.connect("font-set", select_font)

        # Background image
        path = conf.get("welcome_image")
        conf.set("welcome_image", path)

        image_chooser_dialog = Gtk.FileChooserDialog(
            _("Select background image file"), mainwindow(), Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.OK))
        image_chooser_button = Gtk.FileChooserButton.new_with_dialog(
            image_chooser_dialog)

        filter = Gtk.FileFilter()
        filter.set_name(_("Images"))
        filter.add_pattern("*.bmp")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.png")
        filter.add_pattern("*.svg")
        image_chooser_dialog.add_filter(filter)
        image_chooser_button.set_filename(path)

        self.widgets["imageChooserDock"].add(image_chooser_button)
        image_chooser_button.show()

        def select_new_image(button):
            new_image = image_chooser_dialog.get_filename()
            if new_image:
                conf.set("welcome_image", new_image)
                from pychess.widgets.TaskerManager import tasker
                newTheme(tasker, background=new_image)
                tasker.queue_draw()
            else:
                # restore the original
                image_chooser_dialog.set_filename(path)

        image_chooser_button.connect("file-set", select_new_image)

        # Board style
        uistuff.createCombo(widgets["board_style"], name="board_style")
        data = [(item[0], item[1]) for item in board_items]

        uistuff.createCombo(widgets["board_style"], data)
        uistuff.keep(widgets["board_style"], "board_style")

        # conf.set("board_style", conf.get("board_style"))

        # Board frame
        uistuff.createCombo(widgets["board_frame"], name="board_frame")
        data = [(item[0], item[1]) for item in [(None, "no frame")] + board_items[1:]]

        uistuff.createCombo(widgets["board_frame"], data)
        uistuff.keep(widgets["board_frame"], "board_frame")

        # conf.set("board_frame", conf.get("board_frame"))

        # Board Colours

        def onColourSetLight(_):
            """ :Description: Sets the light squares of the chess board
                to the value selected in the colour picker
            """
            conf.set('lightcolour',
                     widgets['light_cbtn'].get_color().to_string())

        widgets["light_cbtn"].connect_after("color-set", onColourSetLight)

        def onColourSetDark(_):
            """ :Description: Sets the dark squares of the chess board
                to the value selected in the colour picker
            """
            conf.set('darkcolour',
                     widgets['dark_cbtn'].get_color().to_string())

        widgets["dark_cbtn"].connect_after("color-set", onColourSetDark)

        def onResetColourClicked(_):
            """ :Description: Resets the chess board squares to factory default
            """
            conf.set("lightcolour", conf.get("lightcolour"))
            conf.set("darkcolour", conf.get("darkcolour"))

        widgets["reset_btn"].connect("clicked", onResetColourClicked)

        # Get the current board colours if set, if not set, set them to default
        conf.set("lightcolour", conf.get("lightcolour"))
        conf.set("darkcolour", conf.get("darkcolour"))

        # Next 2 lines take a #hex str converts them to a color then to a RGBA representation
        self.lightcolour = Gdk.RGBA()
        self.lightcolour.parse(conf.get("lightcolour"))
        self.darkcolour = Gdk.RGBA()
        self.darkcolour.parse(conf.get("darkcolour"))

        # Set the color swatches in preference to stored values
        widgets['light_cbtn'].set_rgba(self.lightcolour)
        widgets['dark_cbtn'].set_rgba(self.darkcolour)

        # Chess Sets

        self.themes = self.discoverThemes()
        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

        for theme in self.themes:
            pngfile = "%s/%s.png" % (addDataPrefix("pieces"), theme)

            if isfile(pngfile):
                pixbuf = get_pixbuf(pngfile)
                store.append((pixbuf, theme))
            else:
                print(
                    "WARNING: No piece theme preview icons found. Please run \
                    create_theme_preview.sh !")
                break

        self.icon_view = widgets["pieceTheme"]
        self.icon_view.set_model(store)
        self.icon_view.set_pixbuf_column(0)
        self.icon_view.set_text_column(1)

        def keepSize(crt, _):
            """ :Description: Hack to fix spacing problem in iconview
                http://stackoverflow.com/questions/14090094/what-causes-the-different-\
                    display-behaviour-for-a-gtkiconview-between-different
            """
            crt.handler_block(crt_notify)
            crt.set_property('width', 40)
            crt.handler_unblock(crt_notify)

        crt = self.icon_view.get_cells()[0]
        crt_notify = crt.connect('notify', keepSize)

        def _getActive(iconview):
            model = iconview.get_model()
            selected = iconview.get_selected_items()

            if len(selected) == 0:
                return conf.get("pieceTheme")

            indices = selected[0].get_indices()
            if indices:
                idx = indices[0]
                theme = model[idx][1]
                Pieces.set_piece_theme(theme)
                return theme

        def _setActive(iconview, value):
            try:
                index = self.themes.index(value)
            except ValueError:
                index = 0
            iconview.select_path(Gtk.TreePath(index, ))

        uistuff.keep(widgets["pieceTheme"], "pieceTheme", _getActive, _setActive)

    def discoverThemes(self):
        """ :Description: Finds all the different chess sets that are present
            in the pieces directory

            :return: (a List) of themes
        """
        themes = ['Pychess']

        pieces = addDataPrefix("pieces")
        themes += [d.capitalize()
                   for d in listdir(pieces)
                   if isdir(os.path.join(pieces, d)) and d != 'ttf']

        ttf = addDataPrefix("pieces/ttf")
        themes += ["ttf-" + splitext(d)[0].capitalize()
                   for d in listdir(ttf) if splitext(d)[1] == '.ttf']
        themes.sort()

        return themes

# Save initing


class SaveTab:
    """ :Description: Allows the user to configure the structure of saved
        game files name along with various game attributes such as elapse time
        between moves and analysis engin evalutations
    """
    def __init__(self, widgets):
        # Init 'auto save" checkbutton
        def checkCallBack(_):
            """ :Description: Sets the various option based on user interaction with the
                checkboxes in the gui
            """

            checkbox = widgets["autoSave"]
            widgets["autosave_grid"].set_property("sensitive", checkbox.get_active())

        conf.notify_add("autoSave", checkCallBack)
        uistuff.keep(widgets["autoSave"], "autoSave")
        checkCallBack(_)

        self.auto_save_path = conf.get("autoSavePath")
        conf.set("autoSavePath", self.auto_save_path)

        auto_save_chooser_dialog = Gtk.FileChooserDialog(
            _("Select auto save path"), mainwindow(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.OK))
        auto_save_chooser_button = Gtk.FileChooserButton.new_with_dialog(
            auto_save_chooser_dialog)
        auto_save_chooser_button.set_current_folder(self.auto_save_path)

        widgets["savePathChooserDock"].add(auto_save_chooser_button)
        auto_save_chooser_button.show()

        def selectAutoSave(_):
            """ :Description: Sets the auto save path for stored games if it
                has changed since last time

                :signal: Activated on receiving the 'current-folder-changed' signal
            """
            new_directory = auto_save_chooser_dialog.get_filename()
            if new_directory != self.auto_save_path:
                conf.set("autoSavePath", new_directory)

        auto_save_chooser_button.connect("current-folder-changed", selectAutoSave)

        conf.set("autoSaveFormat", conf.get("autoSaveFormat"))
        uistuff.keep(widgets["autoSaveFormat"], "autoSaveFormat")

        # uistuff.keep(widgets["saveEmt"], "saveEmt")
        # uistuff.keep(widgets["saveEval"], "saveEval")
        # uistuff.keep(widgets["saveRatingChange"], "saveRatingChange")
        # uistuff.keep(widgets["indentPgn"], "indentPgn")
        # uistuff.keep(widgets["saveOwnGames"], "saveOwnGames")
