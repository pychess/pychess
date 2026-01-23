import asyncio
import unittest
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from pychess.Utils.const import FEN_START, NORMALCHESS
from pychess.Players.engineNest import discoverer
from pychess.System import uistuff, cancel_all_tasks
from pychess.widgets import gamewidget
from pychess.widgets import enginesDialog
from pychess.widgets import newGameDialog
from pychess.widgets.newGameDialog import COPY, CLEAR, PASTE, INITIAL
from pychess.widgets import preferencesDialog
from pychess.widgets.discovererDialog import DiscovererDialog
from pychess.perspectives.games import Games
from pychess.perspectives.welcome import Welcome
from pychess.perspectives import perspective_manager

discoverer.pre_discover()


class DialogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        widgets = uistuff.GladeWidgets("PyChess.glade")
        gamewidget.setWidgets(widgets)
        perspective_manager.set_widgets(widgets)

        self.welcome_persp = Welcome()
        perspective_manager.add_perspective(self.welcome_persp)

        self.games_persp = Games()
        perspective_manager.add_perspective(self.games_persp)

    async def asyncTearDown(self):
        self.games_persp.gamewidgets.clear()
        await cancel_all_tasks()

    async def test0(self):
        """Open engines dialogs"""

        # engines dialog
        widgets = gamewidget.getWidgets()
        enginesDialog.run(widgets)
        engines = [item[1] for item in enginesDialog.engine_dialog.allstore]
        self.assertTrue("PyChess.py" in engines)

        widgets["manage_engines_dialog"].hide()

    async def test1(self):
        """Open new game dialog"""

        dialog = newGameDialog.NewGameMode()

        def on_gmwidg_created(persp, gmwidg, event):
            event.set()

        event = asyncio.Event()
        self.games_persp.connect("gmwidg_created", on_gmwidg_created, event)

        dialog.run()
        dialog.widgets["newgamedialog"].response(Gtk.ResponseType.OK)

        await event.wait()

        newGameDialog.NewGameMode.widgets["newgamedialog"].hide()

    async def test2(self):
        """Open setup position dialog"""

        dialog = newGameDialog.SetupPositionExtension()

        def on_gmwidg_created(persp, gmwidg, event):
            event.set()

        event = asyncio.Event()
        self.games_persp.connect("gmwidg_created", on_gmwidg_created, event)

        dialog.run(FEN_START, NORMALCHESS)
        dialog.widgets["newgamedialog"].response(INITIAL)
        dialog.widgets["newgamedialog"].response(COPY)
        dialog.widgets["newgamedialog"].response(CLEAR)
        dialog.widgets["newgamedialog"].response(PASTE)
        dialog.widgets["newgamedialog"].response(Gtk.ResponseType.OK)

        await event.wait()

        newGameDialog.NewGameMode.widgets["newgamedialog"].hide()

    @unittest.skipIf(
        sys.platform == "win32",
        "Windows produces TypeError: could not get a reference to type class\n"
        + "on line: cls.sourcebuffer = GtkSource.Buffer()",
    )
    async def test3(self):
        """Start a new game from enter notation dialog"""

        dialog = newGameDialog.EnterNotationExtension()

        def on_gmwidg_created(persp, gmwidg, event):
            event.set()

        event = asyncio.Event()
        self.games_persp.connect("gmwidg_created", on_gmwidg_created, event)

        dialog.run()
        dialog.sourcebuffer.set_text("1. f3 e5 2. g4 Qh4")
        dialog.widgets["newgamedialog"].response(Gtk.ResponseType.OK)

        await event.wait()

        # Show the firs move of the game
        def on_shown_changed(view, shown, event):
            if shown == 1:
                event.set()

        gmwidg = self.games_persp.gamewidgets.pop()
        view = gmwidg.board.view
        board = gmwidg.gamemodel.boards[1]

        event = asyncio.Event()
        view.connect("shownChanged", on_shown_changed, event)

        view.setShownBoard(board)

        await event.wait()

        newGameDialog.NewGameMode.widgets["newgamedialog"].hide()

    async def test4(self):
        """Open preferences dialog"""

        widgets = gamewidget.getWidgets()
        preferencesDialog.run(widgets)

        notebook = widgets["preferences_notebook"]
        self.assertIsNotNone(preferencesDialog.general_tab)

        notebook.next_page()
        self.assertIsNotNone(preferencesDialog.hint_tab)

        notebook.next_page()
        self.assertIsNotNone(preferencesDialog.theme_tab)

        notebook.next_page()
        self.assertIsNotNone(preferencesDialog.sound_tab)

        notebook.next_page()
        self.assertIsNotNone(preferencesDialog.save_tab)

        widgets["preferences_dialog"].hide()

    async def test5(self):
        """Open engine discoverer dialog"""
        dd = DiscovererDialog(discoverer)

        def on_all_engines_discovered(discoverer, event):
            print("on_all_engines_discovered() OK")
            event.set()

        event = asyncio.Event()
        discoverer.connect("all_engines_discovered", on_all_engines_discovered, event)

        await dd.start()

        await event.wait()

        dd.close()


if __name__ == "__main__":
    unittest.main()
