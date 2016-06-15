# -*- coding: UTF-8 -*-

import os
import webbrowser
import math
import atexit
import logging
import signal
import subprocess
import platform
import sys

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib

from pychess.compat import urlopen, basestring, open, pathname2url, url2pathname, unquote
from pychess.System import conf, uistuff, prefix, SubProcess, idle_add
from pychess.System.uistuff import POSITION_GOLDEN
from pychess.System.Log import log, LogPipe
from pychess.System.LogEmitter import GLogHandler, logemitter
from pychess.System.debug import start_thread_dump, print_obj_referrers, print_muppy_sumary
from pychess.System.prefix import getUserDataPrefix, addUserDataPrefix
from pychess.Utils.const import HINT, NAME, SPY
from pychess.Utils.checkversion import checkversion
from pychess.widgets import enginesDialog
from pychess.widgets import newGameDialog
from pychess.widgets import tipOfTheDay
from pychess.widgets.discovererDialog import DiscovererDialog
from pychess.widgets import gamewidget
from pychess.widgets.ionest import game_handler
from pychess.widgets import analyzegameDialog
from pychess.widgets import preferencesDialog, gameinfoDialog, playerinfoDialog
from pychess.widgets.TaskerManager import tasker
from pychess.widgets.TaskerManager import NewGameTasker
from pychess.widgets.TaskerManager import InternetGameTasker
from pychess.Players.engineNest import discoverer
from pychess.Savers import chesspastebin
from pychess.ic import ICLogon
# from pychess.Database.gamelist import GameList
from pychess import VERSION, VERSION_NAME

leftkeys = list(map(Gdk.keyval_from_name, ("Left", "KP_Left")))
rightkeys = list(map(Gdk.keyval_from_name, ("Right", "KP_Right")))
upkeys = list(map(Gdk.keyval_from_name, ("Up", "KP_Up")))
downkeys = list(map(Gdk.keyval_from_name, ("Down", "KP_Down")))
homekeys = list(map(Gdk.keyval_from_name, ("Home", "KP_Home")))
endkeys = list(map(Gdk.keyval_from_name, ("End", "KP_End")))
functionkeys = [Gdk.keyval_from_name(k)
                for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9",
                          "F10", "F11")]

recentManager = Gtk.RecentManager.get_default()

TARGET_TYPE_URI_LIST = 0xbadbeef
DRAG_ACTION = Gdk.DragAction.COPY
DRAG_RESTRICT = Gtk.TargetFlags.OTHER_APP
DND_LIST = [Gtk.TargetEntry.new("text/uri-list", DRAG_RESTRICT, TARGET_TYPE_URI_LIST)]


