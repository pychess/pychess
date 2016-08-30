import os
import threading
import traceback

from gi.repository import Gtk, GObject, GLib

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
from pychess.Database.PgnImport import PgnImport, FIDEPlayersImport, download_file
from pychess.Database.JvR import JvR
from pychess.Savers import database, pgn, fen, epd
from pychess.System.protoopen import protoopen
from pychess.System import profile_me


class Database(GObject.GObject, Perspective):
    __gsignals__ = {
        'chessfile_opened': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'chessfile_closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'chessfile_imported': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'chessfile_switched': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
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

        self.progressbar0 = Gtk.ProgressBar(show_text=True)
        self.progressbar = Gtk.ProgressBar(show_text=True)
        self.progress_dialog = Gtk.Dialog("Import", None, 0, (
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.progress_dialog.get_content_area().pack_start(self.progressbar0, True, True, 0)
        self.progress_dialog.get_content_area().pack_start(self.progressbar, True, True, 0)
        self.progress_dialog.get_content_area().show_all()

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

        self.switcher_panel.connect("chessfile_switched", self.on_chessfile_switched)

    def open_chessfile(self, filename):
        if filename.endswith(".pdb"):
            chessfile = database.load(filename)
        elif filename.endswith(".pgn"):
            chessfile = pgn.load(protoopen(filename))
        elif filename.endswith(".epd"):
            chessfile = epd.load(protoopen(filename))
        elif filename.endswith(".fen"):
            chessfile = fen.load(protoopen(filename))
        else:
            return

        if self.gamelist is None:
            self.init_layout()

        perspective_manager.activate_perspective("database")
        self.emit("chessfile_opened", chessfile)

    def close(self, widget):
        self.emit("chessfile_closed")

    def on_chessfile_switched(self, switcher, chessfile):
        self.emit("chessfile_switched", chessfile)

    def on_import_endgame_nl(self):
        self.do_import(JvR)

        response = self.progress_dialog.run()
        if response == Gtk.ResponseType.CANCEL:
            self.importer.do_cancel()
        self.progress_dialog.hide()

    def on_import_twic(self):
        LATEST = get_latest_twic()
        if LATEST is None:
            return

        html = "http://www.theweekinchess.com/html/twic%s.html"
        twic = []

        pgn = "https://raw.githubusercontent.com/rozim/ChessData/master/Twic/fix-twic%s.pgn"
        # pgn = "/home/tamas/PGN/twic/twic%sg.zip"
        for i in range(210, 920):
            twic.append((html % i, pgn % i))

        pgn = "http://www.theweekinchess.com/zips/twic%sg.zip"
        # pgn = "/home/tamas/PGN/twic/twic%sg.zip"
        for i in range(920, LATEST + 1):
            twic.append((html % i, pgn % i))

        twic.append((html % LATEST, pgn % LATEST))

        self.do_import(twic)
        response = self.progress_dialog.run()
        if response == Gtk.ResponseType.CANCEL:
            self.importer.do_cancel()
        self.progress_dialog.hide()

    def on_update_players(self):
        def importing():
            self.importer = FIDEPlayersImport(self.gamelist.chessfile.engine)
            self.importer.import_players(progressbar=self.progressbar)
            GLib.idle_add(self.progress_dialog.hide)

        thread = threading.Thread(target=importing)
        thread.daemon = True
        thread.start()

        response = self.progress_dialog.run()
        if response == Gtk.ResponseType.CANCEL:
            self.importer.do_cancel()
        self.progress_dialog.hide()

    def on_import_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            _("Open chess file"), None, Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
             Gtk.ResponseType.OK))
        dialog.set_select_multiple(True)

        filter_text = Gtk.FileFilter()
        filter_text.set_name(".pgn")
        filter_text.add_mime_type("application/x-chess-pgn")
        dialog.add_filter(filter_text)

        filter_text = Gtk.FileFilter()
        filter_text.set_name(".zip")
        filter_text.add_mime_type("application/zip")
        dialog.add_filter(filter_text)

        dialog = NestedFileChooserDialog(dialog)
        filenames = dialog.run()
        if filenames is not None:
            self.do_import(filenames)

            response = self.progress_dialog.run()
            if response == Gtk.ResponseType.CANCEL:
                self.importer.do_cancel()
            self.progress_dialog.hide()

    def do_import(self, filenames):
        @profile_me
        def importing():
            GLib.idle_add(self.progressbar.set_text, "Preparing to start import...")

            self.importer = PgnImport(self.gamelist.chessfile.engine)
            for i, filename in enumerate(filenames):
                GLib.idle_add(self.progressbar0.set_fraction, (i + 1) / float(len(filenames)))
                # GLib.idle_add(self.progressbar0.set_text, filename)
                if self.importer.cancel:
                    break
                if isinstance(filename, tuple):
                    info_link, pgn_link = filename
                    self.importer.do_import(pgn_link, info=info_link, progressbar=self.progressbar)
                else:
                    self.importer.do_import(filename, progressbar=self.progressbar)

            self.gamelist.offset = 0
            self.gamelist.chessfile.build_where_tags("")
            self.gamelist.chessfile.build_where_bitboards(0, 0)
            self.gamelist.chessfile.build_query()
            self.gamelist.chessfile.update_count()
            GLib.idle_add(self.gamelist.load_games)
            GLib.idle_add(self.emit, "chessfile_imported", self.gamelist.chessfile)
            GLib.idle_add(self.progress_dialog.hide)

        thread = threading.Thread(target=importing)
        thread.daemon = True
        thread.start()


class NestedFileChooserDialog(object):
    def __init__(self, dialog):
        self.dialog = dialog
        self.filenames = None

    def run(self):
        self._run()
        return self.filenames

    def _run(self):
        self.dialog.show()
        self.dialog.connect("response", self._response)
        Gtk.main()

    def _response(self, dialog, response):
        self.filenames = self.dialog.get_filenames()
        self.dialog.destroy()
        Gtk.main_quit()


def get_latest_twic():
    filename = download_file("http://www.theweekinchess.com/twic")
    latest = None

    if filename is None:
        return latest

    PREFIX = 'href="http://www.theweekinchess.com/html/twic'
    with open(filename) as f:
        for line in f:
            if line.lstrip().startswith(PREFIX):
                latest = int(line.strip()[len(PREFIX):-6])
                break
    return latest
