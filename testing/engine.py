import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

from pychess.Players.PyChessCECP import PyChessCECP


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = PyChessCECP()

    @patch("sys.stdout", new_callable=StringIO)
    @patch(
        "pychess.Players.PyChessCECP.get_input",
        new=MagicMock(side_effect=["protover 2", "stop_unittest"]),
    )
    def test1(self, mock_stdout):
        """Send 'protover 2' to PyChess engine"""

        self.engine.run()
        output = mock_stdout.getvalue()

        self.assertTrue(output.endswith("feature done=1\n"))

    @patch("sys.stdout", new_callable=StringIO)
    @patch(
        "pychess.Players.PyChessCECP.get_input",
        new=MagicMock(side_effect=["perft", "stop_unittest"]),
    )
    def test2(self, mock_stdout):
        """Send 'perft' to PyChess engine"""

        self.engine.run()
        output = mock_stdout.getvalue()

        self.assertTrue(output.endswith("nps\n"))

    @patch("sys.stdout", new_callable=StringIO)
    @patch(
        "pychess.Players.PyChessCECP.get_input",
        new=MagicMock(side_effect=["benchmark 2", "stop_unittest"]),
    )
    def test3(self, mock_stdout):
        """Send 'benchmark 2' to PyChess engine"""

        self.engine.run()
        output = mock_stdout.getvalue()

        self.assertTrue(output.endswith("n/s\n"))


if __name__ == "__main__":
    unittest.main()
