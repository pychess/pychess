""" :Description: This module facilitates configurable object that the end user can
    customise such as which chess setor board colours to use or the ability to turn on/off
    various sidepanel facilities such as hints, comments engine analysis etc. It also allows
    the user to setup and use customised sounds or no sounds at all for a variety of in game
    events such as running out of time or piece movement events etc.
"""
from __future__ import print_function

import os
from os import listdir
from os.path import isdir, isfile, splitext

import sys
from xml.dom import minidom

from gi.repository import Gtk, GdkPixbuf, Gdk

from pychess.compat import pathname2url, url2pathname, unquote
from pychess.System.prefix import addDataPrefix, getDataPrefix
from pychess.System.idle_add import idle_add
from pychess.System import conf, gstreamer, uistuff
from pychess.Players.engineNest import discoverer
from pychess.Utils.const import HINT, SPY, SOUND_MUTE, SOUND_BEEP, SOUND_URI, SOUND_SELECT
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.gfx import Pieces
from pychess.widgets import Background
from pychess.widgets.Background import hexcol, newTheme

firstRun = True


def run(widgets):
    global firstRun
    if firstRun:
        initialize(widgets)
        firstRun = False
    widgets["preferences_dialog"].show()
    widgets["preferences_dialog"].present()


def initialize(widgets):
    """ :Description: Initialises the various tabs for each section of configurable artifacts
    """
    GeneralTab(widgets)
    HintTab(widgets)
    SoundTab(widgets)
    PanelTab(widgets)
    ThemeTab(widgets)
    SaveTab(widgets)

    uistuff.keepWindowSize("preferencesdialog", widgets["preferences_dialog"])

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

        conf.set("firstName", conf.get("firstName", conf.username))
        conf.set("secondName", conf.get("secondName", _("Guest")))

        # Give to uistuff.keeper

        for key in ("firstName", "secondName", "showEmt", "showEval",
                    "autoPromote", "hideTabs", "closeAll", "faceToFace",
                    "showCords", "showCaptured", "figuresInNotation",
                    "fullAnimation", "moveAnimation", "noAnimation",
                    "showFICSgameno"):
            uistuff.keep(widgets[key], key)

        # Options on by default
        for key in ("autoRotate", "fullAnimation", "showBlunder"):
            uistuff.keep(widgets[key], key, first_value=True)

# Hint initing


def anal_combo_get_value(combobox):
    engine = list(discoverer.getAnalyzers())[combobox.get_active()]
    return engine.get("md5")


def anal_combo_set_value(combobox, value, show_arrow_check, ana_check,
                         analyzer_type):
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

    from pychess.widgets.ionest import game_handler
    from pychess.widgets.gamewidget import widgets
    for gmwidg in game_handler.gamewidgets:
        spectators = gmwidg.gamemodel.spectators
        md5 = engine.get('md5')

        if analyzer_type in spectators and \
                spectators[analyzer_type].md5 != md5:
            gmwidg.gamemodel.remove_analyzer(analyzer_type)
            gmwidg.gamemodel.start_analyzer(analyzer_type)
            if not widgets[show_arrow_check].get_active():
                gmwidg.gamemodel.pause_analyzer(analyzer_type)


