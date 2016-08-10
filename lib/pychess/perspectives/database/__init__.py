import os
import threading
import traceback

from gi.repository import Gtk, GLib, GObject

from pychess.compat import StringIO
from pychess.System.Log import log
from pychess.perspectives import Perspective, perspective_manager
from pychess.perspectives.database.gamelist import GameList
from pychess.perspectives.database.SwitcherPanel import SwitcherPanel
from pychess.perspectives.database.OpeningTreePanel import OpeningTreePanel
from pychess.perspectives.database.FilterPanel import FilterPanel
from pychess.perspectives.database.PreviewPanel import PreviewPanel
from pychess.System.prefix import addDataPrefix, addUserConfigPrefix
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock import EAST, SOUTH, CENTER, NORTH
from pychess.widgets import dock_panel_tab
from pychess.widgets.ionest import game_handler
from pychess.Database.PgnImport import PgnImport
from pychess.Savers import database, pgn, fen, epd
from pychess.System.protoopen import protoopen


class Database(GObject.GObject, Perspective):
    __gsignals__ = {
        'chessfile_opened': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'chessfile_closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        Perspective.__init__(self, "database", _("Database"))
        self.gamelist = None

    def create_toolbuttons(self):
        self.import_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CONVERT)
        self.import_button.set_tooltip_text(_("Import PGN file"))
        self.import_button.connect("clicked", self.on_import_clicked)

        self.close_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CLOSE)
        self.close_button.set_tooltip_text(_("Close"))
        self.close_button.connect("clicked", self.close)

    def init_layout(self):
        perspective_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        perspective_manager.set_perspective_widget("database", perspective_widget)

        self.gamelist = GameList(database.load(None))
        self.switcher_panel = SwitcherPanel(self.gamelist)
        self.opening_tree_panel = OpeningTreePanel(self.gamelist)
        self.filter_panel = FilterPanel(self.gamelist)
        self.preview_panel = PreviewPanel(self.gamelist)

        self.progressbar = Gtk.ProgressBar(show_text=True)

        perspective = perspective_manager.get_perspective("database")

        self.dock = PyDockTop("database", perspective)
        align = Gtk.Alignment()
        align.show()
        align.add(self.dock)
        self.dock.show()
        perspective_widget.pack_start(align, True, True, 0)

        dockLocation = addUserConfigPrefix("pydock-database.xml")

        docks = {
            "gamelist": (Gtk.Label(label="gamelist"), self.gamelist.box),
            "switcher": (dock_panel_tab(_("Database switcher"), "", addDataPrefix("glade/panel_docker.svg")), self.switcher_panel.alignment),
            "openingtree": (dock_panel_tab(_("Opening tree"), "", addDataPrefix("glade/panel_docker.svg")), self.opening_tree_panel.box),
            "filter": (dock_panel_tab(_("Filter"), "", addDataPrefix("glade/panel_docker.svg")), self.filter_panel.box),
            "preview": (dock_panel_tab(_("Preview"), "", addDataPrefix("glade/panel_docker.svg")), self.preview_panel.box),
        }

        if os.path.isfile(dockLocation):
            try:
                self.dock.loadFromXML(dockLocation, docks)
            except Exception as e:
                stringio = StringIO()
                traceback.print_exc(file=stringio)
                error = stringio.getvalue()
                log.error("Dock loading error: %s\n%s" % (e, error))
                msg_dia = Gtk.MessageDialog(None,
                                            type=Gtk.MessageType.ERROR,
                                            buttons=Gtk.ButtonsType.CLOSE)
                msg_dia.set_markup(_(
                    "<b><big>PyChess was unable to load your panel settings</big></b>"))
                msg_dia.format_secondary_text(_(
                    "Your panel settings have been reset. If this problem repeats, \
                    you should report it to the developers"))
                msg_dia.run()
                msg_dia.hide()
                os.remove(dockLocation)
                for title, panel in docks.values():
                    title.unparent()
                    panel.unparent()

        if not os.path.isfile(dockLocation):
            leaf = self.dock.dock(docks["gamelist"][1], CENTER, docks["gamelist"][0], "gamelist")
            leaf.setDockable(False)

            leaf.dock(docks["switcher"][1], NORTH, docks["switcher"][0], "switcher")
            leaf = leaf.dock(docks["filter"][1], EAST, docks["filter"][0], "filter")
            leaf = leaf.dock(docks["openingtree"][1], SOUTH, docks["openingtree"][0], "openingtree")
            leaf.dock(docks["preview"][1], SOUTH, docks["preview"][0], "preview")

        def unrealize(dock):
            dock.saveToXML(dockLocation)
            dock._del()

        self.dock.connect("unrealize", unrealize)

        self.dock.show_all()
        perspective_widget.show_all()

        perspective_manager.set_perspective_toolbuttons("database", [self.import_button, self.close_button])

    def open_chessfile(self, filename):
        if self.gamelist is None:
            self.init_layout()

        perspective_manager.activate_perspective("database")

        if filename.endswith(".pdb"):
            chessfile = database.load(filename)
        elif filename.endswith(".pgn"):
            chessfile = pgn.load(protoopen(filename))
        elif filename.endswith(".epd"):
            chessfile = epd.load(protoopen(filename))
        elif filename.endswith(".fen"):
            chessfile = fen.load(protoopen(filename))

        self.emit("chessfile_opened", chessfile)

    def close(self, widget):
        self.emit("chessfile_closed")

    def on_import_clicked(self, widget):
        opendialog, savedialog, enddir, savecombo, savers = game_handler.getOpenAndSaveDialogs()
        opendialog.set_select_multiple(True)
        response = opendialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filenames = opendialog.get_filenames()
            self.do_import(filenames)
        opendialog.hide()

    def do_import(self, filenames):
        self.gamelist.progress_dock.add(self.progressbar)
        self.gamelist.progress_dock.show_all()

        def importing():
            importer = PgnImport(self.gamelist.chessfile.engine)
            for filename in filenames:
                importer.do_import(filename, self.progressbar)
            GLib.idle_add(self.gamelist.progress_dock.remove, self.progressbar)
            GLib.idle_add(self.gamelist.load_games)

        thread = threading.Thread(target=importing)
        thread.daemon = True
        thread.start()
