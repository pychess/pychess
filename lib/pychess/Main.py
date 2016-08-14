# -*- coding: UTF-8 -*-

import os
import webbrowser
import math
import platform
import sys
import subprocess

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib

from pychess.compat import urlopen, basestring, open, pathname2url, url2pathname, unquote
from pychess.System.Log import log
from pychess.System import conf, uistuff, prefix
from pychess.System.debug import print_obj_referrers, print_muppy_sumary
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
from pychess.widgets.TaskerManager import internet_game_tasker
from pychess.Players.engineNest import discoverer
from pychess.Savers import chesspastebin
from pychess.ic import ICLogon
from pychess.perspectives import perspective_manager
from pychess.perspectives.welcome import Welcome
from pychess.perspectives.games import Games
from pychess.perspectives.fics import FICS
from pychess.perspectives.database import Database
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
    def __init__(self, app):
        self.app = app

    def on_window_key_press(self, window, event):
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
            # Let default handler work if typing inside entry widgets
            current_focused_widget = gamewidget.getWidgets()["window1"].get_focus()
            if current_focused_widget is not None and isinstance(current_focused_widget, Gtk.Entry):
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

    def on_drag_received(self, widget, context, x, y, selection, target_type, timestamp):
        if target_type == TARGET_TYPE_URI_LIST:
            uris = selection.get_uris()
            if len(uris) == 1 and uris[0].lower()[-4:] in (".pgn", ".pdb", "epd"):
                uri = uris[0]
                perspective = perspective_manager.get_perspective("database")
                perspective.open_chessfile(uri)
            else:
                newGameDialog.loadFilesAndRun(uris)

    # Game Menu

    def on_new_game1_activate(self, widget):
        newGameDialog.NewGameMode.run()

    def on_play_internet_chess_activate(self, widget):
        ICLogon.run()

    def on_new_database1_activate(self, widget):
        game_handler.create_database()

    def on_load_game1_activate(self, widget):
        opendialog, savedialog, enddir, savecombo, savers = game_handler.getOpenAndSaveDialogs()
        response = opendialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filename = opendialog.get_filename()
            perspective = perspective_manager.get_perspective("database")
            perspective.open_chessfile(filename)
        opendialog.hide()

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
        persp = perspective_manager.current_perspective
        if persp.name == "games":
            gmwidg = gamewidget.cur_gmwidg()
            game_handler.closeGame(gmwidg)
        elif persp.name == "database":
            persp.close()

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
            ICLogon.stop()
            self.app.quit()
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


