import json
from pathlib import Path
import tempfile
import unittest

from utilities.yacpdb_build import (
    FORMAT_NAME,
    FORMAT_VERSION,
    build_corpus,
    collection_name,
    write_corpus,
)


def entry(problem_id, *, solution="1.Qb2-b1 !", stipulation="#2"):
    return {
        "id": problem_id,
        "authors": ["Example, Composer"],
        "source": {
            "name": "Example Source",
            "date": {"year": 1900},
            "problemid": 12,
        },
        "award": {"distinction": "1st Prize"},
        "algebraic": {
            "white": ["Ka1", "Qb2"],
            "black": ["Kh8"],
        },
        "stipulation": stipulation,
        "solution": solution,
    }


class YacpdbBuildTest(unittest.TestCase):
    def test_collection_name_comes_from_snapshot_filename(self):
        self.assertEqual(collection_name(Path("loyd-yacpdb.json")), "loyd")
        with self.assertRaisesRegex(ValueError, "input filename must end"):
            collection_name(Path("loyd.json"))

    def test_build_corpus_keeps_only_fully_compiled_core_candidates(self):
        corpus, counts, failures = build_corpus(
            [
                entry(30),
                entry(10),
                entry(20, solution="1.Qb2-z9 !"),
                entry(40, stipulation="+"),
            ],
            collection="example",
        )

        self.assertEqual(corpus["format"], FORMAT_NAME)
        self.assertEqual(corpus["version"], FORMAT_VERSION)
        self.assertEqual(corpus["collection"], "example")
        self.assertEqual(corpus["source_records"], 4)
        self.assertEqual(corpus["candidate_records"], 3)
        self.assertEqual([puzzle["id"] for puzzle in corpus["puzzles"]], [10, 30])
        self.assertEqual(counts["compiled"], 2)
        self.assertEqual(counts["failed"], 1)
        self.assertEqual(counts["excluded"], 1)
        self.assertEqual(failures[0][0], 20)
        self.assertEqual(failures[0][1], "unsupported-syntax")

        puzzle = corpus["puzzles"][0]
        self.assertEqual(puzzle["authors"], ["Example, Composer"])
        self.assertEqual(puzzle["fen"], "7k/8/8/8/8/8/1Q6/K7 w - - 0 1")
        self.assertEqual(puzzle["stipulation"], "#2")
        self.assertEqual(puzzle["source"]["name"], "Example Source")
        self.assertEqual(puzzle["award"]["distinction"], "1st Prize")
        self.assertEqual(puzzle["tree"][0]["move"], "b2b1")

    def test_generated_json_is_compact_deterministic_utf8(self):
        corpus, _, _ = build_corpus([entry(1)], collection="example")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "example.yacpdb.json"
            write_corpus(path, corpus)
            first = path.read_bytes()
            write_corpus(path, corpus)
            second = path.read_bytes()

        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))
        self.assertNotIn(b": ", first)
        self.assertEqual(first.count(b"\n"), len(corpus["puzzles"]) + 2)
        decoded = json.loads(first)
        self.assertEqual(decoded, corpus)


if __name__ == "__main__":
    unittest.main()
