import os
import sys
import importlib
import traceback
import zipfile
import zipimport
from io import StringIO

from gi.repository import Gtk

from pychess import MSYS2
from pychess.System.Log import log
from pychess.widgets import createImage, dock_panel_tab, mainwindow, gtk_close
from pychess.widgets.pydock import SOUTH


def panel_name(module_name):
    return module_name.split(".")[-1]


class Perspective:
    def __init__(self, name, label):
        self.name = name
        self.label = label
        self.default = False
        self.widget = Gtk.Alignment()
        self.widget.show()
        self.toolbuttons = []
        self.menuitems = []
        self.docks = {}
        self.main_notebook = None

        if getattr(sys, 'frozen', False) and not MSYS2:
            zip_path = os.path.join(os.path.dirname(sys.executable), "library.zip")
            importer = zipimport.zipimporter(zip_path + "/pychess/perspectives/%s" % name)
            postfix = "Panel.pyc"
            with zipfile.ZipFile(zip_path, 'r') as myzip:
                names = [f[:-4].split("/")[-1] for f in myzip.namelist() if f.endswith(postfix) and "/%s/" % name in f]
            self.sidePanels = [importer.load_module(name) for name in names]
        else:
            path = "%s/%s" % (os.path.dirname(__file__), name)
            ext = ".pyc" if getattr(sys, 'frozen', False) and MSYS2 else ".py"
            postfix = "Panel%s" % ext
            files = [f[:-len(ext)] for f in os.listdir(path) if f.endswith(postfix)]
            self.sidePanels = [importlib.import_module("pychess.perspectives.%s.%s" % (name, f)) for f in files]

        for panel in self.sidePanels:
            close_button = Gtk.Button()
            close_button.set_property("can-focus", False)
            close_button.add(createImage(gtk_close))
            close_button.set_relief(Gtk.ReliefStyle.NONE)
            close_button.set_size_request(20, 18)
            close_button.connect("clicked", self.on_clicked, panel)

            menu_item = Gtk.CheckMenuItem(label=panel.__title__)
            menu_item.name = panel_name(panel.__name__)
            # if menu_item.name != "LecturesPanel":
            #    menu_item.set_active(True)
            menu_item.connect("toggled", self.on_toggled, panel)
            self.menuitems.append(menu_item)
            panel.menu_item = menu_item

            box = dock_panel_tab(panel.__title__, panel.__desc__, panel.__icon__, close_button)
            self.docks[panel_name(panel.__name__)] = [box, None, menu_item]

    def on_clicked(self, button, panel):
        """ Toggle show/hide side panel menu item in View menu """
        panel.menu_item.set_active(not panel.menu_item.get_active())

    def on_toggled(self, menu_item, panel):
        """ Show/Hide side panel """
        try:
            leaf = self.notebooks[panel_name(panel.__name__)].get_parent().get_parent()
        except AttributeError:
            # new sidepanel appeared (not in saved layout .xml file)
            name = panel_name(panel.__name__)
            leaf = self.main_notebook.get_parent().get_parent()
            leaf.dock(self.docks[name][1], SOUTH, self.docks[name][0], name)

        parent = leaf.get_parent()
        names = [p[2] for p in leaf.panels]

        active = menu_item.get_active()
        name = panel_name(panel.__name__)
        shown = sum([1 for panel in self.sidePanels if panel_name(panel.__name__) in names and self.notebooks[panel_name(panel.__name__)].is_visible()])

        if active:
            self.notebooks[name].show()
            leaf.setCurrentPanel(name)
            if shown == 0 and hasattr(leaf, "position"):
                # If this is the first one, adjust Gtk.Paned divider handle
                if leaf.position != 0:
                    parent.set_position(leaf.position)
                else:
                    parent.set_position(parent.props.max_position / 2)
        else:
            self.notebooks[name].hide()
            if shown == 1:
                # If this is the last one, adjust Gtk.Paned divider handle
                pos = parent.get_position()
                leaf.position = pos if pos != parent.props.min_position and pos != parent.props.max_position else 0
                if leaf == parent.get_child1():
                    parent.set_position(parent.props.min_position)
                else:
                    parent.set_position(parent.props.max_position)

    def activate_panel(self, name):
        for panel in self.sidePanels:
            if panel_name(panel.__name__).startswith(name):
                if panel.menu_item.get_active():
                    # if menu item is already active set_active() doesn't triggers on_toggled()
                    self.on_toggled(panel.menu_item, panel)
                else:
                    panel.menu_item.set_active(True)
                break

    def load_from_xml(self):
        if os.path.isfile(self.dockLocation):
            try:
                self.dock.loadFromXML(self.dockLocation, self.docks)
            except Exception as e:
                # We don't send error message when error caused by no more existing SwitcherPanel
                if e.args[0] != "SwitcherPanel" and "unittest" not in sys.modules.keys():
                    stringio = StringIO()
                    traceback.print_exc(file=stringio)
                    error = stringio.getvalue()
                    log.error("Dock loading error: %s\n%s" % (e, error))
                    msg_dia = Gtk.MessageDialog(mainwindow(),
                                                type=Gtk.MessageType.ERROR,
                                                buttons=Gtk.ButtonsType.CLOSE)
                    msg_dia.set_markup(_(
                        "<b><big>PyChess was unable to load your panel settings</big></b>"))
                    msg_dia.format_secondary_text(_(
                        "Your panel settings have been reset. If this problem repeats, \
                        you should report it to the developers"))
                    msg_dia.run()
                    msg_dia.hide()
                os.remove(self.dockLocation)
                for title, panel, menu_item in self.docks.values():
                    title.unparent()
                    panel.unparent()

    @property
    def sensitive(self):
        perspective, button, index = perspective_manager.perspectives[self.name]
        return button.get_sensitive()

    def create_toolbuttons(self):
        pass

    def close(self):
        pass


