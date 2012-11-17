import sys, os
from os import listdir
from os.path import isdir, isfile, splitext
from xml.dom import minidom

import gtk

from pychess.System.prefix import addDataPrefix, getUserDataPrefix
from pychess.System.glock import glock_connect_after
from pychess.System import conf, gstreamer, uistuff
from pychess.Players.engineNest import discoverer
from pychess.Utils.const import *
from pychess.Utils.IconLoader import load_icon
from pychess.gfx import Pieces

firstRun = True
def run(widgets):
    global firstRun
    if firstRun:
        initialize(widgets)
        firstRun = False
    widgets["preferences"].show()

def initialize(widgets):
    GeneralTab(widgets)
    EngineTab(widgets)
    SoundTab(widgets)
    PanelTab(widgets)
    ThemeTab(widgets)
    
    def delete_event (widget, *args):
        widgets["preferences"].hide()
        return True
    widgets["preferences"].connect("delete-event", delete_event)
    widgets["preferences_close_button"].connect("clicked", delete_event)
    
    widgets["preferences"].connect("key-press-event",
        lambda w,e: delete_event(w) if e.keyval == gtk.keysyms.Escape else None)

################################################################################
# General initing                                                              #
################################################################################

class GeneralTab:
    
    def __init__ (self, widgets):

        conf.set("firstName", conf.get("firstName", conf.username))
        conf.set("secondName", conf.get("secondName", _("Guest")))
        
        # Give to uistuff.keeper
        
        for key in ("firstName", "secondName",
                    "hideTabs", "autoRotate", "faceToFace", "showCords", "figuresInNotation", "autoCallFlag",
                    "fullAnimation", "moveAnimation", "noAnimation"):
            uistuff.keep(widgets[key], key)

        def get_active(widget):
            active = widget.get_active()
            Pieces.transparent_pieces = active
            return active

        uistuff.keep (widgets["transparentPieces"], "transparentPieces", get_value_=get_active)

################################################################################
# Engine initing                                                               #
################################################################################

