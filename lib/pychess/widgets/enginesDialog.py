import os
import sys
import shutil

from gi.repository import Gtk, Gdk, GLib, GObject, Pango
from gi.repository.GdkPixbuf import Pixbuf

from pychess.System import uistuff
from pychess.System.prefix import getEngineDataPrefix, addDataPrefix
from pychess.Utils.IconLoader import get_pixbuf
from pychess.Players.engineNest import discoverer, is_uci, is_cecp, ENGINE_DEFAULT_LEVEL
from pychess.Players.engineList import VM_LIST, listEnginesFromPath
from pychess.Utils.isoCountries import ISO3166_LIST
from pychess.widgets import newGameDialog
from pychess.widgets import mainwindow

firstRun = True
engine_dialog = None


def run(widgets):
    global firstRun, engine_dialog
    if firstRun:
        # Display of the countries
        items = []
        for iso in ISO3166_LIST:
            path = addDataPrefix("flags/%s.png" % iso.iso2)
            if not(iso.iso2 and os.path.isfile(path)):
                path = addDataPrefix("flags/unknown.png")
            items.append((get_pixbuf(path), iso.country))
        uistuff.createCombo(widgets["engine_country_combo"], name="engine_country_combo",
                            ellipsize_mode=Pango.EllipsizeMode.END)
        data = [(item[0], item[1]) for item in items]
        uistuff.updateCombo(widgets["engine_country_combo"], data)

        engine_dialog = EnginesDialog(widgets)

        def cancel_event(widget, with_confirmation, *args):
            # Confirm if the changes need to be saved
            modified = discoverer.hasChanged()
            if modified and with_confirmation:
                dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO)
                dialog.set_markup(_("You have unsaved changes. Do you want to save before leaving?"))
                response = dialog.run()
                dialog.destroy()
                # if response == Gtk.ResponseType.CANCEL:
                #    return False
                if response == Gtk.ResponseType.NO:
                    discoverer.restore()
                if response == Gtk.ResponseType.YES:
                    discoverer.save()

            # Close the window
            widgets["manage_engines_dialog"].hide()
            return True

        def save_event(widget, *args):
            discoverer.save()
            widgets["manage_engines_dialog"].hide()
            return True

        widgets["manage_engines_dialog"].connect("delete-event", cancel_event, True)
        widgets["engine_cancel_button"].connect("clicked", cancel_event, False)
        widgets["engine_save_button"].connect("clicked", save_event)
        widgets["manage_engines_dialog"].connect(
            "key-press-event",
            lambda w, e: cancel_event(w, True) if e.keyval == Gdk.KEY_Escape else None)

    discoverer.backup()
    engine_dialog.widgets["enginebook"].set_current_page(0)
    widgets["manage_engines_dialog"].show()
    if not firstRun:
        engine_dialog.update_store()
    firstRun = False


