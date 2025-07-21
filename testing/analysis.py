import asyncio
import unittest

from pychess.Utils.const import WHITE, ANALYZING, INVERSE_ANALYZING
from pychess.Utils.lutils.ldata import MATE_VALUE
from pychess.Utils.Board import Board
from pychess.Players.CECPEngine import CECPEngine

from queue import Queue

from gi.repository import GObject


class DummyCECPAnalyzerEngine(GObject.GObject):
    __gsignals__ = {
        "line": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "died": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.defname = "Dummy"
        self.Q = Queue()

    async def putline(self, line):
        self.emit("line", line)
        await asyncio.sleep(0)

    def write(self, text):
        if text.strip() == "protover 2":
            self.emit(
                "line", "feature setboard=1 analyze=1 ping=1 draw=0 sigint=0 done=1"
            )
        pass

    def readline(self):
        return self.Q.get()


class EmittingTestCase(unittest.TestCase):
    def __init__(self, methodName="runTest"):
        unittest.TestCase.__init__(self, methodName)
        self.args = {}

    def traceSignal(self, object, signal):
        self.args[object] = None

        def handler(manager, *args):
            self.args[object] = args

        object.connect(signal, handler)

    def getSignalResults(self, object):
        return self.args.get(object, None)


class CECPTests(EmittingTestCase):
    def _setupengine(self, mode):
        engine = DummyCECPAnalyzerEngine()
        analyzer = CECPEngine(engine, WHITE, 2, 0)

        def optionsCallback(engine):
            analyzer.setOptionAnalyzing(mode)

        analyzer.connect("readyForOptions", optionsCallback)
        analyzer.prestart()
        analyzer.start(asyncio.Event(), set())

        return engine, analyzer

    async def _testLine(
        self, engine, analyzer, board, analine, ply, moves, score, depth, nps
    ):
        self.traceSignal(analyzer, "analyze")
        await engine.putline(analine)
        results = self.getSignalResults(analyzer)
        self.assertNotEqual(results, None, "signal wasn't sent")
        self.assertEqual(results, ([(ply, moves, score, depth, nps)],))

    def setUp(self):
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.engineA, self.analyzerA = self._setupengine(ANALYZING)
        self.engineI, self.analyzerI = self._setupengine(INVERSE_ANALYZING)

    def test1(self):
        """Test analyzing in forced mate situations"""

        board = Board("B1n1n1KR/1r5B/6R1/2b1p1p1/2P1k1P1/1p2P2p/1P2P2P/3N1N2 w - - 0 1")
        self.analyzerA.setBoardList([board], [])
        self.analyzerI.setBoardList([board], [])

        async def coro():
            await self._testLine(
                self.engineA,
                self.analyzerA,
                board,
                "1. Mat1 0 1     Bxb7#",
                0,
                ["Bxb7#"],
                MATE_VALUE,
                "1.",
                "",
            )

            # Notice, in the opposite situation there is no forced mate. Black can
            # do Bxe3 or Ne7+, but we just emulate a stupid analyzer not
            # recognizing this.
            await self._testLine(
                self.engineI,
                self.analyzerI,
                board.switchColor(),
                "10. -Mat 2 35 64989837     Bd4 Bxb7#",
                0,
                ["Bd4", "Bxb7#"],
                -MATE_VALUE,
                "10.",
                "185685248",
            )

        self.loop.run_until_complete(coro())

    def test2(self):
        """Test analyzing in promotion situations"""

        board = Board("5k2/PK6/8/8/8/6P1/6P1/8 w - - 1 48")
        self.analyzerA.setBoardList([board], [])
        self.analyzerI.setBoardList([board], [])

        async def coro():
            await self._testLine(
                self.engineA,
                self.analyzerA,
                board,
                "9. 1833 23 43872584     a8=Q+ Kf7 Qa2+ Kf6 Qd2 Kf5 g4+",
                94,
                ["a8=Q+", "Kf7", "Qa2+", "Kf6", "Qd2", "Kf5", "g4+"],
                1833,
                "9.",
                "190750365",
            )

            await self._testLine(
                self.engineI,
                self.analyzerI,
                board.switchColor(),
                "10. -1883 59 107386433     Kf7 a8=Q Ke6 Qa6+ Ke5 Qd6+ Kf5",
                94,
                ["Kf7", "a8=Q", "Ke6", "Qa6+", "Ke5", "Qd6+", "Kf5"],
                -1883,
                "10.",
                "182010903",
            )

        self.loop.run_until_complete(coro())


if __name__ == "__main__":
    unittest.main()
