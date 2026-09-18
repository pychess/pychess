import io
import json
from pathlib import Path
import unittest

from pychess.Savers.ChessFile import LoadingError
from pychess.Savers.yacpdb import FORMAT_NAME, FORMAT_VERSION, YACPDBFile
from pychess.Savers.yacpdb_solution import (
    direct_solution_children,
    playable_solution_moves,
    solution_nodes_after_moves,
)


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


PACKAGED_CORPUS_DIR = Path(__file__).resolve().parents[1] / "learn" / "puzzles"
PACKAGED_COLLECTIONS = {
    "alekhine",
    "baird",
    "benko",
    "bron",
    "cheron",
    "dawson",
    "horwitz",
    "kubbel",
    "lasker",
    "loyd",
    "mansfield",
    "reti",
    "troicki",
    "vukcevich",
}
PACKAGED_PUZZLE_COUNT = 5338


def load_packaged_puzzle(collection, problem_id):
    path = PACKAGED_CORPUS_DIR / f"{collection}.yacpdb.json"
    with path.open(encoding="utf-8") as handle:
        chessfile = YACPDBFile(handle)
    try:
        rec = next(rec for rec in chessfile.games if rec["YACPDBId"] == problem_id)
        return chessfile.loadToModel(rec, 0, FakeModel())
    finally:
        chessfile.close()


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

    def test_all_packaged_composer_collections_load(self):
        self.assertEqual(list(PACKAGED_CORPUS_DIR.glob("*.olv")), [])
        paths = sorted(PACKAGED_CORPUS_DIR.glob("*.yacpdb.json"))
        self.assertEqual(
            {path.name for path in paths},
            {f"{collection}.yacpdb.json" for collection in PACKAGED_COLLECTIONS},
        )

        total = 0
        for path in paths:
            with self.subTest(collection=path.stem):
                with path.open(encoding="utf-8") as handle:
                    chessfile = YACPDBFile(handle)
                try:
                    self.assertIn(chessfile.collection, PACKAGED_COLLECTIONS)
                    self.assertGreater(chessfile.count, 0)
                    total += chessfile.count
                    for rec in chessfile.games:
                        model = chessfile.loadToModel(rec, 0, FakeModel())
                        self.assertTrue(
                            playable_solution_moves([model.authored_solution_tree])
                        )
                finally:
                    chessfile.close()

        self.assertEqual(total, PACKAGED_PUZZLE_COUNT)

    def test_golden_issue_1862_tree_is_available_at_runtime(self):
        model = load_packaged_puzzle("loyd", 47462)
        tree = model.authored_solution_tree

        self.assertEqual(model.yacpdb_id, 47462)
        self.assertEqual(playable_solution_moves([tree]), ["h6h1"])

        key = tree.real_children()[0]
        self.assertEqual(
            {node.uci for node in direct_solution_children([key])},
            {"g7g6", "g7f7", "g8f7"},
        )

        threat = solution_nodes_after_moves(tree, ["h6h1", "g7g6", "e4g6", "g8h8"])
        self.assertEqual(len(threat), 1)
        self.assertEqual(threat[0].kind, "threat")
        self.assertEqual(playable_solution_moves(threat), ["h1h7"])

    def test_packaged_set_play_is_retained_but_not_offered_as_the_key(self):
        model = load_packaged_puzzle("baird", 1120)
        tree = model.authored_solution_tree

        self.assertEqual(tree.children[0].kind, "set")
        self.assertEqual(
            {node.uci for node in tree.children[0].real_children()},
            {"e4e3", "e4f4"},
        )
        self.assertEqual(playable_solution_moves([tree]), ["c7b5"])

    def test_packaged_try_is_retained_but_not_offered_as_the_key(self):
        model = load_packaged_puzzle("baird", 1067)
        tree = model.authored_solution_tree

        self.assertEqual(playable_solution_moves([tree]), ["d1a1"])
        self.assertEqual(
            {node.uci for node in tree.real_children(include_tries=True)},
            {"d1c1", "d1a1"},
        )
        tried = next(node for node in tree.children if node.uci == "d1c1")
        self.assertTrue(tried.is_try)
        self.assertEqual(
            [node.uci for node in tried.children if node.is_refutation], ["e3d2"]
        )

    def test_packaged_promotion_continuation_is_preserved(self):
        model = load_packaged_puzzle("baird", 1134)
        tree = model.authored_solution_tree

        nodes = solution_nodes_after_moves(tree, ["d1d2", "e5d6", "c7c8q"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].uci, "c7c8q")

    def test_packaged_castling_keys_are_preserved(self):
        kingside = load_packaged_puzzle("dawson", 41070)
        queenside = load_packaged_puzzle("dawson", 41069)

        self.assertEqual(
            playable_solution_moves([kingside.authored_solution_tree]), ["O-O"]
        )
        self.assertEqual(
            playable_solution_moves([queenside.authored_solution_tree]), ["O-O-O"]
        )

    def test_old_manual_loyd_hint_is_available_from_authored_tree(self):
        model = load_packaged_puzzle("loyd", 15311)

        self.assertEqual(
            playable_solution_moves([model.authored_solution_tree]), ["g2h1"]
        )


if __name__ == "__main__":
    unittest.main()