class EnginesDialog():
    def update_options(self, *args):
        if self.cur_engine is not None:
            # Initial reset
            self.options_store.clear()

            # Detection of the name of the engine to reload
            engines = discoverer.getEngines()
            names = [engine["name"] for engine in engines]
            if self.cur_engine not in names:
                self.cur_engine = engines[0]["name"]
            engine = discoverer.getEngineByName(self.cur_engine)
            if engine:
                options = engine.get("options")
                if options:
                    options.sort(key=lambda obj: obj['name'].lower() if 'name' in obj else '')
                    for option in options:
                        key = option["name"]
                        val = option
                        if option["type"] != "button":
                            val["default"] = option.get("default")
                            val["value"] = option.get("value", val["default"])
                            modified = val["value"] != val["default"]
                        else:
                            modified = False
                        self.options_store.append(["*" if modified else "", key, val])

    def update_store(self, *args):
        newGameDialog.createPlayerUIGlobals(discoverer)
        engine_names = [row[1] for row in self.allstore]
        new_items = []
        # don't add the very first (Human) player to engine store
        for item in newGameDialog.allEngineItems:
            if item[1] not in engine_names:
                new_items.append(item)
        ts_iter = None
        for item in new_items:
            ts_iter = self.allstore.append(item)
        if ts_iter is not None:
            text_select = self.tv.get_selection()
            text_select.select_iter(ts_iter)
        self.update_options()

    def __init__(self, widgets):
        self.widgets = widgets
        self.dialog = self.widgets["manage_engines_dialog"]
        self.cur_engine = None
        self.default_workdir = getEngineDataPrefix()

        uistuff.keepWindowSize("engineswindow", self.dialog)

        # Put engines into tree store
        self.allstore = Gtk.ListStore(Pixbuf, str)

        self.tv = self.widgets["engines_treeview"]
        self.tv.set_model(self.allstore)
        self.tv.append_column(Gtk.TreeViewColumn("Flag", Gtk.CellRendererPixbuf(), pixbuf=0))
        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("editable", False)
        self.tv.append_column(Gtk.TreeViewColumn("Name", name_renderer, text=1))

        # Add cell renderer to protocol combo column
        protocol_combo = self.widgets["engine_protocol_combo"]
        protocol_combo.set_name("engine_protocol_combo")
        cell = Gtk.CellRendererText()
        protocol_combo.pack_start(cell, True)
        protocol_combo.add_attribute(cell, "text", 0)

        # Add columns and cell renderers to options treeview
        self.options_store = Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT)
        optv = self.widgets["options_treeview"]
        optv.set_model(self.options_store)
        optv.append_column(Gtk.TreeViewColumn("  ", Gtk.CellRendererText(), text=0))
        optv.append_column(Gtk.TreeViewColumn(_("Option"), Gtk.CellRendererText(), text=1))
        optv.append_column(Gtk.TreeViewColumn(_("Value"), KeyValueCellRenderer(self.options_store), data=2))

        self.update_store()

        def do_update_store(self, *args):
            GLib.idle_add(engine_dialog.update_store)

        discoverer.connect_after("engine_discovered", do_update_store)

        ################################################################
        # remove button
        ################################################################
        def remove(button):
            if self.cur_engine is not None:
                self.widgets['remove_engine_button'].set_sensitive(False)
                discoverer.removeEngine(self.cur_engine)

                selection = self.tv.get_selection()
                result = selection.get_selected()
                if result is not None:
                    model, ts_iter = result
                    model.remove(ts_iter)
                if model.iter_n_children() == 0:
                    clearView()

                # Notify playerCombos in NewGameTasker
                discoverer.emit("all_engines_discovered")

        self.widgets["remove_engine_button"].connect("clicked", remove)

        ################################################################
        # add button
        ################################################################
        engine_chooser_dialog = Gtk.FileChooserDialog(
            _("Select engine"), mainwindow(), Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.OK))

        filter = Gtk.FileFilter()
        filter.set_name(_("Executable files"))
        filter.add_mime_type("application/x-executable")
        filter.add_mime_type("application/x-sharedlib")
        filter.add_mime_type("application/x-ms-dos-executable")
        filter.add_mime_type("application/x-msdownload")
        filter.add_pattern("*.exe")
        for vm in VM_LIST:
            filter.add_pattern("*%s" % vm.ext)

        engine_chooser_dialog.add_filter(filter)
        self.add = False

        def add(button):
            self.add = True
            response = engine_chooser_dialog.run()

            if response == Gtk.ResponseType.OK:
                new_engine = engine_chooser_dialog.get_filename()
                binname = os.path.split(new_engine)[1]
                ext = os.path.splitext(new_engine)[1]

                # Verify if the engine already exists under the same name
                if new_engine != "":
                    for eng in discoverer.getEngines():
                        if eng["command"] == new_engine:
                            msg_dia = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                                        buttons=Gtk.ButtonsType.OK)
                            msg_dia.set_markup(_("<big><b>Unable to add %s</b></big>" % new_engine))
                            msg_dia.format_secondary_text(_("The engine is already installed under the same name"))
                            msg_dia.run()
                            msg_dia.hide()
                            new_engine = ""
                            break

                # Detect the host application
                if new_engine != "":
                    vm_name = None
                    vm_args = None
                    vmpath = ""

                    # Scripting
                    for vm in VM_LIST:
                        if ext == vm.ext:
                            vm_name = vm.name
                            vm_args = vm.args
                            break

                    # Wine for Windows application under Linux
                    if vm_name is None and new_engine.lower().endswith(".exe") and sys.platform != "win32":
                        vm_name = "wine"

                    # Check that the interpreter is available
                    if vm_name is not None:
                        vmpath = shutil.which(vm_name, mode=os.R_OK | os.X_OK)
                        if vmpath is None:
                            msg_dia = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                                        buttons=Gtk.ButtonsType.OK)
                            msg_dia.set_markup(_("<big><b>Unable to add %s</b></big>" % new_engine))
                            msg_dia.format_secondary_text(vm_name + _(" is not installed"))
                            msg_dia.run()
                            msg_dia.hide()
                            new_engine = ""

                # Next checks
                if new_engine:
                    vm_ext_list = [vm.ext for vm in VM_LIST]
                    if ext not in vm_ext_list and not os.access(new_engine, os.X_OK):
                        msg_dia = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                                    buttons=Gtk.ButtonsType.OK)
                        msg_dia.set_markup(_("<big><b>%s is not marked executable in the filesystem</b></big>" %
                                             new_engine))
                        msg_dia.format_secondary_text(_("Try chmod a+x %s" % new_engine))
                        msg_dia.run()
                        msg_dia.hide()
                        self.add = False
                        engine_chooser_dialog.hide()
                        return

                    try:
                        engine_command = []
                        if vmpath:
                            engine_command.append(vmpath)
                        if vm_args is not None:
                            engine_command += vm_args
                        engine_command.append(new_engine)

                        # Search the engines based on the most expectable protocol
                        refeng = discoverer.getReferencedEngine(binname)
                        if refeng is not None and refeng["protocol"] == "xboard":
                            checkers = [is_cecp, is_uci]
                        else:
                            checkers = [is_uci, is_cecp]

                        uci = False
                        for checker in checkers:
                            check_ok = checker(engine_command)
                            if check_ok:
                                uci = checker is is_uci
                                break
                            else:
                                continue

                        if not check_ok:
                            # restore the original
                            engine = discoverer.getEngineByName(self.cur_engine)
                            engine_chooser_dialog.set_filename(engine["command"])
                            msg_dia = Gtk.MessageDialog(mainwindow(),
                                                        type=Gtk.MessageType.ERROR,
                                                        buttons=Gtk.ButtonsType.OK)
                            msg_dia.set_markup(
                                _("<big><b>Unable to add %s</b></big>" %
                                  new_engine))
                            msg_dia.format_secondary_text(_("There is something wrong with this executable"))
                            msg_dia.run()
                            msg_dia.hide()
                            engine_chooser_dialog.hide()
                            self.add = False
                            engine_chooser_dialog.hide()
                            return

                        self.widgets["engine_command_entry"].set_text(new_engine)
                        self.widgets["engine_protocol_combo"].set_active(0 if uci else 1)
                        self.widgets["engine_args_entry"].set_text("")

                        # active = self.widgets["engine_protocol_combo"].get_active()
                        protocol = "uci" if uci else "xboard"

                        # print(binname, new_engine, protocol, vm_name, vm_args)
                        discoverer.addEngine(binname, new_engine, protocol, vm_name, vm_args)
                        self.cur_engine = binname
                        self.add = False
                        discoverer.discover()
                    except Exception:
                        msg_dia = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                                    buttons=Gtk.ButtonsType.OK)
                        msg_dia.set_markup(_("<big><b>Unable to add %s</b></big>" % new_engine))
                        msg_dia.format_secondary_text(_("There is something wrong with this executable"))
                        msg_dia.run()
                        msg_dia.hide()
                        self.add = False
                        engine_chooser_dialog.hide()
                        return
                else:
                    # restore the original
                    engine = discoverer.getEngineByName(self.cur_engine)
                    engine_chooser_dialog.set_filename(engine["command"])

            engine_chooser_dialog.hide()

        self.widgets["add_engine_button"].connect("clicked", add)

        ################################################################
        # add in mass button
        ################################################################

        def addInMass(button):
            # Ask the user to select a folder
            folder_dlg = Gtk.FileChooserDialog(_("Choose a folder"), None, Gtk.FileChooserAction.SELECT_FOLDER, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
            answer = folder_dlg.run()
            path = folder_dlg.get_filename()
            folder_dlg.destroy()

            # Search for the engines
            if answer != Gtk.ResponseType.OK:
                return False
            possibleFiles = listEnginesFromPath(path)

            # Remove the existing engines from the list
            def isNewEngine(path):
                sfn = os.path.basename(path)
                for engine in discoverer.getEngines():
                    if sfn in engine.get("command"):  # The short name must be unique
                        return False
                return True
            possibleFiles = [fn for fn in possibleFiles if isNewEngine(fn)]
            if len(possibleFiles) == 0:
                return False

            # Prepare the result in a dialog
            mass_dialog = self.widgets["engine_list_dialog"]
            self.widgets["mass_path_label"].set_text(path)
            mass_list = self.widgets["mass_list_treeview"]
            if len(mass_list.get_columns()) == 0:  # Not initialized yet
                mass_store = Gtk.ListStore(bool, str)
                mass_list.set_model(mass_store)

                def checkbox_renderer_cb(cell, path, model):
                    model[path][0] = not model[path][0]
                    return
                checkbox_renderer = Gtk.CellRendererToggle()
                checkbox_renderer.set_property("activatable", True)
                checkbox_renderer.connect("toggled", checkbox_renderer_cb, mass_store)
                mass_list.append_column(Gtk.TreeViewColumn(_("Import"), checkbox_renderer, active=0))
                mass_list.append_column(Gtk.TreeViewColumn(_("File name"), Gtk.CellRendererText(), text=1))
            else:
                mass_store = mass_list.get_model()

            mass_store.clear()
            for fn in possibleFiles:
                mass_store.append([False, fn[len(path):]])

            # Show the dialog
            answer = mass_dialog.run()
            mass_dialog.hide()
            if answer != Gtk.ResponseType.OK.real:
                return False

            # Add the new engines
            self.add = True
            found = False
            for entry in mass_store:
                if entry[0]:
                    newengine = discoverer.getReferencedEngine(path + entry[1])
                    if newengine is not None:
                        discoverer.addEngineFromReference(newengine)
                        found = True
            self.add = False
            if found:
                discoverer.discover()
            return True

        self.widgets["mass_engine_button"].connect("clicked", addInMass)

        ################################################################
        def clearView():
            self.selection = True
            self.cur_engine = None
            self.widgets["vm_command_entry"].set_text("")
            self.widgets["vm_args_entry"].set_text("")
            self.widgets["engine_command_entry"].set_text("")
            self.widgets["engine_args_entry"].set_text("")
            self.widgets["engine_protocol_combo"].set_active(0)
            self.widgets["engine_country_combo"].set_active(0)
            self.widgets["engine_comment_entry"].set_text("")
            self.widgets["engine_level_scale"].set_value(ENGINE_DEFAULT_LEVEL)
            self.options_store.clear()
            self.selection = False

        ################################################################
        # vm args
        ################################################################
        def vm_args_changed(widget):
            if self.cur_engine is not None and not self.selection:
                new_args = self.widgets["vm_args_entry"].get_text().strip()
                engine = discoverer.getEngineByName(self.cur_engine)
                old_args = engine.get("vm_args")
                if new_args != old_args:
                    engine["vm_args"] = new_args.split()

        self.widgets["vm_args_entry"].connect("changed", vm_args_changed)

        ################################################################
        # engine args
        ################################################################
        def args_changed(widget):
            if self.cur_engine is not None and not self.selection:
                new_args = self.widgets["engine_args_entry"].get_text().strip()
                engine = discoverer.getEngineByName(self.cur_engine)
                old_args = engine.get("args")
                if new_args != old_args:
                    engine["args"] = new_args.split()

        self.widgets["engine_args_entry"].connect("changed", args_changed)

        ################################################################
        # engine working directory
        ################################################################
        dir_chooser_dialog = Gtk.FileChooserDialog(
            _("Select working directory"), mainwindow(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.OK))
        dir_chooser_button = Gtk.FileChooserButton.new_with_dialog(
            dir_chooser_dialog)

        self.widgets["dirChooserDock"].add(dir_chooser_button)
        dir_chooser_button.show()

        def select_dir(button):
            new_directory = dir_chooser_dialog.get_filename()
            engine = discoverer.getEngineByName(self.cur_engine)
            old_directory = engine.get("workingDirectory")
            if new_directory != old_directory and new_directory != self.default_workdir:
                engine["workingDirectory"] = new_directory

        dir_chooser_button.connect("current-folder-changed", select_dir)

        ################################################################
        # engine protocol
        ################################################################
        def protocol_changed(widget):
            if self.cur_engine is not None and not self.add and not self.selection:
                active = self.widgets["engine_protocol_combo"].get_active()
                new_protocol = "uci" if active == 0 else "xboard"
                engine = discoverer.getEngineByName(self.cur_engine)
                old_protocol = engine["protocol"]
                if new_protocol != old_protocol:
                    command = engine.get("command")
                    engine_command = []
                    vm_command = engine.get("vm_command")
                    if vm_command is not None:
                        engine_command.append(vm_command)
                        vm_args = engine.get("vm_args")
                        if vm_args is not None:
                            engine_command.append(", ".join(vm_args))
                    engine_command.append(command)

                    # is the new protocol supported by the engine?
                    if new_protocol == "uci":
                        check_ok = is_uci(engine_command)
                    else:
                        check_ok = is_cecp(engine_command)

                    if check_ok:
                        # discover engine options for new protocol
                        engine["protocol"] = new_protocol
                        engine["recheck"] = True
                        discoverer.discover()
                    else:
                        # restore the original protocol
                        widgets["engine_protocol_combo"].set_active(
                            0 if old_protocol == "uci" else 1)

        self.widgets["engine_protocol_combo"].connect("changed",
                                                      protocol_changed)

        ################################################################
        # engine country
        ################################################################
        def country_changed(widget):
            if self.cur_engine is not None and not self.selection:
                engine = discoverer.getEngineByName(self.cur_engine)
                old_country = discoverer.getCountry(engine)
                new_country = ISO3166_LIST[widget.get_active()].iso2
                if old_country != new_country:
                    engine["country"] = new_country

                    # Refresh the flag in the tree view
                    path = addDataPrefix("flags/%s.png" % new_country)
                    if not os.path.isfile(path):
                        path = addDataPrefix("flags/unknown.png")
                    item = self.tv.get_selection().get_selected()
                    if item is not None:
                        model, ts_iter = item
                        model[ts_iter][0] = get_pixbuf(path)

                        # Notify playerCombos in NewGameTasker
                        discoverer.emit("all_engines_discovered")

        self.widgets["engine_country_combo"].connect("changed", country_changed)

        def country_keypressed(widget, event):
            idx = 0
            for iso in ISO3166_LIST:
                if (idx != 0) and ((ord(iso.country[0].lower()) == event.keyval) or
                                   (ord(iso.country[0].upper()) == event.keyval)):
                    widget.set_active(idx)
                    break
                idx += 1

        self.widgets["engine_country_combo"].connect("key-press-event", country_keypressed)

        ################################################################
        # comment changed
        ################################################################
        def comment_changed(widget):
            if self.cur_engine is not None and not self.selection:
                new_comment = self.widgets["engine_comment_entry"].get_text().strip()
                engine = discoverer.getEngineByName(self.cur_engine)
                old_comment = engine.get("comment")
                if new_comment != old_comment:
                    engine["comment"] = new_comment

        self.widgets["engine_comment_entry"].connect("changed", comment_changed)

        ################################################################
        # level changed
        ################################################################
        def level_changed(widget):
            if self.cur_engine is not None and not self.selection:
                new_level = widget.get_value()
                engine = discoverer.getEngineByName(self.cur_engine)
                old_level = engine.get("level")
                if new_level != old_level:
                    engine["level"] = int(new_level)

        self.widgets["engine_level_scale"].connect("value-changed", level_changed)

        ################################################################
        # engine tree
        ################################################################
        self.selection = False

        def selection_changed(treeselection):
            store, tv_iter = self.tv.get_selection().get_selected()
            if tv_iter:
                self.selection = True
                path = store.get_path(tv_iter)
                indices = path.get_indices()
                row = indices[0]
                name = store[row][1]
                self.cur_engine = name
                engine = discoverer.getEngineByName(name)
                if "PyChess.py" in engine["command"]:
                    self.widgets['remove_engine_button'].set_sensitive(False)
                else:
                    self.widgets['remove_engine_button'].set_sensitive(True)
                self.widgets["engine_command_entry"].set_text(engine["command"])
                engine_chooser_dialog.set_filename(engine["command"])
                args = [] if engine.get("args") is None else engine.get("args")
                self.widgets["engine_args_entry"].set_text(' '.join(args))

                vm = engine.get("vm_command")
                self.widgets["vm_command_entry"].set_text(vm if vm is not None else "")
                args = [] if engine.get("vm_args") is None else engine.get("vm_args")
                self.widgets["vm_args_entry"].set_text(' '.join(args))

                directory = engine.get("workingDirectory")
                dir_choice = directory if directory is not None else self.default_workdir
                dir_chooser_dialog.set_current_folder(dir_choice)
                self.widgets["engine_protocol_combo"].set_active(0 if engine["protocol"] == "uci" else 1)

                self.widgets["engine_country_combo"].set_active(0)
                country = discoverer.getCountry(engine)
                idx = 0
                for iso in ISO3166_LIST:
                    if iso.iso2 == country:
                        self.widgets["engine_country_combo"].set_active(idx)
                        break
                    idx += 1

                comment = engine.get("comment")
                self.widgets["engine_comment_entry"].set_text(comment if comment is not None else "")

                level = engine.get("level")
                try:
                    level = int(level)
                except Exception:
                    level = ENGINE_DEFAULT_LEVEL
                self.widgets["engine_level_scale"].set_value(level)

                self.update_options()
                self.selection = False

        tree_selection = self.tv.get_selection()
        tree_selection.connect('changed', selection_changed)
        tree_selection.select_path((0, ))
        selection_changed(tree_selection)

        ################################################################
        # restore the default options of the engine
        ################################################################

        def engine_default_options(button):
            if self.cur_engine is not None and not self.selection:
                engine = discoverer.getEngineByName(self.cur_engine)
                options = engine.get("options")
                if options:
                    dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO)
                    dialog.set_markup(_("Do you really want to restore the default options of the engine ?"))
                    response = dialog.run()
                    dialog.destroy()
                    if response == Gtk.ResponseType.YES:
                        for option in options:
                            if "default" in option:
                                option["value"] = option["default"]
                        self.update_options()

        self.widgets["engine_default_options_button"].connect("clicked", engine_default_options)


