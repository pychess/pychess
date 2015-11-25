from __future__ import print_function

import os
import sys
import struct
from os import listdir
from os.path import isdir, isfile, splitext
from xml.dom import minidom

from gi.repository import Gtk, GdkPixbuf
from gi.repository import Gdk

from pychess.compat import pathname2url, url2pathname, unquote
from pychess.System.prefix import addDataPrefix, getDataPrefix
from pychess.System.idle_add import idle_add
from pychess.System import conf, gstreamer, uistuff
from pychess.Players.engineNest import discoverer
from pychess.Utils.const import *
from pychess.Utils.IconLoader import load_icon, get_pixbuf
from pychess.gfx import Pieces
from pychess.System.Log import log


firstRun = True
def run(widgets):
    global firstRun
    if firstRun:
        initialize(widgets)
        firstRun = False
    widgets["preferences"].show()
    widgets["preferences"].present()

def initialize(widgets):
    GeneralTab(widgets)
    HintTab(widgets)
    SoundTab(widgets)
    PanelTab(widgets)
    ThemeTab(widgets)
    SaveTab(widgets)


    uistuff.keepWindowSize("preferencesdialog", widgets["preferences"])

    def delete_event (widget, *args):
        widgets["preferences"].hide()
        return True
    widgets["preferences"].connect("delete-event", delete_event)
    widgets["preferences"].connect("key-press-event",
        lambda w,e: w.event(Gdk.Event(Gdk.EventType.DELETE))
        if e.keyval == Gdk.KEY_Escape else None)

################################################################################
# General initing                                                              #
################################################################################

class GeneralTab:

    def __init__ (self, widgets):

        conf.set("firstName", conf.get("firstName", conf.username))
        conf.set("secondName", conf.get("secondName", _("Guest")))

        # Give to uistuff.keeper

        for key in ("firstName", "secondName", "showEmt", "showEval",
                    "hideTabs", "closeAll", "faceToFace", "showCords", "showCaptured",
                    "figuresInNotation", "fullAnimation", "moveAnimation", "noAnimation"):
            uistuff.keep(widgets[key], key)

        # Options on by default
        for key in ("autoRotate", "fullAnimation", "showBlunder"):
            uistuff.keep(widgets[key], key, first_value=True)

################################################################################
# Hint initing                                                               #
################################################################################

def anal_combo_get_value (combobox):
    engine = list(discoverer.getAnalyzers())[combobox.get_active()]
    return engine.get("md5")

def anal_combo_set_value (combobox, value, show_arrow_check, ana_check, analyzer_type):
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

    from pychess.Main import gameDic
    from pychess.widgets.gamewidget import widgets
    for gmwidg in gameDic.keys():
        spectators = gmwidg.gamemodel.spectators
        md5 = engine.get('md5')

        if analyzer_type in spectators and \
                spectators[analyzer_type].md5 != md5:
            gmwidg.gamemodel.remove_analyzer(analyzer_type)
            gmwidg.gamemodel.start_analyzer(analyzer_type)
            if not widgets[show_arrow_check].get_active():
                gmwidg.gamemodel.pause_analyzer(analyzer_type)