class EngineTab:
    def __init__ (self, widgets):
        self.widgets = widgets
        # Put engines in trees and combos
        
        allstore = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        
        self.tv = widgets["engines_treeview"]
        self.tv.set_model(allstore)
        self.tv.append_column(gtk.TreeViewColumn(
                _("Flag"), gtk.CellRendererPixbuf(), pixbuf=0))
        self.tv.append_column(gtk.TreeViewColumn(
                _("Name"), gtk.CellRendererText(), text=1))

        from pychess.widgets import newGameDialog
        def update_store(discoverer, store):
            store.clear()
            # don't add the very first (Human) player to engine store
            for item in newGameDialog.playerItems[0][1:]:
                store.append(item)
        glock_connect_after(discoverer, "all_engines_discovered",
                            update_store, allstore)
        update_store(discoverer, allstore)

        uistuff.createCombo(widgets["ana_combobox"])
        uistuff.createCombo(widgets["inv_ana_combobox"])

        def update_analyzers_store(discoverer):
            data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
            uistuff.updateCombo(widgets["ana_combobox"], data)
            uistuff.updateCombo(widgets["inv_ana_combobox"], data)
        glock_connect_after(discoverer, "all_engines_discovered",
                            update_analyzers_store)
        update_analyzers_store(discoverer)

        # Save, load and make analyze combos active
        
        conf.set("ana_combobox", conf.get("ana_combobox", 0))
        conf.set("inv_ana_combobox", conf.get("inv_ana_combobox", 0))
        
        def on_analyzer_check_toggled (check):
            widgets["analyzers_vbox"].set_sensitive(check.get_active())
            from pychess.Main import gameDic
            if gameDic:
                if check.get_active():
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.restart_analyzer(HINT)
                else:
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.remove_analyzer(HINT)
        
        widgets["analyzer_check"].connect_after("toggled",
                                                on_analyzer_check_toggled)
        uistuff.keep(widgets["analyzer_check"], "analyzer_check")
        
        def on_invanalyzer_check_toggled (check):
            widgets["inv_analyzers_vbox"].set_sensitive(check.get_active())
            from pychess.Main import gameDic
            if gameDic:
                if check.get_active():
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.restart_analyzer(SPY)
                else:
                    for gmwidg in gameDic.keys():
                        gmwidg.gamemodel.remove_analyzer(SPY)

        widgets["inv_analyzer_check"].connect_after("toggled",
                                              on_invanalyzer_check_toggled)
        uistuff.keep(widgets["inv_analyzer_check"], "inv_analyzer_check")
        
        # Put options in trees in add/edit dialog
        
        #=======================================================================
        # tv = widgets["optionview"]
        # self.tv.append_column(gtk.TreeViewColumn(
        #    "Option", gtk.CellRendererText(), text=0))
        # self.tv.append_column(gtk.TreeViewColumn(
        #    "Value", gtk.CellRendererText(), text=1))
        # 
        # def edit (button):
        #    
        #    iter = widgets["engines_treeview"].get_selection().get_selected()[1]
        #    if iter: row = allstore.get_path(iter)[0]
        #    else: return
        #    
        #    engine = discoverer.getEngineN(row)
        #    optionstags = engine.getElementsByTagName("options")
        #    if not optionstags:
        #        widgets["engine_options_expander"].hide()
        #    else:
        #        widgets["engine_options_expander"].show()
        #        widgets["engine_options_expander"].set_expanded(False)
        #        
        #        optionsstore = gtk.ListStore(str, str)
        #        tv = widgets["optionview"]
        #        self.tv.set_model(optionsstore)
        #        
        #        for option in optionstags[0].childNodes:
        #            if option.nodeType != option.ELEMENT_NODE: continue
        #            optionsstore.append( [option.getAttribute("name"),
        #                                  option.getAttribute("default")] )
        #        
        #    widgets["engine_path_chooser"].set_title(_("Locate Engine"))
        #    widgets["engine_path_chooser"].set_uri("file:///usr/bin/gnuchess")
        #    
        #    dialog = widgets["addconfig_engine"]
        #    answer = dialog.run()
        #    dialog.hide()
        # widgets["edit_engine_button"].connect("clicked", edit)
        #=======================================================================

        self.tv.get_selection().connect('changed', self.selection_changed)

        def remove(button):
            store, iter = self.tv.get_selection().get_selected()
            if iter:
                row = allstore.get_path(iter)[0]
                binname = allstore[row][2]
                discoverer.removeEngine(binname)
                discoverer.start()
        widgets["remove_engine_button"].connect("clicked", remove)

        def add(button):
            dialog = gtk.FileChooserDialog(_("Select engine"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
            response = dialog.run()
            if response == gtk.RESPONSE_OK:
                new_engine = dialog.get_filename()
                if os.access(new_engine, os.R_OK|os.X_OK):
                    discoverer.addEngine(new_engine)
                    discoverer.start()
                else:
                    print "%s is not an executable" % new_engine
            dialog.destroy()
        widgets["add_engine_button"].connect("clicked", add)
        
        # Give widgets to keeper
        
        def get_value (combobox):
            engine = list(discoverer.getAnalyzers())[combobox.get_active()]
            if engine.find('md5') != None:
                return engine.find('md5').text.strip()
        
        def set_value (combobox, value, show_arrow_check, ana_check, analyzer_type):
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
            
            replace_analyzers = False
            if widgets[show_arrow_check].get_active() is True and \
                    widgets[ana_check].get_active() is True:
                replace_analyzers = True
            
            from pychess.Main import gameDic
            for gmwidg in gameDic.keys():
                spectators = gmwidg.gamemodel.spectators
                md5 = engine.find('md5').text.strip()
                
                if analyzer_type in spectators and \
                        spectators[analyzer_type].md5 != md5:
                    gmwidg.gamemodel.remove_analyzer(analyzer_type)
                    if replace_analyzers:
                        gmwidg.gamemodel.start_analyzer(analyzer_type)
        
        uistuff.keep(widgets["ana_combobox"], "ana_combobox", get_value,
            lambda combobox, value: set_value(combobox, value, "hint_mode",
                                              "analyzer_check", HINT))
        uistuff.keep(widgets["inv_ana_combobox"], "inv_ana_combobox", get_value,
            lambda combobox, value: set_value(combobox, value, "spy_mode",
                                              "inv_analyzer_check", SPY))

    def selection_changed(self, treeselection):
        self.widgets['remove_engine_button'].set_sensitive(True)
        
################################################################################
# Sound initing                                                                #
################################################################################

# Setup default sounds

for i in xrange(9):
    if not conf.hasKey("soundcombo%d" % i):
        conf.set("soundcombo%d" % i, SOUND_URI)
if not conf.hasKey("sounduri0"):
    conf.set("sounduri0", "file://"+addDataPrefix("sounds/move1.ogg"))
if not conf.hasKey("sounduri1"):
    conf.set("sounduri1", "file://"+addDataPrefix("sounds/check1.ogg"))
if not conf.hasKey("sounduri2"):
    conf.set("sounduri2", "file://"+addDataPrefix("sounds/capture1.ogg"))
if not conf.hasKey("sounduri3"):
    conf.set("sounduri3", "file://"+addDataPrefix("sounds/start1.ogg"))
if not conf.hasKey("sounduri4"):
    conf.set("sounduri4", "file://"+addDataPrefix("sounds/win1.ogg"))
if not conf.hasKey("sounduri5"):
    conf.set("sounduri5", "file://"+addDataPrefix("sounds/lose1.ogg"))
if not conf.hasKey("sounduri6"):
    conf.set("sounduri6", "file://"+addDataPrefix("sounds/draw1.ogg"))
if not conf.hasKey("sounduri7"):
    conf.set("sounduri7", "file://"+addDataPrefix("sounds/obs_mov.ogg"))
if not conf.hasKey("sounduri8"):
    conf.set("sounduri8", "file://"+addDataPrefix("sounds/obs_end.ogg"))

class SoundTab:
    
    SOUND_DIRS = (addDataPrefix("sounds"), "/usr/share/sounds",
                  "/usr/local/share/sounds", os.environ["HOME"])
    
    COUNT_OF_SOUNDS = 9
    
    actionToKeyNo = {
        "aPlayerMoves": 0,
        "aPlayerChecks": 1,
        "aPlayerCaptures": 2,
        "gameIsSetup": 3,
        "gameIsWon": 4,
        "gameIsLost": 5,
        "gameIsDrawn": 6,
        "observedMoves": 7,
        "oberservedEnds": 8
    }
    
    _player = None
    @classmethod
    def getPlayer (cls):
        if not cls._player:
            cls._player = gstreamer.Player()
        return cls._player
    
    @classmethod
    def playAction (cls, action):
        if not conf.get("useSounds", True):
            return
        
        if type(action) == str:
            no = cls.actionToKeyNo[action]
        else: no = action
        typ = conf.get("soundcombo%d" % no, SOUND_MUTE)
        if typ == SOUND_BEEP:
            sys.stdout.write("\a")
            sys.stdout.flush()
        elif typ == SOUND_URI:
            uri = conf.get("sounduri%d" % no, "")
            if not os.path.isfile(uri[7:]):
                conf.set("soundcombo%d" % no, SOUND_MUTE)
                return
            cls.getPlayer().play(uri)
    
    def __init__ (self, widgets):
        
        # Init open dialog
        
        opendialog = gtk.FileChooserDialog (
                _("Open Sound File"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
                 (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN,
                  gtk.RESPONSE_ACCEPT))
        
        for dir in self.SOUND_DIRS:
            if os.path.isdir(dir):
                opendialog.set_current_folder(dir)
                break
        
        soundfilter = gtk.FileFilter()
        soundfilter.add_custom(soundfilter.get_needed(),
                               lambda data: data[3] and data[3].startswith("audio/"))
        opendialog.add_filter(soundfilter)
        opendialog.set_filter(soundfilter)
        
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
                if opendialog.run() == gtk.RESPONSE_ACCEPT:
                    uri = opendialog.get_uri()
                    model = combobox.get_model()
                    conf.set("sounduri%d"%index, uri)
                    label = os.path.split(uri)[1]
                    if len(model) == 3:
                        model.append([audioIco, label])
                    else:
                        model.set(model.get_iter((3,)), 1, label)
                    combobox.set_active(3)
                else:
                    combobox.set_active(conf.get("soundcombo%d"%index,SOUND_MUTE))
                opendialog.hide()
        
        for i in xrange(self.COUNT_OF_SOUNDS):
            combo = widgets["soundcombo%d"%i]
            uistuff.createCombo (combo, items)
            combo.set_active(0)
            combo.connect("changed", callback, i)
            
            label = widgets["soundlabel%d"%i]
            label.props.mnemonic_widget = combo
            
            uri = conf.get("sounduri%d"%i,"")
            if os.path.isfile(uri[7:]):
                model = combo.get_model()
                model.append([audioIco, os.path.split(uri)[1]])
                combo.set_active(3)
        
        for i in xrange(self.COUNT_OF_SOUNDS):
            if conf.get("soundcombo%d"%i, SOUND_MUTE) == SOUND_URI and \
                    not os.path.isfile(conf.get("sounduri%d"%i,"")[7:]):
                conf.set("soundcombo%d"%i, SOUND_MUTE)
            uistuff.keep(widgets["soundcombo%d"%i], "soundcombo%d"%i)
            #widgets["soundcombo%d"%i].set_active(conf.get("soundcombo%d"%i, SOUND_MUTE))
        
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
        
        def soundError (player, gstmessage):
            widgets["useSounds"].set_sensitive(False)
            widgets["useSounds"].set_active(False)
        self.getPlayer().connect("error", soundError)

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
        
        store = gtk.ListStore(bool, gtk.gdk.Pixbuf, str, object)
        for panel in sidePanels:
            checked = True if not xmlOK else panel.__name__ in saved_panels
            panel_icon = gtk.gdk.pixbuf_new_from_file_at_size(panel.__icon__, 32, 32)
            text = "<b>%s</b>\n%s" % (panel.__title__, panel.__desc__)
            store.append((checked, panel_icon, text, panel))
        
        self.tv = widgets["treeview1"]
        self.tv.set_model(store)
        
        self.widgets['panel_about_button'].connect('clicked', self.panel_about)
        self.widgets['panel_enable_button'].connect('toggled', self.panel_toggled)
        self.tv.get_selection().connect('changed', self.selection_changed)
        
        pixbuf = gtk.CellRendererPixbuf()
        pixbuf.props.yalign = 0
        pixbuf.props.ypad = 3
        pixbuf.props.xpad = 3
        self.tv.append_column(gtk.TreeViewColumn("Icon", pixbuf, pixbuf=1, sensitive=0))
        
        uistuff.appendAutowrapColumn(self.tv, 200, "Name", markup=2, sensitive=0)
        
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
        
        d = gtk.MessageDialog (type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE)
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


class ThemeTab:

    
    def __init__ (self, widgets):
        
        conf.set("pieceTheme", conf.get("pieceTheme", "pychess"))

        self.themes = self.discover_themes()
        
        store = gtk.ListStore(gtk.gdk.Pixbuf, str)
        
        for theme in self.themes:
            pngfile = "%s/%s.png" % (addDataPrefix("pieces"), theme)
        
            if isfile(pngfile):
                pixbuf = gtk.gdk.pixbuf_new_from_file(pngfile)
                store.append((pixbuf, theme))
            else:
                print "WARNING: No piece theme preview icons find. Run create_theme_preview.sh !"
                break

        iconView = widgets["pieceTheme"]
        
        iconView.set_model(store)
        iconView.set_pixbuf_column(0)
        iconView.set_text_column(1)
        
        def _get_active(iconview):
            model = iconview.get_model()
            selected = iconview.get_selected_items()
            
            if len(selected) == 0:
                return conf.get("pieceTheme", "pychess")
            
            i = selected[0][0]
            theme = model[i][1]
            Pieces.set_piece_theme(theme)
            return theme
        
        def _set_active(iconview, value):
            try:
                index = self.themes.index(value)
            except ValueError:
                index = 0
            iconview.select_path((index,))
                
        uistuff.keep (widgets["pieceTheme"], "pieceTheme", _get_active, _set_active)

    def discover_themes(self):
        themes = ['Pychess']
        
        pieces = addDataPrefix("pieces")
        themes += [d.capitalize() for d in listdir(pieces) if isdir(os.path.join(pieces,d)) and d != 'ttf']
        
        ttf = addDataPrefix("pieces/ttf")
        themes += ["ttf-" + splitext(d)[0].capitalize() for d in listdir(ttf) if splitext(d)[1] == '.ttf']
        themes.sort()
        
        return themes
