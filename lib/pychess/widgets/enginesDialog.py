import os

from gi.repository import Gtk
from gi.repository import GObject

from pychess.System import uistuff
from pychess.System.glock import glock_connect_after
from pychess.System.prefix import getEngineDataPrefix
from pychess.Players.engineNest import discoverer, is_uci, is_cecp
from pychess.widgets import newGameDialog


firstRun = True
def run(widgets):
    global firstRun
    if firstRun:
        EnginesDialog(widgets)

        def delete_event (widget, *args):
            widgets["manage_engines_dialog"].hide()
            return True
        widgets["manage_engines_dialog"].connect("delete-event", delete_event)
        widgets["engines_close_button"].connect("clicked", delete_event)
        widgets["manage_engines_dialog"].connect("key-press-event",
            lambda w,e: delete_event(w) if e.keyval == Gdk.KEY_Escape else None)

        firstRun = False

    widgets["manage_engines_dialog"].show()


class EnginesDialog():
    def __init__(self, widgets):
        self.widgets = widgets
        self.dialog = self.widgets["manage_engines_dialog"]
        self.cur_engine = None
        self.default_workdir = getEngineDataPrefix()
        
        uistuff.keepWindowSize("engineswindow", self.dialog, defaultSize=(600, 500))

        # Put engines into tree store
        allstore = Gtk.ListStore(GdkPixbuf.Pixbuf, str)
        
        self.tv = self.widgets["engines_treeview"]
        self.tv.set_model(allstore)
        self.tv.append_column(Gtk.TreeViewColumn(
                "Flag", Gtk.CellRendererPixbuf(), pixbuf=0))
        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("editable", True)
        self.tv.append_column(Gtk.TreeViewColumn("Name", name_renderer, text=1))
        def name_edited(renderer, path, new_name):
            if self.cur_engine is not None:
                old_name = self.cur_engine
                if new_name and new_name != old_name:
                    names = [engine["name"] for engine in discoverer.getEngines()]
                    if new_name not in names:
                        engine = discoverer.getEngineByName(self.cur_engine)
                        engine["name"] = new_name
                        discoverer.save()
                        self.cur_engine = new_name
                        update_store()                        
                        # Notify playerCombos in NewGameTasker
                        discoverer.emit("all_engines_discovered")
        name_renderer.connect("edited", name_edited)

        # Add cell renderer to protocol combo column
        protocol_combo = self.widgets["engine_protocol_combo"]
        cell = Gtk.CellRendererText()
        protocol_combo.pack_start(cell, True)
        protocol_combo.add_attribute(cell, "text", 0)

        # Add columns and cell renderers to options treeview 
        self.options_store = Gtk.ListStore(str, GObject.TYPE_PYOBJECT)
        optv = self.widgets["options_treeview"]
        optv.set_model(self.options_store)
        optv.append_column(Gtk.TreeViewColumn(
           "Option", Gtk.CellRendererText(), text=0))
        optv.append_column(Gtk.TreeViewColumn(
           "Data", KeyValueCellRenderer(self.options_store), data=1))

        def update_options(*args):
            if self.cur_engine is not None:
                engines = discoverer.getEngines()
                names = [engine["name"] for engine in engines]
                # After deleting an engine we will select first
                if self.cur_engine not in names:
                    self.cur_engine = engines[0]["name"]
                engine = discoverer.getEngineByName(self.cur_engine)
                options = engine.get("options")
                if options:
                    self.options_store.clear()
                    for option in options:
                        key = option["name"]
                        val = option
                        if option["type"] != "button":
                            val["default"] = option.get("default")
                            val["value"] = option.get("value", val["default"])
                        self.options_store.append([key, val])

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
                engine = discoverer.getEngineByName(self.cur_engine)
                discoverer.removeEngine(self.cur_engine)
                discoverer.save()
                update_store(discoverer)
                # Notify playerCombos in NewGameTasker
                discoverer.emit("all_engines_discovered")
                ts = self.tv.get_selection()
                ts.select_path((0,))

        self.widgets["remove_engine_button"].connect("clicked", remove)

        ################################################################
        # add button
        ################################################################
        engine_chooser_dialog = Gtk.FileChooserDialog(_("Select engine"), None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        filter = Gtk.FileFilter()
        filter.set_name(_("Chess engines"))
        filter.add_mime_type("application/x-executable")
        engine_chooser_dialog.add_filter(filter)
        self.add = False

        def add(button):
            self.add = True
            response = engine_chooser_dialog.run()

            if response == Gtk.ResponseType.OK:
                new_engine = engine_chooser_dialog.get_filename()
                if new_engine:
                    try:
                        uci = is_uci(new_engine)
                        if not uci:
                            if not is_cecp(new_engine):
                                # restore the original
                                engine = discoverer.getEngineByName(self.cur_engine)
                                engine_chooser_dialog.set_filename(engine["command"])
                                print "Maybe not a chess engine"
                                return
                        path, binname = os.path.split(new_engine)
                        for e in discoverer.getEngines():
                            if e["name"] == binname:
                                binname = e["name"] + "(1)"
                                break
                        self.widgets["engine_command_entry"].set_text(new_engine)
                        self.widgets["engine_protocol_combo"].set_active(0 if uci else 1)
                        self.widgets["engine_args_entry"].set_text("")
                        
                        active = self.widgets["engine_protocol_combo"].get_active()
                        protocol = "uci" if active==0 else "xboard"
                        
                        discoverer.addEngine(binname, new_engine, protocol)
                        self.cur_engine = binname
                        glock_connect_after(discoverer, "engine_discovered", update_store)
                        self.add = False
                        discoverer.discover()
                    except:
                        print "There is something wrong with this executable"
                else:
                    # restore the original
                    engine = discoverer.getEngineByName(self.cur_engine)
                    engine_chooser_dialog.set_filename(engine["command"])
            engine_chooser_dialog.hide()
            
        self.widgets["add_engine_button"].connect("clicked", add)


        ################################################################
        # engine args
        ################################################################
        def args_changed(widget):
            if self.cur_engine is not None:
                new_args = self.widgets["engine_args_entry"].get_text().strip()
                engine = discoverer.getEngineByName(self.cur_engine)
                old_args = engine.get("args")
                if new_args != old_args:
                    engine["args"] = new_args.split()
                    discoverer.save()

        self.widgets["engine_args_entry"].connect("changed", args_changed)


        ################################################################
        # engine working directory
        ################################################################
        dir_chooser_dialog = Gtk.FileChooserDialog(_("Select working directory"), None, Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dir_chooser_button = Gtk.FileChooserButton(dir_chooser_dialog)

        self.widgets["dirChooserDock"].add(dir_chooser_button)
        dir_chooser_button.show()

        def select_dir(button):
            new_directory = dir_chooser_dialog.get_filename()
            engine = discoverer.getEngineByName(self.cur_engine)
            old_directory = engine.get("workingDirectory")
            if new_directory != old_directory and new_directory != self.default_workdir:
                engine["workingDirectory"] = new_directory
                discoverer.save()

        dir_chooser_button.connect("current-folder-changed", select_dir)


        ################################################################
        # engine protocol
        ################################################################
        def protocol_changed(widget):
            if self.cur_engine is not None and not self.add and not self.selection:
                active = self.widgets["engine_protocol_combo"].get_active()
                new_protocol = "uci" if active==0 else "xboard"
                engine = discoverer.getEngineByName(self.cur_engine)
                old_protocol = engine["protocol"]
                if new_protocol != old_protocol:
                    engine_command = engine_chooser_dialog.get_filename()
                    # is the new protocol supported by the engine?
                    if new_protocol == "uci":
                        ok = is_uci(engine_command)
                    else:
                        ok = is_cecp(engine_command)
                    if ok:
                        # discover engine options for new protocol
                        engine["protocol"] = new_protocol
                        engine["recheck"] = True
                        glock_connect_after(discoverer, "engine_discovered", update_options)
                        discoverer.discover()
                    else:
                        # restore the original protocol
                        widgets["engine_protocol_combo"].set_active(0 if old_protocol=="uci" else 1)

        self.widgets["engine_protocol_combo"].connect("changed", protocol_changed)


        ################################################################
        # engine tree
        ################################################################
        self.selection = False
        def selection_changed(treeselection):
            store, iter = self.tv.get_selection().get_selected()
            if iter:
                self.selection = True
                row = store.get_path(iter)[0]
                name = store[row][1]
                self.cur_engine = name
                engine = discoverer.getEngineByName(name)
                self.widgets['copy_engine_button'].set_sensitive(True)
                if "PyChess.py" in engine["command"]:
                    self.widgets['remove_engine_button'].set_sensitive(False)
                else:
                    self.widgets['remove_engine_button'].set_sensitive(True)
                self.widgets["engine_command_entry"].set_text(engine["command"])
                engine_chooser_dialog.set_filename(engine["command"])
                args = [] if engine.get("args") is None else engine.get("args")
                self.widgets["engine_args_entry"].set_text(' '.join(args))
                directory = engine.get("workingDirectory")
                d = directory if directory is not None else self.default_workdir
                dir_chooser_dialog.set_current_folder(d)
                self.widgets["engine_protocol_combo"].set_active(0 if engine["protocol"]=="uci" else 1)
                update_options()
                self.selection = False
                    
        tree_selection = self.tv.get_selection()
        tree_selection.connect('changed', selection_changed)
        tree_selection.select_path((0,))


class KeyValueCellRenderer(Gtk.CellRenderer):
    """ Custom renderer providing different renderers in different rows.
        The model parameter is a Gtk.ListStore(str, GObject.TYPE_PYOBJECT)
        containing key data pairs. Each data is a dictionary with
        name, type, default, value, min, max (for spin options), choices (list of combo options)
        The 'type' can be 'check', 'spin', 'text', 'combo', 'button'.
        Examples:
            ('Nullmove', {'name': 'Nullmove', 'default': false, 'type': 'check', 'value': True})
            ('Selectivity', {'name': 'Selectivity', 'default': 1, 'type': 'spin', 'min': 0, 'max': 4, 'value': 2})
            ('Style', {'name': 'Style', 'default': 'Solid', 'type': 'combo', 'choices': ['Solid', 'Normal','Risky'], 'value': 'Normal'})
            ('NalimovPath', {'name': 'NalimovPath', 'default': '',  'type': 'text', 'value': '/home/egtb'})
            ('Clear Hash', {'name': 'Clear Hash', 'type': 'button'})
    """
    __gproperties__ = {"data": (GObject.TYPE_PYOBJECT, "Data", "Data", GObject.PARAM_READWRITE)}
    
    def __init__(self, model):
        GObject.GObject.__init__(self)       
        self.data = None

        self.text_renderer = Gtk.CellRendererText()
        self.text_renderer.set_property("editable", True)
        self.text_renderer.connect("edited", self.text_edited_cb, model)

        self.toggle_renderer = Gtk.CellRendererToggle()
        self.toggle_renderer.set_property("activatable", True)
        self.toggle_renderer.set_property("xalign", 0)
        self.toggle_renderer.connect("toggled", self.toggled_cb, model)

        self.ro_toggle_renderer = Gtk.CellRendererToggle()
        self.ro_toggle_renderer.set_property("activatable", False)
        self.ro_toggle_renderer.set_property("xalign", 0)

        self.spin_renderer = Gtk.CellRendererSpin()
        self.spin_renderer.set_property("editable", True)
        self.spin_renderer.connect("edited", self.spin_edited_cb, model)

        self.combo_renderer = Gtk.CellRendererCombo()
        self.combo_renderer.set_property("has_entry", False)
        self.combo_renderer.set_property("editable", True)
        self.combo_renderer.set_property("text_column", 0)
        self.combo_renderer.connect("edited", self.text_edited_cb, model)

        self.button_renderer = Gtk.CellRendererText()
        self.button_renderer.set_property("editable", False)

    def text_edited_cb(self, cell, path, new_text, model):
        model[path][1]["value"] = new_text
        discoverer.save()
        return

    def toggled_cb(self, cell, path, model):
        model[path][1]["value"] = not model[path][1]["value"]
        discoverer.save()
        return
        
    def spin_edited_cb(self, cell, path, new_text, model):
        model[path][1]["value"] = new_text
        discoverer.save()
        return

    def _get_renderer(self):
        if self.data["type"] == "check":
            if self.data["name"] == "UCI_Chess960":
                return self.ro_toggle_renderer
            else:
                return self.toggle_renderer
        elif self.data["type"] == "spin":
            return self.spin_renderer
        elif self.data["type"] == "text":
            return self.text_renderer
        elif self.data["type"] == "combo":
            return self.combo_renderer
        elif self.data["type"] == "button":
            return self.button_renderer
    renderer = property(_get_renderer)
    
    def do_set_property(self, pspec, value):
        if value["type"] == "check":
            self.toggle_renderer.set_active(value["value"])
            self.set_property("mode", Gtk.CellRendererMode.ACTIVATABLE)
        elif value["type"] == "spin":
            adjustment = Gtk.Adjustment(value=int(value["value"]), lower=value["min"], upper=value["max"], step_incr=1)
            self.spin_renderer.set_property("adjustment", adjustment)
            self.spin_renderer.set_property("text", value["value"])
            self.set_property("mode", Gtk.CellRendererMode.EDITABLE)
        elif value["type"] == "text":
            self.text_renderer.set_property("text", value["value"])
            self.set_property("mode", Gtk.CellRendererMode.EDITABLE)
        elif value["type"] == "combo":
            liststore = Gtk.ListStore(str)
            for choice in value["choices"]:
                liststore.append([choice])
            self.combo_renderer.set_property("model", liststore)
            self.combo_renderer.set_property("text", value["value"])
            self.set_property("mode", Gtk.CellRendererMode.EDITABLE)
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

GObject.type_register(KeyValueCellRenderer)
