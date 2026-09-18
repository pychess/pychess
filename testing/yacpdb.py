import io
import json
from pathlib import Path
import unittest

from pychess.Savers.ChessFile import LoadingError
from pychess.Savers.yacpdb import FORMAT_NAME, FORMAT_VERSION, YACPDBFile


class FakeBoard:
    def __init__(self, fen):
        self.fen = fen

    def asFen(self):
        return self.fen


class FakeVariant:
    def __call__(self, *, setup):
        return FakeBoard(setup)


class FakeModel:
    def __init__(self):
        self.tags = {}
        self.variant = FakeVariant()


def corpus(*puzzles, version=FORMAT_VERSION):
    return {
        "format": FORMAT_NAME,
        "version": version,
        "collection": "example",
        "source_records": len(puzzles),
        "candidate_records": len(puzzles),
        "puzzles": list(puzzles),
    }


def puzzle(**overrides):
    value = {
        "id": 42,
        "authors": ["Example, Composer"],
        "fen": "7k/8/8/8/8/8/1Q6/K7 w - - 0 1",
        "stipulation": "#2",
        "solution": "1.Qb2-b1 !",
        "tree": [{"move": "b2b1", "mark": "!"}],
        "source": {
            "name": "Example Source",
            "date": {"year": 1900, "month": 4, "day": 5},
            "problemid": 12,
        },
        "award": {"distinction": "1st Prize"},
    }
    value.update(overrides)
    return value


def open_corpus(payload):
    return YACPDBFile(io.StringIO(json.dumps(payload)))


class YACPDBFileTest(unittest.TestCase):
    def test_loads_metadata_and_compiled_tree_into_model(self):
        chessfile = open_corpus(corpus(puzzle()))
        self.addCleanup(chessfile.close)

        self.assertEqual(chessfile.collection, "example")
        self.assertEqual(chessfile.count, 1)
        records, _ = chessfile.get_records()
        rec = records[0]
        self.assertEqual(rec["Id"], 42)
        self.assertEqual(rec["White"], "Example, Composer")
        self.assertEqual(rec["Black"], "Mate in 2")
        self.assertEqual(rec["Event"], "Example Source (12)")
        self.assertEqual(rec["Site"], "1st Prize")
        self.assertEqual(rec["Date"], "1900.04.05")

        model = chessfile.loadToModel(rec, 0, FakeModel())
        self.assertEqual(model.tags["FEN"], rec["FEN"])
        self.assertEqual(model.tags["Termination"], "mate in 2")
        self.assertEqual(model.boards[0].asFen(), rec["FEN"])
        self.assertEqual(model.yacpdb_id, 42)
        self.assertEqual(model.authored_solution, "1.Qb2-b1 !")
        self.assertEqual(
            [node.uci for node in model.authored_solution_tree.real_children()],
            ["b2b1"],
        )

    def test_handles_partial_and_historical_source_dates(self):
        with self.subTest("year and month"):
            rec = open_corpus(
                corpus(
                    puzzle(
                        source={"name": "Source", "date": {"year": 1900, "month": 4}}
                    )
                )
            ).games[0]
            self.assertEqual(rec["Date"], "1900.04")

        with self.subTest("historical year range"):
            rec = open_corpus(
                corpus(puzzle(source={"name": None, "date": {"year": "1900-1901"}}))
            ).games[0]
            self.assertEqual(rec["Event"], "YACPDB #42")
            self.assertEqual(rec["Date"], "1900-1901")

    def test_rejects_unknown_format_version(self):
        with self.assertRaisesRegex(LoadingError, "version"):
            open_corpus(corpus(puzzle(), version=FORMAT_VERSION + 1))

    def test_rejects_invalid_compiled_tree_when_puzzle_is_loaded(self):
        chessfile = open_corpus(corpus(puzzle(tree=[{"move": "Qb1"}])))
        self.addCleanup(chessfile.close)
        with self.assertRaisesRegex(LoadingError, "YACPDB #42"):
            chessfile.loadToModel(chessfile.games[0], 0, FakeModel())

    def test_golden_issue_1862_tree_is_available_at_runtime(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "learn"
            / "puzzles"
            / "loyd.yacpdb.json"
        )
        with path.open(encoding="utf-8") as handle:
            chessfile = YACPDBFile(handle)
        rec = next(rec for rec in chessfile.games if rec["YACPDBId"] == 47462)
        model = chessfile.loadToModel(rec, 0, FakeModel())

        self.assertEqual(model.yacpdb_id, 47462)
        self.assertEqual(model.authored_solution_tree.real_children()[0].uci, "h6h1")


if __name__ == "__main__":
    unittest.main()