class GladeHandlers(object):
    def on_window_key_press(window, event):
        log.debug('on_window_key_press: %s %s' % (window.get_title(), event))

        # debug leaking memory
        if Gdk.keyval_name(event.keyval) == "F12":
            if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                print_muppy_sumary()
            else:
                print_obj_referrers()

        # Tabbing related shortcuts
        if not gamewidget.getheadbook():
            pagecount = 0
        else:
            pagecount = gamewidget.getheadbook().get_n_pages()
        if pagecount > 1:
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                page_num = gamewidget.getheadbook().get_current_page()
                # Move selected
                if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                    child = gamewidget.getheadbook().get_nth_page(page_num)
                    if event.keyval == Gdk.KEY_Page_Up:
                        gamewidget.getheadbook().reorder_child(child, (
                            page_num - 1) % pagecount)
                        return True
                    elif event.keyval == Gdk.KEY_Page_Down:
                        gamewidget.getheadbook().reorder_child(child, (
                            page_num + 1) % pagecount)
                        return True
                # Change selected
                else:
                    if event.keyval == Gdk.KEY_Page_Up:
                        gamewidget.getheadbook().set_current_page(
                            (page_num - 1) % pagecount)
                        return True
                    elif event.keyval == Gdk.KEY_Page_Down:
                        gamewidget.getheadbook().set_current_page(
                            (page_num + 1) % pagecount)
                        return True

        gmwidg = gamewidget.cur_gmwidg()
        if gmwidg is not None:
            for panel in gmwidg.panels:
                focused = panel.get_focus_child()
                # Do nothing in chat panel
                if focused is not None and isinstance(focused, Gtk.Entry):
                    return False

            # Navigate on boardview with arrow keys
            if event.keyval in leftkeys:
                if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                    gmwidg.board.view.backToMainLine()
                    return True
                else:
                    gmwidg.board.view.showPrev()
                    return True
            elif event.keyval in rightkeys:
                gmwidg.board.view.showNext()
                return True
            elif event.keyval in upkeys:
                gmwidg.board.view.showPrev(step=2)
                return True
            elif event.keyval in downkeys:
                gmwidg.board.view.showNext(step=2)
                return True
            elif event.keyval in homekeys:
                gmwidg.board.view.showFirst()
                return True
            elif event.keyval in endkeys:
                gmwidg.board.view.showLast()
                return True

            if (not event.get_state() & Gdk.ModifierType.CONTROL_MASK) and \
                    (not event.get_state() & Gdk.ModifierType.MOD1_MASK) and \
                    (event.keyval != Gdk.KEY_Escape) and \
                    (event.keyval not in functionkeys):
                # Enter moves with keyboard
                board_control = gmwidg.board
                keyname = Gdk.keyval_name(event.keyval)
                board_control.key_pressed(keyname)
                print(board_control.keybuffer)
                return True

            return False

    def on_recent_game_activated(self, uri):
        if isinstance(uri, basestring):
            path = url2pathname(uri)
            recentManager.add_item("file:" + pathname2url(path))

    #          Drag 'n' Drop          #

    def on_drag_received(self, widget, context, x, y, selection, target_type,
                         timestamp):
        if target_type == TARGET_TYPE_URI_LIST:
            uris = selection.get_uris()
            if len(uris) == 1 and uris[0].lower().endswith(".pgn"):
                uri = uris[0]
                newGameDialog.LoadFileExtension.run(uri)
            else:
                newGameDialog.loadFilesAndRun(uris)

    # Game Menu

    def on_new_game1_activate(self, widget):
        newGameDialog.NewGameMode.run()

    def on_play_internet_chess_activate(self, widget):
        ICLogon.run()

    def on_load_game1_activate(self, widget):
        newGameDialog.LoadFileExtension.run(None)

    def on_set_up_position_activate(self, widget):
        rotate_menu = gamewidget.getWidgets()["rotate_board1"]
        rotate_menu.set_sensitive(True)
        gmwidg = gamewidget.cur_gmwidg()
        if gmwidg is not None:
            if len(gmwidg.gamemodel.boards) == 1:
                ply = 0
            else:
                ply = gmwidg.board.view.shown
            fen = gmwidg.gamemodel.boards[ply].asFen()
        else:
            fen = None
        newGameDialog.SetupPositionExtension.run(fen)

    def on_open_database_activate(self, widget):
        # GameList().load_games()
        pass

    def on_enter_game_notation_activate(self, widget):
        newGameDialog.EnterNotationExtension.run()

    def on_save_game1_activate(self, widget):
        gmwidg = gamewidget.cur_gmwidg()
        position = gmwidg.board.view.shown
        game_handler.saveGame(gmwidg.gamemodel, position)

    def on_save_game_as1_activate(self, widget):
        gmwidg = gamewidget.cur_gmwidg()
        position = gmwidg.board.view.shown
        game_handler.saveGameAs(gmwidg.gamemodel, position)

    def on_share_game_activate(self, widget):
        gmwidg = gamewidget.cur_gmwidg()
        chesspastebin.paste(gmwidg.gamemodel)

    def on_export_position_activate(self, widget):
        gmwidg = gamewidget.cur_gmwidg()
        position = gmwidg.board.view.shown
        game_handler.saveGameAs(gmwidg.gamemodel, position, export=True)

    def on_analyze_game_activate(self, widget):
        analyzegameDialog.run()

    def on_properties1_activate(self, widget):
        gameinfoDialog.run(gamewidget.getWidgets())

    def on_player_rating1_activate(self, widget):
        playerinfoDialog.run(gamewidget.getWidgets())

    def on_close1_activate(self, widget):
        gmwidg = gamewidget.cur_gmwidg()
        game_handler.closeGame(gmwidg)

    def on_quit1_activate(self, widget, *args):
        if isinstance(widget, Gdk.Event):
            if len(game_handler.gamewidgets) == 1 and conf.get("hideTabs", False):
                gmwidg = gamewidget.cur_gmwidg()
                game_handler.closeGame(gmwidg, gmwidg.gamemodel)
                return True
            elif len(game_handler.gamewidgets) >= 1 and conf.get("closeAll", False):
                game_handler.closeAllGames(game_handler.gamewidgets)
                return True
        if game_handler.closeAllGames(game_handler.gamewidgets) in (
                Gtk.ResponseType.OK, Gtk.ResponseType.YES):
            Gtk.main_quit()
        else:
            return True

    # View Menu

    def on_rotate_board1_activate(self, widget):
        board_control = newGameDialog.SetupPositionExtension.board_control
        if board_control is not None and board_control.view.is_visible():
            view = newGameDialog.SetupPositionExtension.board_control.view
        elif gamewidget.cur_gmwidg() is not None:
            view = gamewidget.cur_gmwidg().board.view
        else:
            return
        if view.rotation:
            view.rotation = 0
        else:
            view.rotation = math.pi

    def on_fullscreen1_activate(self, widget):
        gamewidget.getWidgets()["window1"].fullscreen()
        gamewidget.getWidgets()["fullscreen1"].hide()
        gamewidget.getWidgets()["leave_fullscreen1"].show()

    def on_leave_fullscreen1_activate(self, widget):
        gamewidget.getWidgets()["window1"].unfullscreen()
        gamewidget.getWidgets()["leave_fullscreen1"].hide()
        gamewidget.getWidgets()["fullscreen1"].show()

    def on_about1_activate(self, widget):
        about_dialog = gamewidget.getWidgets()["aboutdialog1"]
        response = about_dialog.run()
        if response == Gtk.ResponseType.DELETE_EVENT or response == Gtk.ResponseType.CANCEL:
            gamewidget.getWidgets()["aboutdialog1"].hide()

    def on_log_viewer1_activate(self, widget):
        from pychess.widgets import LogDialog
        if widget.get_active():
            LogDialog.show()
        else:
            LogDialog.hide()

    def on_show_sidepanels_activate(self, widget):
        gamewidget.zoomToBoard(not widget.get_active())

    def on_hint_mode_activate(self, widget):
        for gmwidg in game_handler.gamewidgets:
            if gmwidg.isInFront():
                if widget.get_active():
                    gmwidg.gamemodel.resume_analyzer(HINT)
                else:
                    gmwidg.gamemodel.pause_analyzer(HINT)

    def on_spy_mode_activate(self, widget):
        for gmwidg in game_handler.gamewidgets:
            if gmwidg.isInFront():
                if widget.get_active():
                    gmwidg.gamemodel.resume_analyzer(SPY)
                else:
                    gmwidg.gamemodel.pause_analyzer(SPY)

    # Edit menu

    def on_copy_pgn_activate(self, widget):
        gamewidget.cur_gmwidg().copy_pgn()

    def on_copy_fen_activate(self, widget):
        gamewidget.cur_gmwidg().copy_fen()

    def on_manage_engines_activate(self, widget):
        enginesDialog.run(gamewidget.getWidgets())

    def on_preferences_activate(self, widget):
        preferencesDialog.run(gamewidget.getWidgets())

    # Help menu

    def on_about_chess1_activate(self, widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))

    def on_how_to_play1_activate(self, widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))

    def translate_this_application_activate(self, widget):
        webbrowser.open("https://www.transifex.com/projects/p/pychess/")

    def on_TipOfTheDayMenuItem_activate(self, widget):
        tipOfTheDay.TipOfTheDay.show()