class PyChess(Gtk.Application):
    def __init__(self, log_viewer, purge_recent, chess_file, ics_host, ics_port):
        Gtk.Application.__init__(self,
                                 application_id="org.pychess",
                                 flags=Gio.ApplicationFlags.NON_UNIQUE)
        if ics_host:
            ICLogon.host = ics_host
        if ics_port:
            ICLogon.port = ics_port

        self.log_viewer = log_viewer
        self.purge_recent = purge_recent
        self.chess_file = chess_file
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        if self.purge_recent:
            items = recentManager.get_items()
            for item in items:
                uri = item.get_uri()
                if item.get_application_info("pychess"):
                    recentManager.remove_item(uri)

        self.git_rev = ""

        self.initGlade(self.log_viewer)
        self.addPerspectives()
        self.handleArgs(self.chess_file)
        checkversion()

        self.loaded_cids = {}
        self.saved_cids = {}
        self.terminated_cids = {}

        log.info("PyChess %s %s git %s" % (VERSION_NAME, VERSION, self.git_rev))
        log.info("Command line args: '%s'" % self.chess_file)
        log.info("Platform: %s" % platform.platform())
        log.info("Python version: %s.%s.%s" % sys.version_info[0:3])
        log.info("Pyglib version: %s.%s.%s" % GLib.pyglib_version)

    def do_activate(self):
        self.add_window(self.window)
        self.window.show_all()
        gamewidget.getWidgets()["player_rating1"].hide()
        gamewidget.getWidgets()["leave_fullscreen1"].hide()

    def on_gmwidg_created(self, gamehandler, gmwidg):
        log.debug("GladeHandlers.on_gmwidg_created: starting")
        # Bring playing window to the front
        gamewidget.getWidgets()["window1"].present()

        self.loaded_cids[gmwidg.gamemodel] = gmwidg.gamemodel.connect("game_loaded", self.update_recent)
        self.saved_cids[gmwidg.gamemodel] = gmwidg.gamemodel.connect("game_saved", self.update_recent)
        self.terminated_cids[gmwidg.gamemodel] = gmwidg.gamemodel.connect("game_terminated", self.on_terminated)

        log.debug("GladeHandlers.on_gmwidg_created: returning")

    def on_chessfile_opened(self, persp, chessfile):
        self.update_recent(None, chessfile.path)

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
        self.widgets = widgets = uistuff.GladeWidgets("PyChess.glade")
        self.glade_handlers = GladeHandlers(self)
        widgets.getGlade().connect_signals(self.glade_handlers)
        self.window = widgets["window1"]

        # new_game_tasker, internet_game_tasker = NewGameTasker(
        # ), InternetGameTasker()
        # tasker.packTaskers(new_game_tasker, internet_game_tasker)
        # widgets["Background"].add(tasker)

        # Redirect widgets
        gamewidget.setWidgets(widgets)

        # Main.py still needs a minimum of information
        game_handler.connect("gmwidg_created", self.on_gmwidg_created)

        # The only menuitems that need special initing
        for widget in ("hint_mode", "spy_mode"):
            widgets[widget].set_sensitive(False)

        uistuff.keep(widgets["hint_mode"], "hint_mode", first_value=False)
        uistuff.keep(widgets["spy_mode"], "spy_mode", first_value=False)
        uistuff.keep(widgets["show_sidepanels"], "show_sidepanels", first_value=True)
        uistuff.keep(widgets["auto_call_flag"], "autoCallFlag", first_value=True)

        # Show main window and init d'n'd
        widgets["window1"].set_title('%s - PyChess' % _('Welcome'))
        widgets["window1"].connect("delete-event", self.glade_handlers.on_quit1_activate)
        widgets["window1"].connect("key-press-event", self.glade_handlers.on_window_key_press)

        uistuff.keepWindowSize("main", widgets["window1"], None, uistuff.POSITION_GOLDEN)

        # To get drag in the whole window, we add it to the menu and the
        # background. If it can be gotten to work, the drag_dest_set_proxy
        # method is very interesting.
        widgets["menubar1"].drag_dest_set(Gtk.DestDefaults.ALL, DND_LIST, DRAG_ACTION)
        widgets["box2"].drag_dest_set(Gtk.DestDefaults.ALL, DND_LIST, DRAG_ACTION)
        widgets["perspectives_notebook"].drag_dest_set(Gtk.DestDefaults.ALL, DND_LIST, DRAG_ACTION)

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
                perspective = perspective_manager.get_perspective("database")
                perspective.open_chessfile(self.get_current_uri())
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
        self.file_filter.add_mime_type("application/x-chess-epd")
        self.file_filter.add_mime_type("application/x-chess-fen")
        self.file_filter.add_mime_type("application/x-chess-pychess")
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

    def addPerspectives(self):
        perspective_manager.set_widgets(self.widgets)
        for persp in (Welcome, Games, FICS, Database):
            perspective = persp()
            perspective_manager.add_perspective(perspective)
            perspective.create_toolbuttons()

            if persp == Database:
                perspective.connect("chessfile_opened", self.on_chessfile_opened)

        new_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_NEW)
        new_button.set_tooltip_text(_("New Game"))
        new_button.connect("clicked", self.glade_handlers.on_new_game1_activate)
        perspective_manager.toolbar.insert(new_button, 0)

        open_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_OPEN)
        open_button.set_tooltip_text(_("Open Game"))
        open_button.connect("clicked", self.glade_handlers.on_load_game1_activate)
        perspective_manager.toolbar.insert(open_button, 1)

    def handleArgs(self, chess_file):
        if chess_file:

            def do(discoverer):
                perspective = perspective_manager.get_perspective("database")
                GLib.idle_add(perspective.open_chessfile, chess_file)

            discoverer.connect_after("all_engines_discovered", do)
