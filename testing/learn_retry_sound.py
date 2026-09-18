import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pychess.widgets.LearnInfoBar import LearnInfoBar
from pychess.widgets import preferencesDialog


class LearnRetrySoundTest(unittest.TestCase):
    @staticmethod
    def _infobar(puzzle_game):
        return SimpleNamespace(
            gamemodel=SimpleNamespace(
                puzzle_game=puzzle_game,
                practice_game=False,
                status=None,
            ),
            boardcontrol=SimpleNamespace(game_preview=False),
            content_area=SimpleNamespace(add=Mock()),
            clear=Mock(),
            set_message_type=Mock(),
            add_button=Mock(),
            set_response_sensitive=Mock(),
            show_all=Mock(),
        )

    def test_puzzle_retry_plays_invalid_move_sound(self):
        infobar = self._infobar(True)
        with (
            patch("pychess.widgets.LearnInfoBar.Gtk.Label", return_value=object()),
            patch.object(preferencesDialog.SoundTab, "playAction") as play_action,
        ):
            LearnInfoBar.retry(infobar)

        play_action.assert_called_once_with("invalidMove")
        self.assertTrue(infobar.boardcontrol.game_preview)

    def test_non_puzzle_retry_does_not_play_invalid_move_sound(self):
        infobar = self._infobar(False)
        with (
            patch("pychess.widgets.LearnInfoBar.Gtk.Label", return_value=object()),
            patch.object(preferencesDialog.SoundTab, "playAction") as play_action,
        ):
            LearnInfoBar.retry(infobar)

        play_action.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
