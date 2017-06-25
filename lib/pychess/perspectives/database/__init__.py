import os
import threading
import traceback
from io import StringIO

from gi.repository import Gtk, GObject, GLib

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
from pychess.widgets import gamewidget
from pychess.widgets import dock_panel_tab
from pychess.Database.model import create_indexes, drop_indexes
from pychess.Database.PgnImport import PgnImport, download_file
from pychess.Database.JvR import JvR
from pychess.Savers import pgn, fen, epd
from pychess.System.protoopen import protoopen


def new_notebook():
    notebook = Gtk.Notebook()
    notebook.set_show_tabs(False)
    notebook.set_show_border(False)
    return notebook


class Database(GObject.GObject, Perspective):
    __gsignals__ = {
        'chessfile_opened0': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'chessfile_opened': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'chessfile_closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'chessfile_imported': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        Perspective.__init__(self, "database", _("Database"))
        self.widgets = gamewidget.getWidgets()
        self.chessfile = None
        self.chessfiles = []
        self.gamelists = []
        self.filter_panels = []
        self.notebooks = {}
        self.connect("chessfile_opened0", self.on_chessfile_opened0)

    @property
    def gamelist(self):
        if self.chessfile is None:
            return None
        else:
            return self.gamelists[self.chessfiles.index(self.chessfile)]

    @property
    def filter_panel(self):
        if self.chessfile is None:
            return None
        else:
            return self.filter_panels[self.chessfiles.index(self.chessfile)]

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

        self.switcher_panel = SwitcherPanel(self)
        self.notebooks["gamelist"] = new_notebook()
        self.notebooks["opening_tree"] = new_notebook()
        self.notebooks["filter"] = new_notebook()
        self.notebooks["preview"] = new_notebook()

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(50, 50)
        self.progressbar0 = Gtk.ProgressBar(show_text=True)
        self.progressbar1 = Gtk.ProgressBar(show_text=True)

        mainwindow = gamewidget.getWidgets()["main_window"]
        self.progress_dialog = Gtk.Dialog("", mainwindow, 0, (
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.progress_dialog.get_content_area().pack_start(self.spinner, True, True, 0)
        self.progress_dialog.get_content_area().pack_start(self.progressbar0, True, True, 0)
        self.progress_dialog.get_content_area().pack_start(self.progressbar1, True, True, 0)
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
            "gamelist": (Gtk.Label(label="gamelist"), self.notebooks["gamelist"]),
            "switcher": (dock_panel_tab(_("Databases"), "", addDataPrefix("glade/panel_docker.svg")), self.switcher_panel.alignment),
            "openingtree": (dock_panel_tab(_("Openings"), "", addDataPrefix("glade/panel_book.svg")), self.notebooks["opening_tree"]),
            "filter": (dock_panel_tab(_("Filters"), "", addDataPrefix("glade/panel_docker.svg")), self.notebooks["filter"]),
            "preview": (dock_panel_tab(_("Preview"), "", addDataPrefix("glade/panel_docker.svg")), self.notebooks["preview"]),
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

    def set_sensitives(self, on):
        self.import_button.set_sensitive(on)
        self.widgets["import_chessfile"].set_sensitive(on)
        self.widgets["import_endgame_nl"].set_sensitive(on)
        self.widgets["import_twic"].set_sensitive(on)

    def open_chessfile(self, filename):
        if self.chessfile is None:
            self.init_layout()

        perspective_manager.activate_perspective("database")

        self.progress_dialog.set_title(_("Open"))
        self.progressbar0.hide()
        self.progressbar1.show()
        self.progressbar1.set_text("Importing game headers...")
        self.spinner.show()
        self.spinner.start()

        def opening():
            if filename.endswith(".pgn"):
                chessfile = pgn.load(protoopen(filename), self.progressbar1)
            elif filename.endswith(".epd"):
                chessfile = epd.load(protoopen(filename))
            elif filename.endswith(".fen"):
                chessfile = fen.load(protoopen(filename))
            else:
                chessfile = None

            GLib.idle_add(self.spinner.stop)
            GLib.idle_add(self.progress_dialog.hide)
            if chessfile is not None:
                self.chessfile = chessfile
                self.chessfiles.append(chessfile)
                GLib.idle_add(self.emit, "chessfile_opened0", chessfile)

        thread = threading.Thread(target=opening)
        thread.daemon = True
        thread.start()

        response = self.progress_dialog.run()
        if response == Gtk.ResponseType.CANCEL:
            self.importer.do_cancel()
        self.progress_dialog.hide()

    def on_chessfile_opened0(self, persp, chessfile):
        gamelist = GameList(self)
        self.gamelists.append(gamelist)
        opening_tree_panel = OpeningTreePanel(self)
        filter_panel = FilterPanel(self)
        self.filter_panels.append(filter_panel)
        preview_panel = PreviewPanel(self)

        self.notebooks["gamelist"].append_page(gamelist.box)
        self.notebooks["opening_tree"].append_page(opening_tree_panel.box)
        self.notebooks["filter"].append_page(filter_panel.box)
        self.notebooks["preview"].append_page(preview_panel.box)

        self.on_chessfile_switched(None, self.chessfile)

        gamelist.load_games()
        opening_tree_panel.update_tree(load_games=False)

        self.set_sensitives(True)
        self.emit("chessfile_opened", chessfile)

    def close(self, widget):
        i = self.chessfiles.index(self.chessfile)
        if self.chessfile.path is not None:
            self.notebooks["gamelist"].remove_page(i)
            self.notebooks["opening_tree"].remove_page(i)
            self.notebooks["filter"].remove_page(i)
            self.notebooks["preview"].remove_page(i)
            del self.gamelists[i]
            del self.filter_panels[i]
            del self.chessfiles[i]
            self.chessfile.close()

        if len(self.chessfiles) == 0:
            self.set_sensitives(False)
            perspective_manager.disable_perspective("database")

        self.emit("chessfile_closed")

    def on_chessfile_switched(self, switcher, chessfile):
        self.chessfile = chessfile
        i = self.chessfiles.index(chessfile)

        self.notebooks["gamelist"].set_current_page(i)
        self.notebooks["opening_tree"].set_current_page(i)
        self.notebooks["filter"].set_current_page(i)
        self.notebooks["preview"].set_current_page(i)

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

        # import limited to latest twic .pgn for now
        twic = twic[-1:]

        self.do_import(twic)
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
        filter_text.add_pattern("*.pgn")
        filter_text.add_mime_type("application/x-chess-pgn")
        dialog.add_filter(filter_text)

        filter_text = Gtk.FileFilter()
        filter_text.set_name(".zip")
        filter_text.add_pattern("*.zip")
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
        self.progress_dialog.set_title(_("Import"))
        self.spinner.hide()
        if len(filenames) == 1:
            self.progressbar0.hide()
        else:
            self.progressbar0.show()
        self.progressbar1.show()
        self.progressbar1.set_text("Preparing to start import...")

        # @profile_me
        def importing():
            drop_indexes(self.chessfile.engine)

            self.importer = PgnImport(self.chessfile, append_pgn=True)
            for i, filename in enumerate(filenames):
                GLib.idle_add(self.progressbar0.set_fraction, i / float(len(filenames)))
                # GLib.idle_add(self.progressbar0.set_text, filename)
                if self.importer.cancel:
                    break
                if isinstance(filename, tuple):
                    info_link, pgn_link = filename
                    self.importer.do_import(pgn_link, info=info_link, progressbar=self.progressbar1)
                else:
                    self.importer.do_import(filename, progressbar=self.progressbar1)

            GLib.idle_add(self.progressbar1.set_text, "Recreating indexes...")

            # .sqlite
            create_indexes(self.chessfile.engine)

            # .scout
            self.chessfile.init_scoutfish()

            # .bin
            self.chessfile.init_chess_db()

            self.chessfile.set_tag_filter(None)
            self.chessfile.set_fen_filter(None)
            self.chessfile.set_scout_filter(None)
            GLib.idle_add(self.gamelist.load_games)
            GLib.idle_add(self.emit, "chessfile_imported", self.chessfile)
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
        if response != Gtk.ResponseType.CANCEL:
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
            position = line.find(PREFIX)
            if position >= 0:
                latest = int(line[position + len(PREFIX):][:4])
                break
    return latest
