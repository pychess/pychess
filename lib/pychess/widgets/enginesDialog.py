import os
import sys
import shutil
from collections import namedtuple

from gi.repository import Gtk, Gdk, GLib, GObject
from gi.repository.GdkPixbuf import Pixbuf

from pychess.System import uistuff
from pychess.System.prefix import getEngineDataPrefix, addDataPrefix
from pychess.Utils.IconLoader import get_pixbuf
from pychess.Players.engineNest import discoverer, is_uci, is_cecp
from pychess.Utils.isoCountries import ISO3166_LIST
from pychess.widgets import newGameDialog
from pychess.widgets import mainwindow

firstRun = True

VM = namedtuple('VM', 'name, ext, args')
VM_LIST = [
    VM("node", ".js", None),
    VM("java", ".jar", "-jar"),
    VM("python", ".py", "-u")]


def run(widgets):
    global firstRun
    if firstRun:
        # Bubble sort for the translated countries
        for i in range(len(ISO3166_LIST) - 1, 1, - 1):
            for j in range(1, i - 1):
                if ISO3166_LIST[i].country < ISO3166_LIST[j].country:
                    tmp = ISO3166_LIST[i]
                    ISO3166_LIST[i] = ISO3166_LIST[j]
                    ISO3166_LIST[j] = tmp
        # Display of the countries
        items = []
        for iso in ISO3166_LIST:
            path = addDataPrefix("flags/%s.png" % iso.iso2)
            if not(iso.iso2 and os.path.isfile(path)):
                path = addDataPrefix("flags/unknown.png")
            items.append((get_pixbuf(path), iso.country))
        uistuff.createCombo(widgets["engine_country_combo"], name="engine_country_combo")
        data = [(item[0], item[1]) for item in items]
        uistuff.updateCombo(widgets["engine_country_combo"], data)

        EnginesDialog(widgets)

        def delete_event(widget, *args):
            widgets["manage_engines_dialog"].hide()
            return True

        widgets["manage_engines_dialog"].connect("delete-event", delete_event)
        widgets["engines_close_button"].connect("clicked", delete_event)
        widgets["manage_engines_dialog"].connect(
            "key-press-event",
            lambda w, e: delete_event(w) if e.keyval == Gdk.KEY_Escape else None)

        firstRun = False

    widgets["manage_engines_dialog"].show()