class PyChess(object):
    def __init__(self, log_viewer, chess_file):
        self.git_rev = ""

        self.initGlade(log_viewer)
        self.handleArgs(chess_file)
        checkversion()

        self.loaded_cids = {}
        self.saved_cids = {}
        self.terminated_cids = {}

    def on_gmwidg_created(self, gamehandler, gmwidg):
        log.debug("GladeHandlers.on_gmwidg_created: starting")
        # Bring playing window to the front
        gamewidget.getWidgets()["window1"].present()

        self.loaded_cids[gmwidg.gamemodel] = gmwidg.gamemodel.connect("game_loaded", self.update_recent)
        self.saved_cids[gmwidg.gamemodel] = gmwidg.gamemodel.connect("game_saved", self.update_recent)
        self.terminated_cids[gmwidg.gamemodel] = gmwidg.gamemodel.connect("game_terminated", self.on_terminated)

        log.debug("GladeHandlers.on_gmwidg_created: returning")

    def on_terminated(self, gamemodel):
        if gamemodel.handler_is_connected(self.loaded_cids[gamemodel]):
            gamemodel.disconnect(self.loaded_cids[gamemodel])
            del self.loaded_cids[gamemodel]
        if gamemodel.handler_is_connected(self.saved_cids[gamemodel]):
            gamemodel.disconnect(self.saved_cids[gamemodel])
            del self.saved_cids[gamemodel]
        if gamemodel.handler_is_connected(self.terminated_cids[gamemodel]):
            gamemodel.disconnect(self.terminated_cids[gamemodel])
            del self.terminated_cids[gamemodel]

    def update_recent(self, gamemodel, uri):
        if isinstance(uri, basestring):
            path = url2pathname(uri)
            recentManager.add_item("file:" + pathname2url(path))

    def initGlade(self, log_viewer):
        # Init glade and the 'GladeHandlers'
        widgets = uistuff.GladeWidgets("PyChess.glade")
        widgets.getGlade().connect_signals(GladeHandlers())

        new_game_tasker, internet_game_tasker = NewGameTasker(
        ), InternetGameTasker()
        tasker.packTaskers(new_game_tasker, internet_game_tasker)
        widgets["Background"].add(tasker)

        # Redirect widgets
        gamewidget.setWidgets(widgets)

        # Main.py still needs a minimum of information
        game_handler.connect("gmwidg_created", self.on_gmwidg_created)

        # The only menuitems that need special initing
        for widget in ("hint_mode", "spy_mode"):
            widgets[widget].set_sensitive(False)

        uistuff.keep(widgets["hint_mode"], "hint_mode", first_value=True)
        uistuff.keep(widgets["spy_mode"], "spy_mode", first_value=True)
        uistuff.keep(widgets["show_sidepanels"], "show_sidepanels", first_value=True)
        uistuff.keep(widgets["auto_call_flag"], "autoCallFlag", first_value=True)

        # Show main window and init d'n'd
        widgets["window1"].set_title('%s - PyChess' % _('Welcome'))
        widgets["window1"].connect("delete-event", GladeHandlers.__dict__["on_quit1_activate"])
        widgets["window1"].connect("key-press-event", GladeHandlers.__dict__["on_window_key_press"])

        uistuff.keepWindowSize("main", widgets["window1"], None, POSITION_GOLDEN)
        widgets["window1"].show()
        widgets["Background"].show_all()

        # To get drag in the whole window, we add it to the menu and the
        # background. If it can be gotten to work, the drag_dest_set_proxy
        # method is very interesting.
        widgets["menubar1"].drag_dest_set(Gtk.DestDefaults.ALL, DND_LIST, DRAG_ACTION)
        widgets["Background"].drag_dest_set(Gtk.DestDefaults.ALL, DND_LIST, DRAG_ACTION)

        # Init 'minor' dialogs

        # Log dialog
        if log_viewer:
            from pychess.widgets import LogDialog
            LogDialog.add_destroy_notify(
                lambda: widgets["log_viewer1"].set_active(0))
        else:
            widgets["log_viewer1"].set_property('sensitive', False)

        # About dialog
        self.aboutdialog = widgets["aboutdialog1"]
        self.aboutdialog.set_program_name(NAME)
        self.aboutdialog.set_copyright("Copyright © 2006-2016")
        self.aboutdialog.set_version(VERSION_NAME + " " + VERSION)
        if os.path.isdir(prefix.addDataPrefix(".git")):
            try:
                label = subprocess.check_output(["git", "describe"])
            except subprocess.CalledProcessError:
                label = ""
            if label:
                comments = self.aboutdialog.get_comments()
                self.git_rev = label
                self.aboutdialog.set_comments("git %s\n%s" %
                                              (self.git_rev, comments))

        with open(prefix.addDataPrefix("ARTISTS"), encoding="utf-8") as f:
            self.aboutdialog.set_artists(f.read().splitlines())
        with open(prefix.addDataPrefix("AUTHORS"), encoding="utf-8") as f:
            self.aboutdialog.set_authors(f.read().splitlines())
        with open(prefix.addDataPrefix("DOCUMENTERS"), encoding="utf-8") as f:
            self.aboutdialog.set_documenters(f.read().splitlines())
        with open(prefix.addDataPrefix("TRANSLATORS"), encoding="utf-8") as f:
            self.aboutdialog.set_translator_credits(f.read())
        with open(prefix.addDataPrefix("LICENSE"), encoding="utf-8") as f:
            self.aboutdialog.set_license(f.read())

        # RecentChooser
        def recent_item_activated(self):
            uri = self.get_current_uri()
            try:
                urlopen(unquote(uri)).close()
                newGameDialog.LoadFileExtension.run(self.get_current_uri())
            except (IOError, OSError):
                # shomething wrong whit the uri
                recentManager.remove_item(uri)

        self.menu_recent = Gtk.RecentChooserMenu()
        self.menu_recent.set_show_tips(True)
        self.menu_recent.set_sort_type(Gtk.RecentSortType.MRU)
        self.menu_recent.set_limit(10)
        self.menu_recent.set_name("menu_recent")

        self.file_filter = Gtk.RecentFilter()
        self.file_filter.add_mime_type("application/x-chess-pgn")
        self.menu_recent.set_filter(self.file_filter)

        self.menu_recent.connect("item-activated", recent_item_activated)
        widgets["load_recent_game1"].set_submenu(self.menu_recent)

        # Discoverer dialog
        def discovering_started(discoverer, binnames):
            GLib.idle_add(DiscovererDialog.show, discoverer,
                          widgets["window1"], binnames)

        discoverer.connect("discovering_started", discovering_started)
        DiscovererDialog.init(discoverer)
        discoverer.discover()

        # Tip of the day dialog
        if conf.get("show_tip_at_startup", False):
            tipOfTheDay.TipOfTheDay.show()

        if conf.get("autoLogin", False):
            internet_game_tasker.connectClicked(None)

    def website(self, clb, link):
        webbrowser.open(link)

    def handleArgs(self, chess_file):
        if chess_file:

            def do(discoverer):
                GLib.idle_add(newGameDialog.LoadFileExtension.run, chess_file)

            discoverer.connect_after("all_engines_discovered", do)


