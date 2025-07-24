import asyncio
import sys
import unittest

modules_to_test = (
    "Board",
    "alphabeta",
    "bitboard",
    "database",
    "draw",
    "eval",
    "fen",
    "frc_castling",
    "frc_movegen",
    "move",
    "movegen",
    "pgn",
    "atomic",
    "crazyhouse",
    "losers",
    "seirawan",
    "sittuyin",
    "placement",
    "suicide",
    "zobrist",
    "polyglot",
    "ficsmanagers",
    "ficsplay",
    "ficsobserve",
    "ficslecturebot",
    "ficspuzzlebot",
    "analysis",
    "selfplay",
    "engine",
    "savegame",
    "dialogs",
    "learn",
    "remotegame",
)


def suite():
    tests = unittest.TestSuite()
    for module in map(__import__, modules_to_test):
        tests.addTest(unittest.defaultTestLoader.loadTestsFromModule(module))
    return tests


if __name__ == "__main__":
    # Python >=3.14 does not auto-create an asyncio event loop for us
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    ret = unittest.TextTestRunner(verbosity=2).run(suite())
    if ret.wasSuccessful():
        sys.exit(0)
    sys.exit(1)