class EnginesDialog():
    def __init__(self, widgets):
        self.widgets = widgets
        self.dialog = self.widgets["manage_engines_dialog"]
        self.cur_engine = None
        self.default_workdir = getEngineDataPrefix()

        uistuff.keepWindowSize("engineswindow",
                               self.dialog,
                               defaultSize=(1, 500))

        # Put engines into tree store
        allstore = Gtk.ListStore(Pixbuf, str)

        self.tv = self.widgets["engines_treeview"]
        self.tv.set_model(allstore)
        self.tv.append_column(Gtk.TreeViewColumn("Flag",
                                                 Gtk.CellRendererPixbuf(),
                                                 pixbuf=0))
        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("editable", False)
        self.tv.append_column(Gtk.TreeViewColumn("Name",
                                                 name_renderer,
                                                 text=1))

        def name_edited(renderer, path, new_name):
            if self.cur_engine is not None:
                old_name = self.cur_engine
                if new_name and new_name != old_name:
                    names = [engine["name"]
                             for engine in discoverer.getEngines()]
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
        protocol_combo.set_name("engine_protocol_combo")
        cell = Gtk.CellRendererText()
        protocol_combo.pack_start(cell, True)
        protocol_combo.add_attribute(cell, "text", 0)

        # Add columns and cell renderers to options treeview
        self.options_store = Gtk.ListStore(str, GObject.TYPE_PYOBJECT)
        optv = self.widgets["options_treeview"]
        optv.set_model(self.options_store)
        optv.append_column(Gtk.TreeViewColumn("Option",
                                              Gtk.CellRendererText(),
                                              text=0))
        optv.append_column(Gtk.TreeViewColumn("Data",
                                              KeyValueCellRenderer(
                                                  self.options_store),
                                              data=1))

        def update_options(*args):
            if self.cur_engine is not None:
                engines = discoverer.getEngines()
                names = [engine["name"] for engine in engines]
                # After deleting an engine we will select first
                if self.cur_engine not in names:
                    self.cur_engine = engines[0]["name"]
                engine = discoverer.getEngineByName(self.cur_engine)
                options = engine.get("options")
                self.options_store.clear()
                if options:
                    options.sort(key=lambda obj: obj['name'].lower() if 'name' in obj else '')
                    for option in options:
                        key = option["name"]
                        val = option
                        if option["type"] != "button":
                            val["default"] = option.get("default")
                            val["value"] = option.get("value", val["default"])
                        self.options_store.append([key, val])

        def update_store(*args):
            newGameDialog.createPlayerUIGlobals(discoverer)
            engine_names = [row[1] for row in allstore]
            new_items = []
            # don't add the very first (Human) player to engine store
            for item in newGameDialog.allEngineItems:
                if item[1] not in engine_names:
                    new_items.append(item)
            ts_iter = None
            for item in new_items:
                ts_iter = allstore.append(item)
            if ts_iter is not None:
                text_select = self.tv.get_selection()
                text_select.select_iter(ts_iter)
            update_options()

        update_store()

        def do_update_store(*args):
            GLib.idle_add(update_store)

        discoverer.connect_after("engine_discovered", do_update_store)

        ################################################################
        # remove button
        ################################################################
        def remove(button):
            if self.cur_engine is not None:
                self.widgets['remove_engine_button'].set_sensitive(False)
                # engine = discoverer.getEngineByName(self.cur_engine)
                discoverer.removeEngine(self.cur_engine)
                discoverer.save()

                selection = self.tv.get_selection()
                result = selection.get_selected()
                if result is not None:
                    model, ts_iter = result
                    model.remove(ts_iter)

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
                vm_name = None
                vm_args = None
                vmpath = ""
                if new_engine.lower().endswith(".exe") and sys.platform != "win32":
                    vm_name = "wine"
                    vmpath = shutil.which(vm_name, mode=os.R_OK | os.X_OK)
                    if vmpath is None:
                        msg_dia = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                                    buttons=Gtk.ButtonsType.OK)
                        msg_dia.set_markup(_("<big><b>Unable to add %s</b></big>" %
                                             new_engine))
                        msg_dia.format_secondary_text(_("wine not installed"))
                        msg_dia.run()
                        msg_dia.hide()
                        new_engine = ""

                for vm in VM_LIST:
                    ext = os.path.splitext(new_engine)[1]
                    if ext == vm.ext:
                        vm_name = vm.name
                        vm_args = vm.args
                        vmpath = shutil.which(vm_name, mode=os.R_OK | os.X_OK)
                        if vmpath is None:
                            msg_dia = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                                        buttons=Gtk.ButtonsType.OK)
                            msg_dia.set_markup(_("<big><b>Unable to add %s</b></big>" %
                                                 new_engine))
                            msg_dia.format_secondary_text(vm_name + _(" is not installed"))
                            msg_dia.run()
                            msg_dia.hide()
                            new_engine = ""
                        break

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
                            engine_command.append(vm_args)
                        engine_command.append(new_engine)
                        # Some engines support CECP and UCI, but main variant engines are CECP,
                        # so we better to start with CECP this case
                        variant_engines = ("fmax", "sjaakii", "sjeng")
                        if any((True
                                for eng in variant_engines
                                if eng in new_engine.lower())):
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
                            engine = discoverer.getEngineByName(
                                self.cur_engine)
                            engine_chooser_dialog.set_filename(engine[
                                "command"])
                            msg_dia = Gtk.MessageDialog(mainwindow(),
                                                        type=Gtk.MessageType.ERROR,
                                                        buttons=Gtk.ButtonsType.OK)
                            msg_dia.set_markup(
                                _("<big><b>Unable to add %s</b></big>" %
                                  new_engine))
                            msg_dia.format_secondary_text(_(
                                "There is something wrong with this executable"))
                            msg_dia.run()
                            msg_dia.hide()
                            engine_chooser_dialog.hide()
                            self.add = False
                            engine_chooser_dialog.hide()
                            return

                        binname = os.path.split(new_engine)[1]
                        for eng in discoverer.getEngines():
                            if eng["name"] == binname:
                                binname = eng["name"] + "(1)"
                                break

                        self.widgets["engine_command_entry"].set_text(new_engine)
                        self.widgets["engine_protocol_combo"].set_active(0 if uci else 1)
                        self.widgets["engine_args_entry"].set_text("")

                        # active = self.widgets["engine_protocol_combo"].get_active()
                        protocol = "uci" if uci else "xboard"

                        if vm_args is not None:
                            vm_args = vm_args.split(",")
                        # print(binname, new_engine, protocol, vm_name, vm_args)
                        discoverer.addEngine(binname, new_engine, protocol, vm_name, vm_args, "unknown")
                        self.cur_engine = binname
                        self.add = False
                        discoverer.discover()
                    except Exception:
                        msg_dia = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                                    buttons=Gtk.ButtonsType.OK)
                        msg_dia.set_markup(_("<big><b>Unable to add %s</b></big>" %
                                             new_engine))
                        msg_dia.format_secondary_text(_(
                            "There is something wrong with this executable"))
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
        # vm args
        ################################################################
        def vm_args_changed(widget):
            if self.cur_engine is not None:
                new_args = self.widgets["vm_args_entry"].get_text().strip()
                engine = discoverer.getEngineByName(self.cur_engine)
                old_args = engine.get("vm_args")
                if new_args != old_args:
                    engine["vm_args"] = new_args.split()
                    discoverer.save()

        self.widgets["vm_args_entry"].connect("changed", vm_args_changed)

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
                discoverer.save()

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
                    discoverer.save()

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
                self.widgets['copy_engine_button'].set_sensitive(True)
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

                update_options()
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
                        discoverer.save()
                        update_options()

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
                                GObject.PARAM_READWRITE)}

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
            adjustment = Gtk.Adjustment(value=int(value["value"]),
                                        lower=value["min"],
                                        upper=value["max"],
                                        step_incr=1)
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

    def do_activate(self, event, widget, path, background_area, cell_area,
                    flags):
        return self.renderer.activate(event, widget, path, background_area,
                                      cell_area, flags)

    def do_start_editing(self, event, widget, path, background_area, cell_area,
                         flags):
        return self.renderer.start_editing(event, widget, path,
                                           background_area, cell_area, flags)


GObject.type_register(KeyValueCellRenderer)
