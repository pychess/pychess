import asyncio
import unittest

from pychess.Utils.const import FEN_START, NORMALCHESS
from pychess.Players.engineNest import discoverer
from pychess.System import uistuff
from pychess.widgets import gamewidget
from pychess.widgets import enginesDialog
from pychess.widgets import newGameDialog
from pychess.widgets import preferencesDialog
from pychess.widgets.discovererDialog import DiscovererDialog
from pychess.perspectives.games import Games
from pychess.perspectives.welcome import Welcome
from pychess.perspectives import perspective_manager


discoverer.pre_discover()


class DialogTests(unittest.TestCase):
    def setUp(self):
        widgets = uistuff.GladeWidgets("PyChess.glade")
        gamewidget.setWidgets(widgets)
        perspective_manager.set_widgets(widgets)

        self.welcome_persp = Welcome()
        perspective_manager.add_perspective(self.welcome_persp)

        self.games_persp = Games()
        perspective_manager.add_perspective(self.games_persp)

    def test1(self):
        """ Open several dialogs """

        enginesDialog.run(gamewidget.getWidgets())

        newGameDialog.SetupPositionExtension.run(FEN_START, NORMALCHESS)

        dd = DiscovererDialog(discoverer)
        self.dd_task = asyncio.async(dd.start())

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


if __name__ == '__main__':
    unittest.main()
