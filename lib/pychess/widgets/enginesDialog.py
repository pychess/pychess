import os

import gtk
import gobject

from xml.etree.ElementTree import fromstring

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
            lambda w,e: delete_event(w) if e.keyval == gtk.keysyms.Escape else None)

        firstRun = False

    widgets["manage_engines_dialog"].show()


class EnginesDialog():
    def __init__(self, widgets):
        self.widgets = widgets
        self.dialog = self.widgets["manage_engines_dialog"]
        
        uistuff.keepWindowSize("engineswindow", self.dialog, defaultSize=(600, 500))

        # Put engines into tree store
        allstore = gtk.ListStore(gtk.gdk.Pixbuf, str)
        
        self.tv = self.widgets["engines_treeview"]
        self.tv.set_model(allstore)
        self.tv.append_column(gtk.TreeViewColumn(
                "Flag", gtk.CellRendererPixbuf(), pixbuf=0))
        self.tv.append_column(gtk.TreeViewColumn(
                "Name", gtk.CellRendererText(), text=1))

        # Add cell renderer to protocol combo column
        protocol_combo = self.widgets["engine_protocol_combo"]
        cell = gtk.CellRendererText()
        protocol_combo.pack_start(cell, True)
        protocol_combo.add_attribute(cell, "text", 0)

        # Add columns and cell renderers to options treeview 
        self.options_store = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        optv = self.widgets["options_treeview"]
        optv.set_model(self.options_store)
        optv.append_column(gtk.TreeViewColumn(
           "Option", gtk.CellRendererText(), text=0))
        optv.append_column(gtk.TreeViewColumn(
           "Data", KeyValueCellRenderer(self.options_store), data=1))

        self.cur_engine = None
        self.default_workdir = getEngineDataPrefix()

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

        self.widgets["remove_engine_button"].connect("clicked", remove)

        ################################################################
        # add button
        ################################################################
        self.add = False
        def add(button):
            self.add = True
            engine_chooser_dialog.run()

        self.widgets["add_engine_button"].connect("clicked", add)


        ################################################################
        # engine name
        ################################################################
        def name_changed(widget, event):
            if self.cur_engine is not None:
                new_name = self.widgets["engine_name_entry"].get_text().strip()
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
                        self.widgets["engine_name_entry"].set_text(old_name)
                        print "Name %s allready exist" % new_name

        self.widgets["engine_name_entry"].connect("focus-out-event", name_changed)


        ################################################################
        # engine args
        ################################################################
        def args_changed(widget, event):
            if self.cur_engine is not None:
                new_args = self.widgets["engine_args_entry"].get_text().strip()
                xmlengine = discoverer.getEngines()[self.cur_engine]
                args = xmlengine.find("args")
                args.clear()
                args.append(fromstring('<arg value="%s"/>' % new_args))
                discoverer.save()

        self.widgets["engine_args_entry"].connect("focus-out-event", args_changed)


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
            if new_directory != old_directory and new_directory != self.default_workdir:
                xmlengine.set("directory", new_directory)
                discoverer.save()

        dir_chooser_button.connect("current-folder-changed", select_dir)


        ################################################################
        # engine protocol
        ################################################################
        def protocol_changed(widget):
            if self.cur_engine is not None and not self.add:
                active = self.widgets["engine_protocol_combo"].get_active()
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

        self.widgets["engine_protocol_combo"].connect("changed", protocol_changed)


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
                #try:
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
                    self.widgets["engine_name_entry"].set_text(binname)
                    self.widgets["engine_protocol_combo"].set_active(0 if uci else 1)
                    self.widgets["engine_args_entry"].set_text("")
                    
                    name = self.widgets["engine_name_entry"].get_text().strip()
                    active = self.widgets["engine_protocol_combo"].get_active()
                    protocol = "uci" if active==0 else "cecp"
                    
                    # When changing an existing engine, first delete the old one
                    if not self.add and self.cur_engine is not None:
                        discoverer.removeEngine(self.cur_engine)
                    self.add = False
                    discoverer.addEngine(name, new_engine, protocol)
                    self.cur_engine = name
                    glock_connect_after(discoverer, "engine_discovered", update_store)
                    discoverer.start()
                #except:
                    #print "There is something wrong with this executable"
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
                self.widgets['copy_engine_button'].set_sensitive(True)
                self.widgets['remove_engine_button'].set_sensitive(True)
                row = store.get_path(iter)[0]
                name = store[row][1]
                self.cur_engine = name
                xmlengine = discoverer.getEngines()[name]
                self.widgets["engine_name_entry"].set_text(xmlengine.get("binname"))
                engine_chooser_dialog.set_filename(xmlengine.find("path").text.strip())
                args = [a.get('value') for a in xmlengine.findall('args/arg')]
                self.widgets["engine_args_entry"].set_text(' '.join(args))
                directory = xmlengine.get("directory")
                d = directory if directory is not None else self.default_workdir
                dir_chooser_dialog.set_current_folder(d)
                self.widgets["engine_protocol_combo"].set_active(0 if xmlengine.get("protocol")=="uci" else 1)
                update_options()
                    
        tree_selection = self.tv.get_selection()
        tree_selection.connect('changed', selection_changed)
        tree_selection.select_path((0,))


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