class HintTab:
    def __init__(self, widgets):
        self.widgets = widgets

        # Options on by default
        for key in ("opening_check", "endgame_check", "online_egtb_check",
                    "analyzer_check", "inv_analyzer_check"):
            uistuff.keep(widgets[key], key, first_value=True)

        # Opening book
        default_path = os.path.join(addDataPrefix("pychess_book.bin"))
        path = conf.get("opening_file_entry", default_path)
        conf.set("opening_file_entry", path)

        book_chooser_dialog = Gtk.FileChooserDialog(
            _("Select book file"), None, Gtk.FileChooserAction.OPEN,
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
            else:
                # restore the original
                book_chooser_dialog.set_filename(path)

        book_chooser_button.connect("file-set", select_new_book)

        def on_opening_check_toggled(check):
            self.widgets["opening_hbox"].set_sensitive(check.get_active())

        self.widgets["opening_check"].connect_after("toggled",
                                                    on_opening_check_toggled)

        # Endgame
        default_path = os.path.join(getDataPrefix())
        egtb_path = conf.get("egtb_path", default_path)
        conf.set("egtb_path", egtb_path)

        egtb_chooser_dialog = Gtk.FileChooserDialog(
            _("Select Gaviota TB path"), None,
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

        @idle_add
        def update_analyzers_store(discoverer):
            data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
            uistuff.updateCombo(widgets["ana_combobox"], data)
            uistuff.updateCombo(widgets["inv_ana_combobox"], data)

        discoverer.connect_after("all_engines_discovered",
                                 update_analyzers_store)
        update_analyzers_store(discoverer)

        # Save, load and make analyze combos active

        # Let Stockfish to be default analyzer in Windows installer
        default = discoverer.getEngineN(-1).get("md5")
        conf.set("ana_combobox", conf.get("ana_combobox", default))
        conf.set("inv_ana_combobox", conf.get("inv_ana_combobox", default))

        def on_analyzer_check_toggled(check):
            self.widgets["analyzers_vbox"].set_sensitive(check.get_active())
            from pychess.widgets.ionest import game_handler
            from pychess.widgets.gamewidget import widgets
            if len(game_handler.gamewidgets) != 0:
                if check.get_active():
                    for gmwidg in game_handler.gamewidgets:
                        gmwidg.gamemodel.restart_analyzer(HINT)
                        if not widgets["hint_mode"].get_active():
                            gmwidg.gamemodel.pause_analyzer(HINT)
                else:
                    for gmwidg in game_handler.gamewidgets:
                        gmwidg.gamemodel.remove_analyzer(HINT)

        self.widgets["analyzers_vbox"].set_sensitive(widgets[
            "analyzer_check"].get_active())
        self.widgets["analyzer_check"].connect_after("toggled",
                                                     on_analyzer_check_toggled)

        def on_invanalyzer_check_toggled(check):
            self.widgets["inv_analyzers_vbox"].set_sensitive(check.get_active())
            from pychess.widgets.ionest import game_handler
            if len(game_handler.gamewidgets) != 0:
                if check.get_active():
                    for gmwidg in game_handler.gamewidgets:
                        gmwidg.gamemodel.restart_analyzer(SPY)
                        if not widgets["spy_mode"].get_active():
                            gmwidg.gamemodel.pause_analyzer(SPY)
                else:
                    for gmwidg in game_handler.gamewidgets:
                        gmwidg.gamemodel.remove_analyzer(SPY)

        self.widgets["inv_analyzers_vbox"].set_sensitive(widgets[
            "inv_analyzer_check"].get_active())
        self.widgets["inv_analyzer_check"].connect_after(
            "toggled", on_invanalyzer_check_toggled)

        # Give widgets to keeper

        uistuff.keep(
            self.widgets["ana_combobox"], "ana_combobox", anal_combo_get_value,
            lambda combobox, value: anal_combo_set_value(combobox, value, "hint_mode", "analyzer_check", HINT))
        uistuff.keep(
            self.widgets["inv_ana_combobox"], "inv_ana_combobox",
            anal_combo_get_value,
            lambda combobox, value: anal_combo_set_value(combobox, value, "spy_mode", "inv_analyzer_check", SPY))

        uistuff.keep(self.widgets["max_analysis_spin"], "max_analysis_spin", first_value=3)

# Sound initing

# Setup default sounds
EXT = "wav" if sys.platform == "win32" else "ogg"

for i in range(11):
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


class SoundTab:

    SOUND_DIRS = (addDataPrefix("sounds"), "/usr/share/sounds",
                  "/usr/local/share/sounds", os.path.expanduser("~"))

    COUNT_OF_SOUNDS = 11

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
    }

    _player = None

    @classmethod
    def getPlayer(cls):
        if not cls._player:
            cls._player = gstreamer.sound_player
        return cls._player

    @classmethod
    def playAction(cls, action):
        if not conf.get("useSounds", True):
            return

        if isinstance(action, str):
            key_no = cls.actionToKeyNo[action]
        else:
            key_no = action
        typ = conf.get("soundcombo%d" % key_no, SOUND_MUTE)
        if typ == SOUND_BEEP:
            sys.stdout.write("\a")
            sys.stdout.flush()
        elif typ == SOUND_URI:
            uri = conf.get("sounduri%d" % key_no, "")
            if not os.path.isfile(url2pathname(uri[5:])):
                conf.set("soundcombo%d" % key_no, SOUND_MUTE)
                return
            cls.getPlayer().play(uri)

    def __init__(self, widgets):

        # Init open dialog

        opendialog = Gtk.FileChooserDialog(
            _("Open Sound File"), None, Gtk.FileChooserAction.OPEN,
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
                    label = unquote(os.path.split(uri)[1])
                    if len(model) == 3:
                        model.append([audioIco, label])
                    else:
                        model.set(model.get_iter((3, )), 1, label)
                    combobox.set_active(3)
                else:
                    combobox.set_active(conf.get("soundcombo%d" % index,
                                                 SOUND_MUTE))
                opendialog.hide()

        for i in range(self.COUNT_OF_SOUNDS):
            combo = widgets["sound%dcombo" % i]
            uistuff.createCombo(combo, items, name="soundcombo%d" % i)
            # combo.set_active(0)
            combo.connect("changed", callback, i)

            label = widgets["soundlabel%d" % i]
            label.props.mnemonic_widget = combo

            uri = conf.get("sounduri%d" % i, "")
            if os.path.isfile(url2pathname(uri[5:])):
                model = combo.get_model()
                model.append([audioIco, unquote(os.path.split(uri)[1])])
                # combo.set_active(3)

        for i in range(self.COUNT_OF_SOUNDS):
            if conf.get("soundcombo%d" % i, SOUND_MUTE) == SOUND_URI and \
                    not os.path.isfile(url2pathname(conf.get("sounduri%d" % i, "")[5:])):
                conf.set("soundcombo%d" % i, SOUND_MUTE)
            uistuff.keep(widgets["sound%dcombo" % i], "soundcombo%d" % i)

        # Init play button

        def playCallback(button, index):
            SoundTab.playAction(index)

        for i in range(self.COUNT_OF_SOUNDS):
            button = widgets["sound%dbutton" % i]
            button.connect("clicked", playCallback, i)

        # Init 'use sound" checkbutton

        def checkCallBack(*args):
            checkbox = widgets["useSounds"]
            widgets["sounds_frame"].set_property("sensitive", checkbox.get_active())

        conf.notify_add("useSounds", checkCallBack)
        widgets["useSounds"].set_active(True)
        uistuff.keep(widgets["useSounds"], "useSounds")
        checkCallBack()

        if not self.getPlayer().ready:
            widgets["useSounds"].set_sensitive(False)
            widgets["useSounds"].set_active(False)

        uistuff.keep(widgets["alarm_spin"], "alarm_spin", first_value=15)

# Panel initing


class PanelTab:
    def __init__(self, widgets):
        # Put panels in trees
        self.widgets = widgets

        from pychess.widgets.gamewidget import sidePanels, dockLocation

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

        d = Gtk.MessageDialog(type=Gtk.MessageType.INFO,
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

        from pychess.widgets.gamewidget import notebooks, docks
        from pychess.widgets.pydock import EAST

        if active:
            leaf = notebooks["board"].get_parent().get_parent()
            leaf.dock(docks[name][1], EAST, docks[name][0], name)
        else:
            try:
                notebooks[name].get_parent().get_parent().undock(notebooks[
                    name])
            except AttributeError:
                # A new panel appeared in the panels directory
                leaf = notebooks["board"].get_parent().get_parent()
                leaf.dock(docks[name][1], EAST, docks[name][0], name)

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


class ThemeTab:
    """ :Description: Allows the setting of various user specific chess
        sets and board colours
    """
    def __init__(self, widgets):
        self.widgets = widgets

        # Background image
        path = conf.get("welcome_image", addDataPrefix("glade/clear.png"))
        conf.set("welcome_image", path)

        image_chooser_dialog = Gtk.FileChooserDialog(
            _("Select background image file"), None, Gtk.FileChooserAction.OPEN,
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

        # Board Colours

        style_ctxt = widgets["window1"].get_style_context()
        LIGHT = hexcol(style_ctxt.lookup_color("p_light_color")[1])
        DARK = hexcol(style_ctxt.lookup_color("p_dark_color")[1])

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
            conf.set("lightcolour", LIGHT)
            conf.set("darkcolour", DARK)

        widgets["reset_btn"].connect("clicked", onResetColourClicked)

        # Get the current board colours if set, if not set, set them to default
        conf.set("lightcolour", conf.get("lightcolour", LIGHT))
        conf.set("darkcolour", conf.get("darkcolour", DARK))

        # Next 2 lines take a #hex str converts them to a color then to a RGBA representation
        self.lightcolour = Gdk.RGBA()
        self.lightcolour.parse(conf.get("lightcolour", LIGHT))
        self.darkcolour = Gdk.RGBA()
        self.darkcolour.parse(conf.get("darkcolour", DARK))

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
                return conf.get("pieceTheme", "Chessicons")

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

        uistuff.keep(widgets["pieceTheme"], "pieceTheme", _getActive,
                     _setActive, "Chessicons")

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
            widgets["autosave_grid"].set_property("sensitive",
                                                  checkbox.get_active())

        conf.notify_add("autoSave", checkCallBack)
        widgets["autoSave"].set_active(False)
        uistuff.keep(widgets["autoSave"], "autoSave")
        checkCallBack(_)

        default_path = os.path.expanduser("~")
        self.auto_save_path = conf.get("autoSavePath", default_path)
        conf.set("autoSavePath", self.auto_save_path)

        auto_save_chooser_dialog = Gtk.FileChooserDialog(
            _("Select auto save path"), None,
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

        conf.set("autoSaveFormat", conf.get("autoSaveFormat", "pychess"))
        uistuff.keep(widgets["autoSaveFormat"], "autoSaveFormat")

        uistuff.keep(widgets["saveEmt"], "saveEmt")
        uistuff.keep(widgets["saveEval"], "saveEval")
        uistuff.keep(widgets["saveOwnGames"], "saveOwnGames")
