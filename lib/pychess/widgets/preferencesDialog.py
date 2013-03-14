import sys, os
from os import listdir
from os.path import isdir, isfile, splitext
from xml.dom import minidom
from xml.etree.ElementTree import fromstring

import gtk, gobject

from pychess.System.prefix import addDataPrefix, getDataPrefix, getUserDataPrefix
from pychess.System.glock import glock_connect_after
from pychess.System import conf, gstreamer, uistuff
from pychess.Players.engineNest import discoverer, is_uci, is_cecp
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
    HintTab(widgets)
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
                    "hideTabs", "autoRotate", "faceToFace", "showCords", "showCaptured",
                    "figuresInNotation", "autoCallFlag","fullAnimation", "moveAnimation", "noAnimation"):
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
        # Put engines into tree store
        
        allstore = gtk.ListStore(gtk.gdk.Pixbuf, str)
        
        self.tv = widgets["engines_treeview"]
        self.tv.set_model(allstore)
        self.tv.append_column(gtk.TreeViewColumn(
                "Flag", gtk.CellRendererPixbuf(), pixbuf=0))
        self.tv.append_column(gtk.TreeViewColumn(
                "Name", gtk.CellRendererText(), text=1))

        # Add cell renderer to protocol combo column
        protocol_combo = widgets["engine_protocol_combo"]
        cell = gtk.CellRendererText()
        protocol_combo.pack_start(cell, True)
        protocol_combo.add_attribute(cell, "text", 0)

        # Add columns and cell renderers to options treeview 
        self.options_store = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        optv = widgets["options_treeview"]
        optv.set_model(self.options_store)
        optv.append_column(gtk.TreeViewColumn(
           "Option", gtk.CellRendererText(), text=0))
        optv.append_column(gtk.TreeViewColumn(
           "Data", KeyValueCellRenderer(self.options_store), data=1))

        self.cur_engine = None

        def update_options(*args):
            if self.cur_engine is not None:
                engines = discoverer.getEngines()
                if self.cur_engine not in engines:
                    self.cur_engine = discoverer.getEngines().keys()[0]
                xmlengine = engines[self.cur_engine]
                options_tags = xmlengine.findall(".//options")
                if options_tags:
                    self.options_store.clear()
                    for option in options_tags[0].getchildren():
                        key = option.get("name")
                        val = {}
                        val["xmlelement"] = option
                        opt_type = option.tag.split("-")[0]
                        val["type"] = opt_type
                        if opt_type == "check":
                            val["default"] = option.get("default").lower() == "true"
                            val["value"] = bool(option.get("value", default=val["default"]))
                        elif opt_type == "spin":
                            val["default"] = int(option.get("default"))
                            val["value"] = int(option.get("value", default=val["default"]))
                            val["max"] = int(option.get("max"))
                            val["min"] = int(option.get("min"))
                        elif opt_type == "string":
                            val["default"] = option.get("default")
                            val["value"] = option.get("value", default=val["default"])
                        elif opt_type == "combo":
                            val["default"] = option.get("default")
                            val["value"] = option.get("value", default=val["default"])
                            choices = [var.get("name") for var in option.findall("var")]
                            val["choices"] = choices
                        self.options_store.append([key, val])

        from pychess.widgets import newGameDialog
        def update_store(*args):
            allstore.clear()
            newGameDialog.createPlayerUIGlobals(discoverer)
            # don't add the very first (Human) player to engine store
            for item in newGameDialog.playerItems[0][1:]:
                allstore.append(item)
            update_options()

        update_store()
        
        ################################################################
        # remove button
        ################################################################
        def remove(button):
            if self.cur_engine is not None:
                self.widgets['remove_engine_button'].set_sensitive(False)
                discoverer.removeEngine(self.cur_engine)
                discoverer.save()
                update_store(discoverer)
                ts = self.tv.get_selection()
                ts.select_path((0,))

        widgets["remove_engine_button"].connect("clicked", remove)

        ################################################################
        # add button
        ################################################################
        self.add = False
        def add(button):
            self.add = True
            engine_chooser_dialog.run()

        widgets["add_engine_button"].connect("clicked", add)


        ################################################################
        # engine name
        ################################################################
        def name_changed(widget, event):
            if self.cur_engine is not None:
                new_name = widgets["engine_name_entry"].get_text().strip()
                old_name = self.cur_engine
                if new_name and new_name != old_name:
                    engines = discoverer.getEngines()
                    if new_name not in engines:
                        engines[new_name] = engines[old_name]
                        engines[new_name].set("binname", new_name)
                        del engines[old_name]
                        self.cur_engine = new_name
                        discoverer.start()
                    else:
                        widgets["engine_name_entry"].set_text(old_name)
                        print "Name %s allready exist" % new_name

        widgets["engine_name_entry"].connect("focus-out-event", name_changed)


        ################################################################
        # engine args
        ################################################################
        def args_changed(widget, event):
            if self.cur_engine is not None:
                new_args = widgets["engine_args_entry"].get_text().strip()
                xmlengine = discoverer.getEngines()[self.cur_engine]
                args = xmlengine.find("args")
                args.clear()
                args.append(fromstring('<arg value="%s"/>' % new_args))
                discoverer.save()

        widgets["engine_args_entry"].connect("focus-out-event", args_changed)


        ################################################################
        # engine working directory
        ################################################################
        dir_chooser_dialog = gtk.FileChooserDialog(_("Select working directory"), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dir_chooser_button = gtk.FileChooserButton(dir_chooser_dialog)

        self.widgets["dirChooserDock"].add(dir_chooser_button)
        dir_chooser_button.show()

        def select_dir(button):
            new_directory = dir_chooser_dialog.get_filename()
            xmlengine = discoverer.getEngines()[self.cur_engine]
            old_directory = xmlengine.get("directory")
            if new_directory != old_directory:
                xmlengine.set("directory", new_directory)
                discoverer.save()

        dir_chooser_button.connect("current-folder-changed", select_dir)


        ################################################################
        # engine protocol
        ################################################################
        def protocol_changed(widget):
            if self.cur_engine is not None and not self.add:
                active = widgets["engine_protocol_combo"].get_active()
                new_protocol = "uci" if active==0 else "cecp"
                xmlengine = discoverer.getEngines()[self.cur_engine]
                old_protocol = xmlengine.get("protocol")
                if new_protocol != old_protocol:
                    engine = engine_chooser_dialog.get_filename()
                    # is the new protocol supported by the engine?
                    if new_protocol == "uci":
                        ok = is_uci(engine)
                    else:
                        ok = is_cecp(engine)
                    if ok:
                        # discover engine options for new protocol
                        xmlengine.set("protocol", new_protocol)
                        xmlengine.set("protover", "2")
                        xmlengine.set('recheck', 'true')
                        glock_connect_after(discoverer, "engine_discovered", update_options)
                        discoverer.start()
                    else:
                        # restore the original protocol
                        widgets["engine_protocol_combo"].set_active(0 if old_protocol=="uci" else 1)

        widgets["engine_protocol_combo"].connect("changed", protocol_changed)


        ################################################################
        # engine
        ################################################################
        engine_chooser_dialog = gtk.FileChooserDialog(_("Select engine"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        engine_chooser_button = gtk.FileChooserButton(engine_chooser_dialog)

        filter = gtk.FileFilter()
        filter.set_name(_("Chess engines"))
        filter.add_mime_type("application/x-executable")
        engine_chooser_dialog.add_filter(filter)

        self.widgets["engineChooserDock"].add(engine_chooser_button)
        engine_chooser_button.show()

        def select_new_engine(button):
            new_engine = engine_chooser_dialog.get_filename()
            if new_engine:
                try:
                    uci = is_uci(new_engine)
                    if not uci:
                        if not is_cecp(new_engine):
                            # restore the original
                            xmlengine = discoverer.getEngines()[self.cur_engine]
                            engine_chooser_dialog.set_filename(xmlengine.find("path").text.strip())
                            return
                    path, binname = os.path.split(new_engine)
                    for name in discoverer.getEngines():
                        if name == binname:
                            binname = name + "(1)"
                            break
                    widgets["engine_name_entry"].set_text(binname)
                    widgets["engine_protocol_combo"].set_active(0 if uci else 1)
                    widgets["engine_directory_entry"].set_text("")
                    widgets["engine_args_entry"].set_text("")
                    
                    name = widgets["engine_name_entry"].get_text().strip()
                    active = widgets["engine_protocol_combo"].get_active()
                    protocol = "uci" if active==0 else "cecp"
                    
                    # When changing an existing engine, first delete the old one
                    if not self.add and self.cur_engine is not None:
                        discoverer.removeEngine(self.cur_engine)
                    self.add = False
                    discoverer.addEngine(name, new_engine, protocol)
                    self.cur_engine = name
                    glock_connect_after(discoverer, "engine_discovered", update_store)
                    discoverer.start()
                except:
                    print "There is something wrong with this executable"
            else:
                # restore the original
                xmlengine = discoverer.getEngines()[self.cur_engine]
                engine_chooser_dialog.set_filename(xmlengine.find("path").text.strip())
                
        engine_chooser_button.connect("file-set", select_new_engine)


        ################################################################
        # engine tree
        ################################################################
        def selection_changed(treeselection):
            store, iter = self.tv.get_selection().get_selected()
            if iter:
                widgets['copy_engine_button'].set_sensitive(True)
                widgets['remove_engine_button'].set_sensitive(True)
                row = store.get_path(iter)[0]
                name = store[row][1]
                self.cur_engine = name
                xmlengine = discoverer.getEngines()[name]
                widgets["engine_name_entry"].set_text(xmlengine.get("binname"))
                engine_chooser_dialog.set_filename(xmlengine.find("path").text.strip())
                args = [a.get('value') for a in xmlengine.findall('args/arg')]
                widgets["engine_args_entry"].set_text(' '.join(args))
                directory = xmlengine.get("directory") if xmlengine.get("directory") is not None else ""
                dir_chooser_dialog.set_current_folder(directory)
                widgets["engine_protocol_combo"].set_active(0 if xmlengine.get("protocol")=="uci" else 1)
                update_options()
                    
        tree_selection = self.tv.get_selection()
        tree_selection.connect('changed', selection_changed)
        tree_selection.select_path((0,))


################################################################################
# Hint initing                                                               #
################################################################################

class HintTab:
    def __init__ (self, widgets):
        self.widgets = widgets
    
        # Opening book
        default_path = os.path.join(addDataPrefix("pychess_book.bin"))
        path = conf.get("opening_file_entry", default_path)
        conf.set("opening_file_entry", path)

        book_chooser_dialog = gtk.FileChooserDialog(_("Select book file"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        book_chooser_button = gtk.FileChooserButton(book_chooser_dialog)

        filter = gtk.FileFilter()
        filter.set_name(_("Opening books"))
        filter.add_pattern("*.bin")
        book_chooser_dialog.add_filter(filter)
        book_chooser_dialog.set_filename(path)

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
        uistuff.keep(widgets["opening_check"], "opening_check")

        # Endgame
        conf.set("online_egtb_check", conf.get("online_egtb_check", 0))
        uistuff.keep(widgets["online_egtb_check"], "online_egtb_check")

        default_path = os.path.join(getDataPrefix())
        path = conf.get("egtb_path_entry", default_path)
        conf.set("egtb_path_entry", path)

        button = widgets["gaviota_filechooser_button"]
        endgamedialog = gtk.FileChooserDialog(_("Select Gaviota TB path"), None, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        endgamedialog.set_current_folder(path)
        
        def on_gaviota_filechooser_button_clicked(button):
            if endgamedialog.run() == gtk.RESPONSE_OK:
                new_path = endgamedialog.get_filename()
                if new_path is not None:
                    widgets["egtb_path_entry"].set_text(new_path)
            endgamedialog.hide()
        widgets["gaviota_filechooser_button"].connect_after("clicked",
                                                on_gaviota_filechooser_button_clicked)
        uistuff.keep(widgets["egtb_path_entry"], "egtb_path_entry")
        
        def on_endgame_check_toggled (check):
            widgets["endgame_vbox"].set_sensitive(check.get_active())
        
        widgets["endgame_check"].connect_after("toggled",
                                                on_endgame_check_toggled)
        uistuff.keep(widgets["endgame_check"], "endgame_check")

        # Analyzing engines
        uistuff.createCombo(widgets["ana_combobox"])
        uistuff.createCombo(widgets["inv_ana_combobox"])

        from pychess.widgets import newGameDialog
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
        soundfilter.set_name(_("Sound files"))
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


class KeyValueCellRenderer(gtk.GenericCellRenderer):
    """ Custom renderer providing different renderers in different rows.
        The model parameter is a gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        containing key data pairs. Each data is a dictionary with
        type, value, min, max (for spin options), chices (list of combo options)
        The 'type' can be 'check', 'spin', 'string', 'combo', 'button'.
        Examples:
            ('Nullmove', {'type': 'check', 'value': True})
            ('Selectivity', {'type': 'spin', 'min': 0, 'max': 4, 'value': 2})
            ('Style', {'type': 'combo', 'choices': ['Solid', 'Normal','Risky'], 'value': 'Normal'})
            ('NalimovPath', {'type': 'string', 'value': 'c:\'})
            ('Clear Hash', {'type': 'button'})
    """
    __gproperties__ = {"data": (gobject.TYPE_PYOBJECT, "Data", "Data", gobject.PARAM_READWRITE)}
    
    def __init__(self, model):
        gtk.GenericCellRenderer.__init__(self)

        self.data = None

        self.text_renderer = gtk.CellRendererText()
        self.text_renderer.set_property("editable", True)
        self.text_renderer.connect("edited", self.text_edited_cb, model)

        self.toggle_renderer = gtk.CellRendererToggle()
        self.toggle_renderer.set_property("activatable", True)
        self.toggle_renderer.set_property("xalign", 0)
        self.toggle_renderer.connect("toggled", self.toggled_cb, model)

        self.spin_renderer = gtk.CellRendererSpin()
        self.spin_renderer.set_property("editable", True)
        self.spin_renderer.connect("edited", self.spin_edited_cb, model)

        self.combo_renderer = gtk.CellRendererCombo()
        self.combo_renderer.set_property("has_entry", False)
        self.combo_renderer.set_property("editable", True)
        self.combo_renderer.set_property("text_column", 0)
        self.combo_renderer.connect("edited", self.text_edited_cb, model)

        self.button_renderer = gtk.CellRendererText()
        self.button_renderer.set_property("editable", False)

    def text_edited_cb(self, cell, path, new_text, model):
        model[path][1]["value"] = new_text
        model[path][1]["xmlelement"].set("value", model[path][1]["value"])
        discoverer.save()
        return

    def toggled_cb(self, cell, path, model):
        model[path][1]["value"] = not model[path][1]["value"]
        model[path][1]["xmlelement"].set("value", str(model[path][1]["value"]))
        discoverer.save()
        return
        
    def spin_edited_cb(self, cell, path, new_text, model):
        model[path][1]["value"] = new_text
        model[path][1]["xmlelement"].set("value", model[path][1]["value"])
        discoverer.save()
        return

    def _get_renderer(self):
        if self.data["type"] == "check":
            return self.toggle_renderer
        elif self.data["type"] == "spin":
            return self.spin_renderer
        elif self.data["type"] == "string":
            return self.text_renderer
        elif self.data["type"] == "combo":
            return self.combo_renderer
        elif self.data["type"] == "button":
            return self.button_renderer
    renderer = property(_get_renderer)
    
    def do_set_property(self, pspec, value):
        if value["type"] == "check":
            self.toggle_renderer.set_active(value["value"])
            self.set_property("mode", gtk.CELL_RENDERER_MODE_ACTIVATABLE)
        elif value["type"] == "spin":
            adjustment = gtk.Adjustment(value=int(value["value"]), lower=value["min"], upper=value["max"], step_incr=1)
            self.spin_renderer.set_property("adjustment", adjustment)
            self.spin_renderer.set_property("text", value["value"])
            self.set_property("mode", gtk.CELL_RENDERER_MODE_EDITABLE)
        elif value["type"] == "string":
            self.text_renderer.set_property("text", value["value"])
            self.set_property("mode", gtk.CELL_RENDERER_MODE_EDITABLE)
        elif value["type"] == "combo":
            liststore = gtk.ListStore(str)
            for choice in value["choices"]:
                liststore.append([choice])
            self.combo_renderer.set_property("model", liststore)
            self.combo_renderer.set_property("text", value["value"])
            self.set_property("mode", gtk.CELL_RENDERER_MODE_EDITABLE)
        elif value["type"] == "button":
            self.button_renderer.set_property("text", "")

        setattr(self, pspec.name, value)
        
    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_get_size(self, widget, cell_area=None):
        return self.renderer.get_size(widget, cell_area=cell_area)
        
    def on_render(self, window, widget, background_area, cell_area, expose_area, flags):
        self.renderer.render(window, widget, background_area, cell_area, expose_area, flags)
        
    def on_activate(self, event, widget, path, background_area, cell_area, flags):
        return self.renderer.activate(event, widget, path, background_area, cell_area, flags)
        
    def on_start_editing(self, event, widget, path, background_area, cell_area, flags):
        return self.renderer.start_editing(event, widget, path, background_area, cell_area, flags)

gobject.type_register(KeyValueCellRenderer)