class KeyValueCellRenderer(Gtk.CellRenderer):
    """ Custom renderer providing different renderers in different rows.
        The model parameter is a Gtk.ListStore(str, GObject.TYPE_PYOBJECT)
        containing key data pairs. Each data is a dictionary with
        name, type, default, value, min, max (for spin options), choices (list of combo options)
        The 'type' can be 'check', 'spin', 'text', 'combo', 'button'.
        Examples:
            ('Nullmove', {'name': 'Nullmove', 'default': false, 'type': 'check', 'value': True})
            ('Selectivity', {'name': 'Selectivity', 'default': 1, 'type': 'spin', \
                'min': 0, 'max': 4, 'value': 2})
            ('Style', {'name': 'Style', 'default': 'Solid', 'type': 'combo', \
                'choices': ['Solid', 'Normal','Risky'], 'value': 'Normal'})
            ('NalimovPath', {'name': 'NalimovPath', 'default': '',  \
                'type': 'text', 'value': '/home/egtb'})
            ('Clear Hash', {'name': 'Clear Hash', 'type': 'button'})
    """
    __gproperties__ = {"data": (GObject.TYPE_PYOBJECT, "Data", "Data",
                                GObject.ParamFlags.READABLE | GObject.ParamFlags.WRITABLE)}

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

    def update_modified_mark(self, ref):
        ref[0] = "*" if ref[2].get("value") != ref[2].get("default") else ""

    def text_edited_cb(self, cell, path, new_text, model):
        model[path][2]["value"] = new_text
        self.update_modified_mark(model[path])
        return

    def toggled_cb(self, cell, path, model):
        model[path][2]["value"] = not model[path][2]["value"]
        self.update_modified_mark(model[path])
        return

    def spin_edited_cb(self, cell, path, new_text, model):
        try:
            model[path][2]["value"] = int(new_text)
            self.update_modified_mark(model[path])
        except Exception:
            pass
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
            adjustment = Gtk.Adjustment(value=int(value["value"]),
                                        lower=value["min"],
                                        upper=value["max"],
                                        step_increment=1)
            self.spin_renderer.set_property("adjustment", adjustment)
            self.spin_renderer.set_property("text", str(value["value"]))
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

    def do_get_size(self, widget, cell_area=None):
        return self.renderer.get_size(widget, cell_area=cell_area)

    def do_render(self, ctx, widget, background_area, cell_area, flags):
        self.renderer.render(ctx, widget, background_area, cell_area, flags)

    def do_activate(self, event, widget, path, background_area, cell_area, flags):
        return self.renderer.activate(event, widget, path, background_area, cell_area, flags)

    def do_start_editing(self, event, widget, path, background_area, cell_area, flags):
        return self.renderer.start_editing(event, widget, path, background_area, cell_area, flags)


GObject.type_register(KeyValueCellRenderer)
