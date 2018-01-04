import os

from gi.repository import Gtk, GObject

from pychess.perspectives import Perspective, perspective_manager
from pychess.System.prefix import addUserConfigPrefix
from pychess.System.Log import log
from pychess.widgets import new_notebook
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import WEST, SOUTH, CENTER


class Learn(GObject.GObject, Perspective):
    def __init__(self):
        GObject.GObject.__init__(self)
        Perspective.__init__(self, "learn", _("Learn"))
        self.always_on = True

        self.dockLocation = addUserConfigPrefix("pydock-learn.xml")
        self.first_run = True

    def create_toolbuttons(self):
        pass

    def init_layout(self):
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