class PerspectiveManager:
    def __init__(self):
        self.perspectives = {}
        self.current_perspective = None

    def set_widgets(self, widgets):
        self.widgets = widgets
        self.toolbar = self.widgets["toolbar1"]
        self.viewmenu = self.widgets["vis1_menu"]

    def on_persp_toggled(self, button):
        active = button.get_active()
        if active:
            for item in self.current_perspective.menuitems:
                item.hide()
            for toolbutton in self.current_perspective.toolbuttons:
                toolbutton.hide()

            name = button.get_name()
            perspective, button, index = self.perspectives[name]
            self.widgets["perspectives_notebook"].set_current_page(index)
            self.current_perspective = perspective

            for item in perspective.menuitems:
                item.show()
            for toolbutton in perspective.toolbuttons:
                toolbutton.show()

    def add_perspective(self, perspective):
        box = self.widgets["persp_buttons"]
        children = box.get_children()
        widget = None if len(children) == 0 else children[0]
        button = Gtk.RadioButton.new_with_label_from_widget(widget, perspective.label)
        if perspective.default:
            self.current_perspective = perspective
        else:
            button.set_sensitive(False)
        button.set_name(perspective.name)
        button.set_mode(False)
        box.pack_start(button, True, True, 0)
        button.connect("toggled", self.on_persp_toggled)

        index = self.widgets["perspectives_notebook"].append_page(perspective.widget, None)
        self.perspectives[perspective.name] = (perspective, button, index)

    def activate_perspective(self, name):
        perspective, button, index = self.perspectives[name]
        button.set_sensitive(True)
        button.set_active(True)

    def disable_perspective(self, name):
        if not self.get_perspective(name).sensitive:
            return

        perspective, button, index = self.perspectives[name]
        button.set_sensitive(False)
        for button in perspective.toolbuttons:
            button.hide()

        if self.get_perspective("fics").sensitive:
            self.activate_perspective("fics")
        elif self.get_perspective("database").sensitive:
            self.activate_perspective("database")
        elif self.get_perspective("games").sensitive:
            self.activate_perspective("games")
        elif self.get_perspective("learn").sensitive:
            self.activate_perspective("learn")
        else:
            self.activate_perspective("welcome")

    def get_perspective(self, name):
        if name in self.perspectives:
            perspective, button, index = self.perspectives[name]
        else:
            perspective = None
        return perspective

    def set_perspective_widget(self, name, widget):
        perspective, button, index = self.perspectives[name]
        container = self.widgets["perspectives_notebook"].get_nth_page(index)
        for child in container.get_children():
            container.remove(child)
        container.add(widget)

    def set_perspective_toolbuttons(self, name, buttons):
        perspective, button, index = self.perspectives[name]
        for button in perspective.toolbuttons:
            if button in self.toolbar:
                self.toolbar.remove(button)
        perspective.toolbuttons = []

        separator = Gtk.SeparatorToolItem.new()
        separator.set_draw(True)
        perspective.toolbuttons.append(separator)
        for button in buttons:
            perspective.toolbuttons.append(button)
            self.toolbar.add(button)
            button.show()

    def set_perspective_menuitems(self, name, menuitems, default=True):
        perspective, button, index = self.perspectives[name]
        for item in perspective.menuitems:
            if item in self.viewmenu:
                self.viewmenu.remove(item)
        perspective.menuitems = []

        item = Gtk.SeparatorMenuItem()
        perspective.menuitems.append(item)
        self.viewmenu.append(item)
        item.show()
        for item in menuitems:
            perspective.menuitems.append(item)
            self.viewmenu.append(item)
            if default:
                item.set_active(True)
            item.show()


perspective_manager = PerspectiveManager()
