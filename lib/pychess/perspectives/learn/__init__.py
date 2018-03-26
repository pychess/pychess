import os
import json
from abc import ABCMeta
from collections import UserDict

from gi.repository import Gtk, GObject
from gi.types import GObjectMeta

from pychess.perspectives import Perspective, perspective_manager
from pychess.System.prefix import addUserConfigPrefix
from pychess.System.Log import log
from pychess.widgets import new_notebook
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import WEST, SOUTH, CENTER
from pychess.System.prefix import addUserDataPrefix


class Learn(GObject.GObject, Perspective):
    def __init__(self):
        GObject.GObject.__init__(self)
        Perspective.__init__(self, "learn", _("Learn"))
        self.always_on = True

        self.dockLocation = addUserConfigPrefix("pydock-learn.xml")
        self.first_run = True

    def create_toolbuttons(self):
        def on_exit_clicked(button):
            perspective_manager.disable_perspective("learn")

        self.exit_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_QUIT)
        self.exit_button.set_tooltip_text(_("Quit Learning"))
        self.exit_button.set_label("exit")
        self.exit_button.connect("clicked", on_exit_clicked)

    def init_layout(self):
        perspective_manager.set_perspective_toolbuttons("learn", (self.exit_button, ))

        perspective_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        perspective_manager.set_perspective_widget("learn", perspective_widget)
        perspective_manager.set_perspective_menuitems("learn", self.menuitems)

        self.notebooks = {"home": new_notebook()}
        self.main_notebook = self.notebooks["home"]
        for panel in self.sidePanels:
            self.notebooks[panel.__name__] = new_notebook(panel.__name__)

        self.dock = PyDockTop("learn", self)
        align = Gtk.Alignment()
        align.show()
        align.add(self.dock)
        self.dock.show()
        perspective_widget.pack_start(align, True, True, 0)

        self.notebooks = {"learnhome": new_notebook()}
        self.main_notebook = self.notebooks["learnhome"]
        for panel in self.sidePanels:
            self.notebooks[panel.__name__] = new_notebook(panel.__name__)

        self.docks["learnhome"] = (Gtk.Label(label="learnhome"), self.notebooks["learnhome"], None)
        for panel in self.sidePanels:
            self.docks[panel.__name__][1] = self.notebooks[panel.__name__]

        self.load_from_xml()

        # Default layout of side panels
        if not os.path.isfile(self.dockLocation):
            leaf = self.dock.dock(self.docks["learnhome"][1], CENTER, self.docks["learnhome"][0], "learnhome")
            leaf.setDockable(False)

            leaf.dock(self.docks["PuzzlesPanel"][1], WEST, self.docks["PuzzlesPanel"][0], "PuzzlesPanel")
            leaf = leaf.dock(self.docks["LecturesPanel"][1], SOUTH, self.docks["LecturesPanel"][0], "LecturesPanel")
            leaf = leaf.dock(self.docks["LessonsPanel"][1], SOUTH, self.docks["LessonsPanel"][0], "LessonsPanel")
            leaf.dock(self.docks["EndgamesPanel"][1], SOUTH, self.docks["EndgamesPanel"][0], "EndgamesPanel")

        def unrealize(dock):
            dock.saveToXML(self.dockLocation)
            dock._del()

        self.dock.connect("unrealize", unrealize)

        self.dock.show_all()
        perspective_widget.show_all()

        log.debug("Learn.__init__: finished")

    def activate(self):
        if self.first_run:
            self.init_layout()
            self.first_run = False

        learn_home = Gtk.Box()
        learn_home.add(Gtk.Label("Practice! Practice! Practice!"))
        learn_home.show_all()

        if not self.first_run:
            self.notebooks["learnhome"].remove_page(-1)
        self.notebooks["learnhome"].append_page(learn_home)

        self.panels = [panel.Sidepanel().load(self) for panel in self.sidePanels]

        for panel, instance in zip(self.sidePanels, self.panels):
            if not self.first_run:
                self.notebooks[panel.__name__].remove_page(-1)
            self.notebooks[panel.__name__].append_page(instance)
            instance.show()

        perspective_manager.activate_perspective("learn")


class GObjectMutableMapping(GObjectMeta, ABCMeta):
    """ GObject.GObject and UserDict has different metaclasses
        so we have to create this metaclass to avoid
        TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
    """
    pass


class SolvingProgress(GObject.GObject, UserDict, metaclass=GObjectMutableMapping):
    """ Book keeping of puzzle/lesson solving progress
        Each dict key is a .pgn/.olv file name
        Values are list of 0/1 values showing a given file puzzles solved or not
        The dict is automatically synced with corresponding puzzles.json/lessons.json files
    """

    __gsignals__ = {
        "progress_updated": (GObject.SignalFlags.RUN_FIRST, None, (str, object, )),
    }

    def __init__(self, progress_file):
        GObject.GObject.__init__(self)
        UserDict.__init__(self)
        self.progress_file = addUserDataPrefix(progress_file)

    def get(self, key, default):
        if os.path.isfile(self.progress_file):
            with open(self.progress_file, "r") as f:
                self.data = json.load(f)
            if key not in self.data:
                self.data[key] = default
        else:
            self.data[key] = default

        # print("Solved: %s / %s %s" % (self[key].count(1), len(self[key]), key))

        return self.data[key]

    def __setitem__(self, key, value):
        with open(self.progress_file, "w") as f:
            self.data[key] = value
            json.dump(self.data, f)
            self.emit("progress_updated", key, value)


puzzles_solving_progress = SolvingProgress("puzzles.json")
lessons_solving_progress = SolvingProgress("lessons.json")