class HintTab:
    def __init__ (self, widgets):
        self.widgets = widgets

        # Options on by default
        for key in ("opening_check", "endgame_check", "online_egtb_check",
                    "analyzer_check", "inv_analyzer_check"):
            uistuff.keep(widgets[key], key, first_value=True)

        # Opening book
        default_path = os.path.join(addDataPrefix("pychess_book.bin"))
        path = conf.get("opening_file_entry", default_path)
        conf.set("opening_file_entry", path)

        book_chooser_dialog = Gtk.FileChooserDialog(_("Select book file"), None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        book_chooser_button = Gtk.FileChooserButton.new_with_dialog(book_chooser_dialog)

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

        def on_opening_check_toggled (check):
            widgets["opening_hbox"].set_sensitive(check.get_active())
        widgets["opening_check"].connect_after("toggled",
                                                on_opening_check_toggled)

        # Endgame
        default_path = os.path.join(getDataPrefix())
        egtb_path = conf.get("egtb_path", default_path)
        conf.set("egtb_path", egtb_path)

        egtb_chooser_dialog = Gtk.FileChooserDialog(_("Select Gaviota TB path"), None, Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        egtb_chooser_button = Gtk.FileChooserButton.new_with_dialog(egtb_chooser_dialog)
        egtb_chooser_button.set_current_folder(egtb_path)

        self.widgets["egtbChooserDock"].add(egtb_chooser_button)
        egtb_chooser_button.show()

        def select_egtb(button):
            new_directory = egtb_chooser_dialog.get_filename()
            if new_directory != egtb_path:
                conf.set("egtb_path", new_directory)

        egtb_chooser_button.connect("current-folder-changed", select_egtb)

        def on_endgame_check_toggled (check):
            widgets["endgame_hbox"].set_sensitive(check.get_active())

        widgets["endgame_check"].connect_after("toggled",
                                                on_endgame_check_toggled)

        # Analyzing engines
        from pychess.widgets import newGameDialog
        data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
        uistuff.createCombo(widgets["ana_combobox"], data)
        uistuff.createCombo(widgets["inv_ana_combobox"], data)

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

        def on_analyzer_check_toggled (check):
            widgets["analyzers_vbox"].set_sensitive(check.get_active())
            from pychess.Main import gameDic
            if gameDic:
                if check.get_active():
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.restart_analyzer(HINT)
                        if not widgets["hint_mode"].get_active():
                            gmwidg.gamemodel.pause_analyzer(HINT)
                else:
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.remove_analyzer(HINT)

        widgets["analyzers_vbox"].set_sensitive(
            widgets["analyzer_check"].get_active())
        widgets["analyzer_check"].connect_after("toggled",
                                                on_analyzer_check_toggled)

        def on_invanalyzer_check_toggled (check):
            widgets["inv_analyzers_vbox"].set_sensitive(check.get_active())
            from pychess.Main import gameDic
            if gameDic:
                if check.get_active():
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.restart_analyzer(SPY)
                        if not widgets["spy_mode"].get_active():
                            gmwidg.gamemodel.pause_analyzer(SPY)
                else:
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.remove_analyzer(SPY)

        widgets["inv_analyzers_vbox"].set_sensitive(
            widgets["inv_analyzer_check"].get_active())
        widgets["inv_analyzer_check"].connect_after("toggled",
                                              on_invanalyzer_check_toggled)

        # Give widgets to keeper

        uistuff.keep(widgets["ana_combobox"], "ana_combobox", anal_combo_get_value,
            lambda combobox, value: anal_combo_set_value(combobox, value, "hint_mode",
                                              "analyzer_check", HINT))
        uistuff.keep(widgets["inv_ana_combobox"], "inv_ana_combobox", anal_combo_get_value,
            lambda combobox, value: anal_combo_set_value(combobox, value, "spy_mode",
                                              "inv_analyzer_check", SPY))

        uistuff.keep(widgets["max_analysis_spin"], "max_analysis_spin", first_value=3)

################################################################################
# Sound initing                                                                #
################################################################################

# Setup default sounds
EXT = "wav" if sys.platform == "win32" else "ogg"

for i in range(11):
    if not conf.hasKey("soundcombo%d" % i):
        conf.set("soundcombo%d" % i, SOUND_URI)
if not conf.hasKey("sounduri0"):
    conf.set("sounduri0", "file:"+pathname2url(addDataPrefix("sounds/move1.%s" % EXT)))
if not conf.hasKey("sounduri1"):
    conf.set("sounduri1", "file:"+pathname2url(addDataPrefix("sounds/check1.%s" % EXT)))
if not conf.hasKey("sounduri2"):
    conf.set("sounduri2", "file:"+pathname2url(addDataPrefix("sounds/capture1.%s" % EXT)))
if not conf.hasKey("sounduri3"):
    conf.set("sounduri3", "file:"+pathname2url(addDataPrefix("sounds/start1.%s" % EXT)))
if not conf.hasKey("sounduri4"):
    conf.set("sounduri4", "file:"+pathname2url(addDataPrefix("sounds/win1.%s" % EXT)))
if not conf.hasKey("sounduri5"):
    conf.set("sounduri5", "file:"+pathname2url(addDataPrefix("sounds/lose1.%s" % EXT)))
if not conf.hasKey("sounduri6"):
    conf.set("sounduri6", "file:"+pathname2url(addDataPrefix("sounds/draw1.%s" % EXT)))
if not conf.hasKey("sounduri7"):
    conf.set("sounduri7", "file:"+pathname2url(addDataPrefix("sounds/obs_mov.%s" % EXT)))
if not conf.hasKey("sounduri8"):
    conf.set("sounduri8", "file:"+pathname2url(addDataPrefix("sounds/obs_end.%s" % EXT)))
if not conf.hasKey("sounduri9"):
    conf.set("sounduri9", "file:"+pathname2url(addDataPrefix("sounds/alarm.%s" % EXT)))
if not conf.hasKey("sounduri10"):
    conf.set("sounduri10", "file:"+pathname2url(addDataPrefix("sounds/invalid.%s" % EXT)))

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
    def getPlayer (cls):
        if not cls._player:
            cls._player = gstreamer.sound_player
        return cls._player

    @classmethod
    def playAction (cls, action):
        if not conf.get("useSounds", True):
            return

        if isinstance(action, str):
            no = cls.actionToKeyNo[action]
        else: no = action
        typ = conf.get("soundcombo%d" % no, SOUND_MUTE)
        if typ == SOUND_BEEP:
            sys.stdout.write("\a")
            sys.stdout.flush()
        elif typ == SOUND_URI:
            uri = conf.get("sounduri%d" % no, "")
            if not os.path.isfile(url2pathname(uri[5:])):
                conf.set("soundcombo%d" % no, SOUND_MUTE)
                return
            cls.getPlayer().play(uri)

    def __init__ (self, widgets):

        # Init open dialog

        opendialog = Gtk.FileChooserDialog (
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

        def callback (combobox, index):
            if combobox.get_active() == SOUND_SELECT:
                if opendialog.run() == Gtk.ResponseType.ACCEPT:
                    uri = opendialog.get_uri()
                    model = combobox.get_model()
                    conf.set("sounduri%d"%index, uri)
                    label = unquote(os.path.split(uri)[1])
                    if len(model) == 3:
                        model.append([audioIco, label])
                    else:
                        model.set(model.get_iter((3,)), 1, label)
                    combobox.set_active(3)
                else:
                    combobox.set_active(conf.get("soundcombo%d"%index,SOUND_MUTE))
                opendialog.hide()

        for i in range(self.COUNT_OF_SOUNDS):
            combo = widgets["soundcombo%d"%i]
            uistuff.createCombo (combo, items)
            combo.set_active(0)
            combo.connect("changed", callback, i)

            label = widgets["soundlabel%d"%i]
            label.props.mnemonic_widget = combo

            uri = conf.get("sounduri%d"%i,"")
            if os.path.isfile(url2pathname(uri[5:])):
                model = combo.get_model()
                model.append([audioIco, unquote(os.path.split(uri)[1])])
                combo.set_active(3)

        for i in range(self.COUNT_OF_SOUNDS):
            if conf.get("soundcombo%d"%i, SOUND_MUTE) == SOUND_URI and \
                    not os.path.isfile(url2pathname(conf.get("sounduri%d"%i,"")[5:])):
                conf.set("soundcombo%d"%i, SOUND_MUTE)
            uistuff.keep(widgets["soundcombo%d"%i], "soundcombo%d"%i)

        # Init play button

        def playCallback (button, index):
            SoundTab.playAction(index)

        for i in range (self.COUNT_OF_SOUNDS):
            button = widgets["soundbutton%d"%i]
            button.connect("clicked", playCallback, i)

        # Init 'use sound" checkbutton

        def checkCallBack (*args):
            checkbox = widgets["useSounds"]
            widgets["frame23"].set_property("sensitive", checkbox.get_active())
        conf.notify_add("useSounds", checkCallBack)
        widgets["useSounds"].set_active(True)
        uistuff.keep(widgets["useSounds"], "useSounds")
        checkCallBack()

        if not self.getPlayer().ready:
            widgets["useSounds"].set_sensitive(False)
            widgets["useSounds"].set_active(False)

        uistuff.keep(widgets["alarm_spin"], "alarm_spin", first_value=15)

################################################################################
# Panel initing                                                               #
################################################################################

class PanelTab:

    def __init__ (self, widgets):
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

        self.tv = widgets["treeview1"]
        self.tv.set_model(store)

        self.widgets['panel_about_button'].connect('clicked', self.panel_about)
        self.widgets['panel_enable_button'].connect('toggled', self.panel_toggled)
        self.tv.get_selection().connect('changed', self.selection_changed)

        pixbuf = Gtk.CellRendererPixbuf()
        pixbuf.props.yalign = 0
        pixbuf.props.ypad = 3
        pixbuf.props.xpad = 3
        self.tv.append_column(Gtk.TreeViewColumn("Icon", pixbuf, pixbuf=1, sensitive=0))

        uistuff.appendAutowrapColumn(self.tv, "Name", markup=2, sensitive=0)

        widgets['notebook1'].connect("switch-page", self.__on_switch_page)
        widgets["preferences"].connect("show", self.__on_show_window)
        widgets["preferences"].connect("hide", self.__on_hide_window)

    def selection_changed(self, treeselection):
        store, iter = self.tv.get_selection().get_selected()
        self.widgets['panel_enable_button'].set_sensitive(bool(iter))
        self.widgets['panel_about_button'].set_sensitive(bool(iter))

        if iter:
            active = self.tv.get_model().get(iter, 0)[0]
            self.widgets['panel_enable_button'].set_active(active)

    def panel_about(self, button):
        store, iter = self.tv.get_selection().get_selected()
        assert iter # The button should only be clickable when we have a selection
        path = store.get_path(iter)
        panel = store[path][3]

        d = Gtk.MessageDialog (type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.CLOSE)
        d.set_markup ("<big><b>%s</b></big>" % panel.__title__)
        text = panel.__about__ if hasattr(panel, '__about__') else _('Undescribed panel')
        d.format_secondary_text (text)
        d.run()
        d.hide()

    def panel_toggled(self, button):
        store, iter = self.tv.get_selection().get_selected()
        assert iter # The button should only be clickable when we have a selection
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
                notebooks[name].get_parent().get_parent().undock(notebooks[name])
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
        else: self.hideit()

    def __on_show_window(self, widget):
        notebook = self.widgets['notebook1']
        page_num = notebook.get_current_page()
        if notebook.get_nth_page(page_num) == self.widgets['sidepanels']:
            self.showit()

    def __on_hide_window(self, widget):
        self.hideit()



#############################################################################
# Theme initing                                                             #
#############################################################################


class ThemeTab:

    def __init__ (self, widgets):

        #################
        # Board Colours
        #################

        # This should probably be in Utils module
        def hex12_to_rgb(hstr):
            hexstr = hstr[1:3] + hstr[5:7] + hstr[10:12]
#            log.debug("Cajone HexStr :  %s , %s " % (hexstr, struct.unpack('BBB',bytes.fromhex(hexstr))))
            return struct.unpack('BBB',bytes.fromhex(hexstr))

        def on_color_set_light(color):
            conf.set('lightcolour',widgets['light_cbtn'].get_color().to_string())
#            log.debug("Cajone Light Colors %s :  " % (widgets['light_cbtn'].get_color().to_string()))

        widgets["light_cbtn"].connect_after("color-set",
                                                on_color_set_light)

        def on_color_set_dark(color):
            conf.set('darkcolour',widgets['dark_cbtn'].get_color().to_string())
#            log.debug("Cajone Dark Color %s :  " % (widgets['dark_cbtn'].get_color().to_string()))

        widgets["dark_cbtn"].connect_after("color-set",
                                                on_color_set_dark)


        # Get the current board colours if set, if not set, set them to default

        conf.set("lightcolour", conf.get("lightcolour", "#ffffffffffff"))
        conf.set("darkcolour", conf.get("darkcolour", "#000000000000"))

        lightcolour =  Gdk.Color(*list(hex12_to_rgb(conf.get("lightcolour", "#ffffffffffff"))))
        darkcolour =  Gdk.Color(*list(hex12_to_rgb(conf.get("darkcolour", "#000000000000"))))

        # Set the color swatches in preference to stored values
        widgets['light_cbtn'].set_color(lightcolour)
        widgets['dark_cbtn'].set_color(darkcolour)




        #############
        # Chess Sets
        #############
        self.themes = self.discover_themes()
        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

        for theme in self.themes:
            pngfile = "%s/%s.png" % (addDataPrefix("pieces"), theme)

            if isfile(pngfile):
                pixbuf = get_pixbuf(pngfile)
                store.append((pixbuf, theme))
            else:
                print("WARNING: No piece theme preview icons found. Please run create_theme_preview.sh !")
                break

        iconView = widgets["pieceTheme"]
        iconView.set_model(store)
        iconView.set_pixbuf_column(0)
        iconView.set_text_column(1)

        #############################################
        # Hack to fix spacing problem in iconview
        # http://stackoverflow.com/questions/14090094/what-causes-the-different-display-behaviour-for-a-gtkiconview-between-different
        def keep_size(crt, *args):
            crt.handler_block(crt_notify)
            crt.set_property('width', 40)
            crt.handler_unblock(crt_notify)

        crt, crp = iconView.get_cells()
        crt_notify = crt.connect('notify', keep_size)
        #############################################

        def _get_active(iconview):
            model = iconview.get_model()
            selected = iconview.get_selected_items()

            if len(selected) == 0:
                return conf.get("pieceTheme", "Chessicons")

            indices = selected[0].get_indices()
            if indices:
                i = indices[0]
                theme = model[i][1]
                Pieces.set_piece_theme(theme)
                return theme

        def _set_active(iconview, value):
            try:
                index = self.themes.index(value)
            except ValueError:
                index = 0
            iconview.select_path(Gtk.TreePath(index,))

        uistuff.keep(widgets["pieceTheme"], "pieceTheme", _get_active,
                     _set_active, "Chessicons")

    def discover_themes(self):
        themes = ['Pychess']

        pieces = addDataPrefix("pieces")
        themes += [d.capitalize() for d in listdir(pieces) if isdir(os.path.join(pieces,d)) and d != 'ttf']

        ttf = addDataPrefix("pieces/ttf")
        themes += ["ttf-" + splitext(d)[0].capitalize() for d in listdir(ttf) if splitext(d)[1] == '.ttf']
        themes.sort()

        return themes

#############################################################################
# Save initing                                                              #
#############################################################################

class SaveTab:

    def __init__ (self, widgets):
        # Init 'auto save" checkbutton
        def checkCallBack (*args):
            checkbox = widgets["autoSave"]
            widgets["autosave_grid"].set_property("sensitive", checkbox.get_active())
        conf.notify_add("autoSave", checkCallBack)
        widgets["autoSave"].set_active(False)
        uistuff.keep(widgets["autoSave"], "autoSave")
        checkCallBack()

        default_path = os.path.expanduser("~")
        autoSavePath = conf.get("autoSavePath", default_path)
        conf.set("autoSavePath", autoSavePath)

        auto_save_chooser_dialog = Gtk.FileChooserDialog(_("Select auto save path"), None, Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        auto_save_chooser_button = Gtk.FileChooserButton.new_with_dialog(auto_save_chooser_dialog)
        auto_save_chooser_button.set_current_folder(autoSavePath)

        widgets["savePathChooserDock"].add(auto_save_chooser_button)
        auto_save_chooser_button.show()

        def select_auto_save(button):
            new_directory = auto_save_chooser_dialog.get_filename()
            if new_directory != autoSavePath:
                conf.set("autoSavePath", new_directory)

        auto_save_chooser_button.connect("current-folder-changed", select_auto_save)

        conf.set("autoSaveFormat", conf.get("autoSaveFormat", "pychess"))
        uistuff.keep(widgets["autoSaveFormat"], "autoSaveFormat")

        uistuff.keep(widgets["saveEmt"], "saveEmt")
        uistuff.keep(widgets["saveEval"], "saveEval")
        uistuff.keep(widgets["saveOwnGames"], "saveOwnGames")
