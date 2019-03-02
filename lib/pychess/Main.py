# -*- coding: UTF-8 -*-

import asyncio
import datetime
import os
import webbrowser
import math
import platform
import sys
import subprocess
from urllib.request import url2pathname, pathname2url

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib

from pychess.compat import create_task
from pychess.System.Log import log
from pychess.System import conf, uistuff, prefix
from pychess.Utils.const import HINT, NAME, SPY, NORMALCHESS
from pychess.Utils.checkversion import checkversion
from pychess.widgets import enginesDialog
from pychess.widgets import newGameDialog
from pychess.widgets.Background import hexcol
from pychess.widgets.tipOfTheDay import TipOfTheDay
from pychess.widgets.discovererDialog import DiscovererDialog
from pychess.widgets.ExternalsDialog import ExternalsDialog
from pychess.widgets import gamewidget
from pychess.widgets.analyzegameDialog import AnalyzeGameDialog
from pychess.widgets import preferencesDialog, gameinfoDialog, playerinfoDialog
from pychess.widgets.TaskerManager import internet_game_tasker
from pychess.widgets.RecentChooser import recent_menu, recent_manager
from pychess.Players.engineNest import discoverer
from pychess.Savers import chesspastebin
from pychess.ic import ICLogon
from pychess.perspectives import perspective_manager
from pychess.perspectives.welcome import Welcome
from pychess.perspectives.games import Games, get_open_dialog
from pychess.perspectives.learn import Learn
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

TARGET_TYPE_URI_LIST = 0xbadbeef
DRAG_ACTION = Gdk.DragAction.COPY
DRAG_RESTRICT = Gtk.TargetFlags.OTHER_APP
DND_LIST = [Gtk.TargetEntry.new("text/uri-list", DRAG_RESTRICT, TARGET_TYPE_URI_LIST)]