def run(no_debug, idle_add_debug, thread_debug, log_viewer, purge_recent,
        chess_file, ics_host, ics_port):
    # Start logging
    if log_viewer:
        log.logger.addHandler(GLogHandler(logemitter))
    log.logger.setLevel(logging.WARNING if no_debug is True else logging.DEBUG)
    oldlogs = [l for l in os.listdir(getUserDataPrefix())
               if l.endswith(".log")]
    conf.set("max_log_files", conf.get("max_log_files", 10))
    oldlogs.sort()
    l = len(oldlogs)
    while l > conf.get("max_log_files", 10):
        try:
            os.remove(addUserDataPrefix(oldlogs[0]))
            del oldlogs[0]
        except OSError:
            pass
        l -= 1

    if purge_recent:
        items = recentManager.get_items()
        for item in items:
            uri = item.get_uri()
            if item.get_application_info("pychess"):
                recentManager.remove_item(uri)

    signal.signal(signal.SIGINT, Gtk.main_quit)
    signal.signal(signal.SIGTERM, Gtk.main_quit)

    def cleanup():
        ICLogon.stop()
        SubProcess.finishAllSubprocesses()

    atexit.register(cleanup)

    pychess = PyChess(log_viewer, chess_file)
    idle_add.debug = idle_add_debug

    sys.stdout = LogPipe(sys.stdout, "stdout")
    sys.stderr = LogPipe(sys.stderr, "stdout")
    log.info("PyChess %s %s git %s" % (VERSION_NAME, VERSION, pychess.git_rev))
    log.info("Command line args: '%s'" % chess_file)
    log.info("Platform: %s" % platform.platform())
    log.info("Python version: %s.%s.%s" % sys.version_info[0:3])
    log.info("Pyglib version: %s.%s.%s" % GLib.pyglib_version)
    if thread_debug:
        start_thread_dump()
    if ics_host:
        ICLogon.host = ics_host
    if ics_port:
        ICLogon.port = ics_port

    Gtk.main()
