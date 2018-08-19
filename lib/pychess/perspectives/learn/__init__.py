import os
import json
from abc import ABCMeta
from collections import UserDict

from gi.repository import Gdk, Gtk, GObject
from gi.types import GObjectMeta

from pychess.perspectives import Perspective, perspective_manager, panel_name
from pychess.System.prefix import addUserConfigPrefix, addDataPrefix
from pychess.System.Log import log
from pychess.widgets import new_notebook, mainwindow
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import WEST, SOUTH, CENTER
from pychess.System.prefix import addUserDataPrefix
from pychess.Savers.olv import OLVFile
from pychess.Savers.pgn import PGNFile
from pychess.System.protoopen import protoopen


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

        self.notebooks = {"home": new_notebook()}
        self.main_notebook = self.notebooks["home"]
        for panel in self.sidePanels:
            self.notebooks[panel_name(panel.__name__)] = new_notebook(panel_name(panel.__name__))

        self.dock = PyDockTop("learn", self)
        align = Gtk.Alignment()
        align.show()
        align.add(self.dock)
        self.dock.show()
        perspective_widget.pack_start(align, True, True, 0)

        self.notebooks = {"learnhome": new_notebook()}
        self.main_notebook = self.notebooks["learnhome"]
        for panel in self.sidePanels:
            self.notebooks[panel_name(panel.__name__)] = new_notebook(panel_name(panel.__name__))

        self.docks["learnhome"] = (Gtk.Label(label="learnhome"), self.notebooks["learnhome"], None)
        for panel in self.sidePanels:
            self.docks[panel_name(panel.__name__)][1] = self.notebooks[panel_name(panel.__name__)]

        self.load_from_xml()

        # Default layout of side panels
        first_time_layout = False
        if not os.path.isfile(self.dockLocation):
            first_time_layout = True
            leaf0 = self.dock.dock(self.docks["learnhome"][1], CENTER, self.docks["learnhome"][0], "learnhome")
            leaf0.setDockable(False)

            leaf = leaf0.dock(self.docks["PuzzlesPanel"][1], WEST, self.docks["PuzzlesPanel"][0], "PuzzlesPanel")
            leaf.dock(self.docks["LessonsPanel"][1], SOUTH, self.docks["LessonsPanel"][0], "LessonsPanel")

            leaf = leaf0.dock(self.docks["LecturesPanel"][1], SOUTH, self.docks["LecturesPanel"][0], "LecturesPanel")
            leaf.dock(self.docks["EndgamesPanel"][1], SOUTH, self.docks["EndgamesPanel"][0], "EndgamesPanel")

        def unrealize(dock):
            dock.saveToXML(self.dockLocation)
            dock._del()

        self.dock.connect("unrealize", unrealize)

        self.dock.show_all()
        perspective_widget.show_all()

        perspective_manager.set_perspective_menuitems("learn", self.menuitems, default=first_time_layout)

        log.debug("Learn.__init__: finished")

    def activate(self):
        if self.first_run:
            self.init_layout()
            self.first_run = False

        learn_home = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        box = Gtk.Box()

        self.tv = Gtk.TreeView()

        color = Gdk.RGBA()
        color.parse("lightblue")

        for i, col in enumerate((_("lichess"), _("wtharvey"), _("yacpdb"), _("lessons"))):
            renderer = Gtk.CellRendererProgress()
            renderer.set_orientation(Gtk.Orientation.VERTICAL)
            renderer.props.height = 100
            renderer.props.inverted = True
            renderer.props.cell_background_rgba = color
            column = Gtk.TreeViewColumn(col, renderer, text=i * 2, value=i * 2 + 1)
            self.tv.append_column(column)

        self.store = Gtk.ListStore(str, int, str, int, str, int, str, int)

        self.update_progress(None, None, None)

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.NONE)

        puzzles_solving_progress.connect("progress_updated", self.update_progress)
        lessons_solving_progress.connect("progress_updated", self.update_progress)

        box.pack_start(self.tv, False, False, 6)

        label = Gtk.Label(xpad=6, xalign=0)
        label.set_markup("<b>%s</b>" % _("Progress"))
        learn_home.pack_start(label, False, False, 6)

        learn_home.pack_start(box, False, False, 0)

        reset = Gtk.Button(_("Reset my progress"))
        learn_home.pack_start(reset, False, False, 6)

        def on_reset_clicked(button):
            dialog = Gtk.MessageDialog(mainwindow(), 0, Gtk.MessageType.QUESTION,
                                       Gtk.ButtonsType.OK_CANCEL,
                                       _("You will lose all your progress data!"))
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                for filename, progress in lessons_solving_progress.items():
                    lessons_solving_progress[filename] = [0] * len(progress)
                for filename, progress in puzzles_solving_progress.items():
                    puzzles_solving_progress[filename] = [0] * len(progress)
                self.update_progress(None, None, None)
            dialog.destroy()

        reset.connect("clicked", on_reset_clicked)

        learn_home.show_all()

        if not self.first_run:
            self.notebooks["learnhome"].remove_page(-1)
        self.notebooks["learnhome"].append_page(learn_home)

        self.panels = [panel.Sidepanel().load(self) for panel in self.sidePanels]

        for panel, instance in zip(self.sidePanels, self.panels):
            if not self.first_run:
                self.notebooks[panel_name(panel.__name__)].remove_page(-1)
            self.notebooks[panel_name(panel.__name__)].append_page(instance)
            instance.show()

        perspective_manager.activate_perspective("learn")

    def update_progress(self, solving_progress, key, progress):
        self.store.clear()

        # Compute cumulative puzzles solving statistics
        solving_progress = puzzles_solving_progress.read_all()

        stat = [0, 0, 0, 0, 0, 0, 0, 0]
        for filename, progress in solving_progress.items():
            if filename.startswith("lichess"):
                stat[0] += len(progress)
                stat[1] += progress.count(1)
            elif filename.startswith("mate_in"):
                stat[2] += len(progress)
                stat[3] += progress.count(1)
            elif filename.endswith(".olv"):
                stat[4] += len(progress)
                stat[5] += progress.count(1)

        # Compute cumulative lessons solving statistics
        solving_progress = lessons_solving_progress.read_all()

        for filename, progress in solving_progress.items():
            stat[6] += len(progress)
            stat[7] += progress.count(1)

        stats = []
        for i in range(4):
            percent = 0 if not stat[i * 2 + 1] else round((stat[i * 2 + 1] * 100.) / stat[i * 2])
            stats.append("%s%%" % percent)
            stats.append(percent)

        self.store.append(stats)


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

    def get_count(self, filename):
        subdir = "puzzles" if self.progress_file.endswith("puzzles.json") else "lessons"
        if filename.lower().endswith(".pgn"):
            chessfile = PGNFile(protoopen(addDataPrefix("learn/%s/%s" % (subdir, filename))))
            chessfile.limit = 1000
            chessfile.init_tag_database()
        elif filename.lower().endswith(".olv"):
            chessfile = OLVFile(protoopen(addDataPrefix("learn/%s/%s" % (subdir, filename)), encoding="utf-8"))
        chessfile.close()
        count = chessfile.count
        return count

    def __getitem__(self, key):
        if os.path.isfile(self.progress_file):
            with open(self.progress_file, "r") as f:
                self.data = json.load(f)
            if key not in self.data:
                self.__setitem__(key, [0] * self.get_count(key))
        else:
            self.__setitem__(key, [0] * self.get_count(key))

        # print("Solved: %s / %s %s" % (self[key].count(1), len(self[key]), key))

        return self.data[key]

    def __setitem__(self, key, value):
        with open(self.progress_file, "w") as f:
            self.data[key] = value
            json.dump(self.data, f)
        self.emit("progress_updated", key, value)

    def read_all(self):
        if os.path.isfile(self.progress_file):
            with open(self.progress_file, "r") as f:
                self.data = json.load(f)
                return self.data
        else:
            return {}


puzzles_solving_progress = SolvingProgress("puzzles.json")
lessons_solving_progress = SolvingProgress("lessons.json")