class GladeHandlers:
    def __init__(self, app):
        self.app = app

    def on_window_key_press(self, window, event):
        log.debug('on_window_key_press: %s %s' % (window.get_title(), event))

        # debug leaking memory
        if Gdk.keyval_name(event.keyval) == "F12":
            from pychess.System.debug import print_obj_referrers, print_muppy_sumary
            if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                print_muppy_sumary()
            else:
                print_obj_referrers()

        # Tabbing related shortcuts
        persp = perspective_manager.get_perspective("games")
        if not persp.getheadbook():
            pagecount = 0
        else:
            pagecount = persp.getheadbook().get_n_pages()
        if pagecount > 1:
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                page_num = persp.getheadbook().get_current_page()
                # Move selected
                if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                    child = persp.getheadbook().get_nth_page(page_num)
                    if event.keyval == Gdk.KEY_Page_Up:
                        persp.getheadbook().reorder_child(child, (
                            page_num - 1) % pagecount)
                        return True
                    elif event.keyval == Gdk.KEY_Page_Down:
                        persp.getheadbook().reorder_child(child, (
                            page_num + 1) % pagecount)
                        return True
                # Change selected
                else:
                    if event.keyval == Gdk.KEY_Page_Up:
                        persp.getheadbook().set_current_page(
                            (page_num - 1) % pagecount)
                        return True
                    elif event.keyval == Gdk.KEY_Page_Down:
                        persp.getheadbook().set_current_page(
                            (page_num + 1) % pagecount)
                        return True

        gmwidg = persp.cur_gmwidg()
        if gmwidg is not None:
            # Let default handler work if typing inside entry widgets
            current_focused_widget = gamewidget.getWidgets()["main_window"].get_focus()
            if current_focused_widget is not None and isinstance(current_focused_widget, Gtk.Entry):
                return False

            # Prevent moving in game while lesson not finished
            if gmwidg.gamemodel.lesson_game:
                return

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
        if isinstance(uri, str):
            path = url2pathname(uri)
            recent_manager.add_item("file:" + pathname2url(path))

    # Drag 'n' Drop

    def on_drag_received(self, widget, context, x, y, selection, target_type, timestamp):
        if target_type == TARGET_TYPE_URI_LIST:
            uris = selection.get_uris()
            for uri in uris:
                if uri.lower().endswith(".fen"):
                    newGameDialog.loadFileAndRun(uri)
                else:
                    perspective = perspective_manager.get_perspective("database")
                    perspective.open_chessfile(uri)

    # Game Menu

    def on_new_game1_activate(self, widget):
        newGameDialog.NewGameMode.run()

    def on_set_up_position_activate(self, widget):
        rotate_menu = gamewidget.getWidgets()["rotate_board1"]
        rotate_menu.set_sensitive(True)
        persp = perspective_manager.get_perspective("games")
        gmwidg = persp.cur_gmwidg()
        if gmwidg is not None:
            ply = gmwidg.board.view.shown
            variation = gmwidg.board.view.shown_variation_idx
            board = gmwidg.gamemodel.getBoardAtPly(ply, variation)
            fen = board.asFen()
            variant = board.variant
        else:
            fen = None
            variant = NORMALCHESS
        newGameDialog.SetupPositionExtension.run(fen, variant)

    def on_enter_game_notation_activate(self, widget):
        newGameDialog.EnterNotationExtension.run()

    def on_play_internet_chess_activate(self, widget):
        ICLogon.run()

    def on_load_game1_activate(self, widget):
        dialog = get_open_dialog()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filenames = dialog.get_filenames()
        else:
            filenames = None

        dialog.destroy()

        if filenames is not None:
            for filename in filenames:
                if filename.lower().endswith(".fen"):
                    newGameDialog.loadFileAndRun(filename)
                else:
                    perspective = perspective_manager.get_perspective("database")
                    perspective.open_chessfile(filename)

    def on_save_game1_activate(self, widget):
        perspective = perspective_manager.get_perspective("games")
        gmwidg = perspective.cur_gmwidg()
        position = gmwidg.board.view.shown
        perspective.saveGame(gmwidg.gamemodel, position)

    def on_save_game_as1_activate(self, widget):
        perspective = perspective_manager.get_perspective("games")
        gmwidg = perspective.cur_gmwidg()
        position = gmwidg.board.view.shown
        perspective.saveGameAs(gmwidg.gamemodel, position)

    def on_export_position_activate(self, widget):
        perspective = perspective_manager.get_perspective("games")
        gmwidg = perspective.cur_gmwidg()
        position = gmwidg.board.view.shown
        perspective = perspective_manager.get_perspective("games")
        perspective.saveGameAs(gmwidg.gamemodel, position, export=True)

    def on_share_game_activate(self, widget):
        perspective = perspective_manager.get_perspective("games")
        gmwidg = perspective.cur_gmwidg()
        chesspastebin.paste(gmwidg.gamemodel)

    def on_properties1_activate(self, widget):
        gameinfoDialog.run(gamewidget.getWidgets())

    def on_analyze_game_activate(self, widget):
        analyze_game_dialog = AnalyzeGameDialog()
        analyze_game_dialog.run()

    def on_player_rating1_activate(self, widget):
        playerinfoDialog.run(gamewidget.getWidgets())

    def on_close1_activate(self, widget):
        persp = perspective_manager.current_perspective
        if persp.name == "games":
            gmwidg = persp.cur_gmwidg()
            persp.closeGame(gmwidg)
        elif persp.name == "database":
            persp.close()

    def on_quit1_activate(self, widget, *args):
        perspective = perspective_manager.get_perspective("games")
        if isinstance(widget, Gdk.Event):
            if len(perspective.gamewidgets) == 1 and conf.get("hideTabs"):
                gmwidg = perspective.cur_gmwidg()
                perspective.closeGame(gmwidg, gmwidg.gamemodel)
                return True
            elif len(perspective.gamewidgets) >= 1 and conf.get("closeAll"):
                perspective.closeAllGames(perspective.gamewidgets)
                return True
        if perspective.closeAllGames(perspective.gamewidgets) in (
                Gtk.ResponseType.OK, Gtk.ResponseType.YES):
            ICLogon.stop()
            self.app.loop.stop()
            self.app.quit()
        else:
            return True

    # View Menu

    def on_rotate_board1_activate(self, widget):
        board_control = newGameDialog.SetupPositionExtension.board_control
        persp = perspective_manager.get_perspective("games")
        if board_control is not None and board_control.view.is_visible():
            view = newGameDialog.SetupPositionExtension.board_control.view
        elif persp.cur_gmwidg() is not None:
            view = persp.cur_gmwidg().board.view
        else:
            return
        if view.rotation:
            view.rotation = 0
        else:
            view.rotation = math.pi

    def on_fullscreen1_activate(self, widget):
        gamewidget.getWidgets()["main_window"].fullscreen()
        gamewidget.getWidgets()["fullscreen1"].hide()
        gamewidget.getWidgets()["leave_fullscreen1"].show()

    def on_leave_fullscreen1_activate(self, widget):
        gamewidget.getWidgets()["main_window"].unfullscreen()
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
        perspective = perspective_manager.get_perspective("games")
        if perspective is not None:
            perspective.zoomToBoard(not widget.get_active())

    def on_hint_mode_activate(self, widget):
        perspective = perspective_manager.get_perspective("games")
        if perspective is None:
            return

        for gmwidg in perspective.gamewidgets:
            if gmwidg.isInFront():
                try:
                    analyzer = gmwidg.gamemodel.spectators[HINT]
                except KeyError:
                    continue
                if widget.get_active():
                    gmwidg.show_arrow(analyzer, HINT)
                else:
                    gmwidg.hide_arrow(analyzer, HINT)

    def on_spy_mode_activate(self, widget):
        perspective = perspective_manager.get_perspective("games")
        if perspective is None:
            return
        for gmwidg in perspective.gamewidgets:
            if gmwidg.isInFront():
                try:
                    analyzer = gmwidg.gamemodel.spectators[HINT]
                except KeyError:
                    continue
                if widget.get_active():
                    gmwidg.show_arrow(analyzer, SPY)
                else:
                    gmwidg.hide_arrow(analyzer, SPY)

    # Edit menu

    def on_copy_pgn_activate(self, widget):
        persp = perspective_manager.get_perspective("games")
        if perspective_manager.current_perspective == persp:
            persp.cur_gmwidg().board.view.copy_pgn()
            return

        persp = perspective_manager.get_perspective("database")
        if perspective_manager.current_perspective == persp:
            if persp.preview_panel is not None:
                persp.preview_panel.boardview.copy_pgn()

    def on_copy_fen_activate(self, widget):
        persp = perspective_manager.get_perspective("games")
        if perspective_manager.current_perspective == persp:
            persp.cur_gmwidg().board.view.copy_fen()
            return

        persp = perspective_manager.get_perspective("database")
        if perspective_manager.current_perspective == persp:
            if persp.preview_panel is not None:
                persp.preview_panel.boardview.copy_fen()

    def on_manage_engines_activate(self, widget):
        enginesDialog.run(gamewidget.getWidgets())

    def on_download_externals_activate(self, widget):
        externals_dialog = ExternalsDialog()
        externals_dialog.show()

    def on_preferences_activate(self, widget):
        preferencesDialog.run(gamewidget.getWidgets())

    # Database menu

    def on_new_database1_activate(self, widget):
        perspective = perspective_manager.get_perspective("database")
        perspective.create_database()

    def on_import_chessfile_activate(self, widget):
        perspective = perspective_manager.get_perspective("database")
        perspective.on_import_clicked(widget)

    def on_database_save_as_activate(self, widget):
        perspective = perspective_manager.get_perspective("database")
        perspective.on_save_as_clicked(widget)

    def on_create_book_activate(self, widget):
        perspective = perspective_manager.get_perspective("database")
        perspective.create_book()

    def on_import_endgame_nl_activate(self, widget):
        perspective = perspective_manager.get_perspective("database")
        perspective.on_import_endgame_nl()

    def on_import_twic_activate(self, widget):
        perspective = perspective_manager.get_perspective("database")
        perspective.on_import_twic()

    def on_update_players_activate(self, widget):
        perspective = perspective_manager.get_perspective("database")
        perspective.on_update_players()

    # Help menu

    def on_about_chess1_activate(self, widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Chess"))

    def on_how_to_play1_activate(self, widget):
        webbrowser.open(_("http://en.wikipedia.org/wiki/Rules_of_chess"))

    def translate_this_application_activate(self, widget):
        webbrowser.open("https://www.transifex.com/projects/p/pychess/")

    def on_TipOfTheDayMenuItem_activate(self, widget):
        tip_of_the_day = TipOfTheDay()
        tip_of_the_day.show()


class PyChess(Gtk.Application):
    def __init__(self, log_viewer, purge_recent, chess_file, ics_host, ics_port, loop, splash):
        Gtk.Application.__init__(self,
                                 application_id="org.pychess",
                                 flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.loop = loop

        if ics_host:
            ICLogon.host = ics_host
        if ics_port:
            ICLogon.port = ics_port

        self.log_viewer = log_viewer
        self.purge_recent = purge_recent
        self.chess_file = chess_file
        self.window = None
        self.splash = splash

    def do_startup(self):
        Gtk.Application.do_startup(self)

        if self.purge_recent:
            items = recent_manager.get_items()
            for item in items:
                uri = item.get_uri()
                if item.get_application_info("pychess"):
                    recent_manager.remove_item(uri)

        self.git_rev = ""

        self.initGlade(self.log_viewer)
        self.addPerspectives()
        self.handleArgs(self.chess_file)
        create_task(checkversion())

        self.loaded_cids = {}
        self.saved_cids = {}
        self.terminated_cids = {}

        log.info("PyChess %s %s git %s" % (VERSION_NAME, VERSION, self.git_rev))
        log.info("Command line args: '%s'" % self.chess_file)
        log.info("Platform: %s" % platform.platform())
        log.info("Python version: %s.%s.%s" % sys.version_info[0:3])
        log.info("Pyglib version: %s.%s.%s" % GLib.pyglib_version)
        log.info("Gtk version: %s.%s.%s" % (Gtk.get_major_version(),
                                            Gtk.get_minor_version(),
                                            Gtk.get_micro_version()))

    @asyncio.coroutine
    def print_tasks(self):
        while True:
            print(datetime.datetime.now().time())
            loop = asyncio.get_event_loop()
            tasks = asyncio.Task.all_tasks(loop)
            for task in tasks:
                print(task)
            print("------------")
            yield from asyncio.sleep(10)

    def do_activate(self):
        # create_task(self.print_tasks())
        self.add_window(self.window)
        self.window.show_all()
        gamewidget.getWidgets()["player_rating1"].hide()
        gamewidget.getWidgets()["leave_fullscreen1"].hide()

        # Externals download dialog
        if not conf.get("dont_show_externals_at_startup"):
            externals_dialog = ExternalsDialog()
            externals_dialog.show()

        # Tip of the day dialog
        if conf.get("show_tip_at_startup"):
            tip_of_the_day = TipOfTheDay()
            tip_of_the_day.show()

        preferencesDialog.run(gamewidget.getWidgets())

        def on_all_engine_discovered(discoverer):
            engine = discoverer.getEngineByName(discoverer.getEngineLearn())
            if engine is None:
                engine = discoverer.getEngineN(-1)
            default_engine = engine.get("md5")
            conf.set("ana_combobox", default_engine)
            conf.set("inv_ana_combobox", default_engine)

        # Try to set conf analyzer engine on very first start of pychess
        if conf.get("ana_combobox") == 0:
            discoverer.connect_after("all_engines_discovered", on_all_engine_discovered)

        dd = DiscovererDialog(discoverer)
        self.dd_task = create_task(dd.start())

        style_ctxt = gamewidget.getWidgets()["main_window"].get_style_context()
        LIGHT = hexcol(style_ctxt.lookup_color("p_light_color")[1])
        DARK = hexcol(style_ctxt.lookup_color("p_dark_color")[1])
        conf.set("lightcolour", LIGHT)
        conf.set("darkcolour", DARK)

        self.splash.destroy()

    def on_gmwidg_created(self, gamehandler, gmwidg):
        log.debug("GladeHandlers.on_gmwidg_created: starting")
        # Bring playing window to the front
        gamewidget.getWidgets()["main_window"].present()

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
        if isinstance(uri, str):
            path = url2pathname(uri)
            recent_manager.add_item("file:" + pathname2url(path))

    def initGlade(self, log_viewer):
        # Init glade and the 'GladeHandlers'
        self.widgets = widgets = uistuff.GladeWidgets("PyChess.glade")
        self.glade_handlers = GladeHandlers(self)
        widgets.getGlade().connect_signals(self.glade_handlers)
        self.window = widgets["main_window"]

        # new_game_tasker, internet_game_tasker = NewGameTasker(
        # ), InternetGameTasker()
        # tasker.packTaskers(new_game_tasker, internet_game_tasker)
        # widgets["Background"].add(tasker)

        # Redirect widgets
        gamewidget.setWidgets(widgets)

        # The only menuitems that need special initing
        for widget in ("hint_mode", "spy_mode"):
            widgets[widget].set_sensitive(False)

        uistuff.keep(widgets["hint_mode"], "hint_mode")
        uistuff.keep(widgets["spy_mode"], "spy_mode")
        uistuff.keep(widgets["show_sidepanels"], "show_sidepanels")
        uistuff.keep(widgets["auto_call_flag"], "autoCallFlag")

        # Show main window and init d'n'd
        widgets["main_window"].set_title('%s - PyChess' % _('Welcome'))
        widgets["main_window"].connect("delete-event", self.glade_handlers.on_quit1_activate)
        widgets["main_window"].connect("key-press-event", self.glade_handlers.on_window_key_press)

        uistuff.keepWindowSize("main", widgets["main_window"], None, uistuff.POSITION_GOLDEN)

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
        self.aboutdialog.set_copyright("Copyright © 2006-2018")
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

        widgets["load_recent_game1"].set_submenu(recent_menu)

        if conf.get("autoLogin"):
            internet_game_tasker.connectClicked(None)

    def website(self, clb, link):
        webbrowser.open(link)

    def addPerspectives(self):
        perspective_manager.set_widgets(self.widgets)
        for persp in (Welcome, Games, FICS, Database, Learn):
            perspective = persp()
            perspective_manager.add_perspective(perspective)
            perspective.create_toolbuttons()

            if persp == Database:
                perspective.connect("chessfile_opened", self.on_chessfile_opened)
            elif persp == Games:
                perspective.connect("gmwidg_created", self.on_gmwidg_created)

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
                perspective.open_chessfile(chess_file)
                self.dd_task.cancel()

            discoverer.connect_after("all_engines_discovered", do)
