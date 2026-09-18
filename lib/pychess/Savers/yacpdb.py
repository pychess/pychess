"""Load generated YACPDB composition collections for Learn puzzles.

The packaged ``*.yacpdb.json`` files are generated offline by
``utilities/yacpdb_build.py``.  Runtime PyChess only reads those files; it does
not contact YACPDB or recompile the original solution notation.
"""

from __future__ import annotations

import json
import re

from .ChessFile import ChessFile, LoadingError
from .yacpdb_solution import solution_tree_from_data
from pychess.Utils.const import WAITING_TO_START

FORMAT_NAME = "pychess-yacpdb"
FORMAT_VERSION = 1
_DIRECT_MATE_RE = re.compile(r"^#([1-9][0-9]*)$")


def load(handle):
    return YACPDBFile(handle)


class YACPDBFile(ChessFile):
    """Reader for the generated, runtime-safe YACPDB puzzle corpus."""

    def __init__(self, handle):
        super().__init__(handle)
        try:
            payload = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LoadingError(f"Invalid YACPDB puzzle corpus: {exc}") from exc

        if not isinstance(payload, dict):
            raise LoadingError("YACPDB puzzle corpus must be a JSON object")
        if payload.get("format") != FORMAT_NAME:
            raise LoadingError("Unsupported YACPDB puzzle corpus format")
        if payload.get("version") != FORMAT_VERSION:
            raise LoadingError(
                f"Unsupported YACPDB puzzle corpus version {payload.get('version')!r}"
            )

        collection = payload.get("collection")
        if not isinstance(collection, str) or not collection:
            raise LoadingError("YACPDB puzzle corpus has no collection name")
        self.collection = collection

        puzzles = payload.get("puzzles")
        if not isinstance(puzzles, list):
            raise LoadingError("YACPDB puzzle corpus has no puzzles list")

        self.games = [self._record(puzzle) for puzzle in puzzles]
        self.count = len(self.games)

    @staticmethod
    def _record(puzzle):
        if not isinstance(puzzle, dict):
            raise LoadingError("YACPDB puzzle record must be an object")

        problem_id = puzzle.get("id")
        if not isinstance(problem_id, int) or problem_id <= 0:
            raise LoadingError("YACPDB puzzle record has no valid problem ID")

        authors = puzzle.get("authors")
        if (
            not isinstance(authors, list)
            or not authors
            or not all(isinstance(author, str) and author for author in authors)
        ):
            raise LoadingError(f"YACPDB #{problem_id} has no valid authors list")

        fen = puzzle.get("fen")
        solution = puzzle.get("solution")
        tree = puzzle.get("tree")
        stipulation = puzzle.get("stipulation")
        mate_match = (
            _DIRECT_MATE_RE.fullmatch(stipulation)
            if isinstance(stipulation, str)
            else None
        )
        if not isinstance(fen, str) or not fen:
            raise LoadingError(f"YACPDB #{problem_id} has no valid FEN")
        if not isinstance(solution, str) or not solution:
            raise LoadingError(f"YACPDB #{problem_id} has no authored solution")
        if not isinstance(tree, list):
            raise LoadingError(f"YACPDB #{problem_id} has no compiled solution tree")
        if mate_match is None:
            raise LoadingError(
                f"YACPDB #{problem_id} has unsupported stipulation {stipulation!r}"
            )

        mate_in = int(mate_match.group(1))
        source = puzzle.get("source")
        event = f"YACPDB #{problem_id}"
        date = ""
        if isinstance(source, dict):
            source_name = source.get("name")
            if source_name not in (None, ""):
                event = str(source_name)
            source_id = source.get("problemid")
            if source_id not in (None, ""):
                event = f"{event} ({source_id})"
            date = YACPDBFile._source_date(source.get("date"))

        site = ""
        award = puzzle.get("award")
        if isinstance(award, dict):
            distinction = award.get("distinction")
            if isinstance(distinction, str):
                site = distinction

        return {
            "Id": problem_id,
            "Offset": 0,
            "White": " - ".join(authors),
            "Black": f"Mate in {mate_in}",
            "Event": event,
            "Site": site,
            "Date": date,
            "FEN": fen,
            "Termination": f"mate in {mate_in}",
            "YACPDBId": problem_id,
            "Solution": solution,
            "SolutionTree": tree,
        }

    @staticmethod
    def _source_date(value):
        if not isinstance(value, dict):
            return ""
        year = value.get("year")
        month = value.get("month")
        day = value.get("day")
        if year in (None, ""):
            return ""
        if isinstance(month, int) and isinstance(day, int):
            return f"{year}.{month:02d}.{day:02d}"
        if isinstance(month, int):
            return f"{year}.{month:02d}"
        return str(year)

    def loadToModel(self, rec, position, model=None):
        if model is None:
            from pychess.Utils.GameModel import GameModel  # noqa: PLC0415

            model = GameModel()

        model.tags["Event"] = rec["Event"]
        model.tags["Site"] = rec["Site"]
        model.tags["Date"] = rec["Date"]
        model.tags["Round"] = ""
        model.tags["White"] = "?"
        model.tags["Black"] = "?"
        model.tags["Termination"] = rec["Termination"]
        model.tags["FEN"] = rec["FEN"]

        model.boards = [model.variant(setup=rec["FEN"])]
        model.variations = [model.boards]
        model.status = WAITING_TO_START

        # Runtime Learn play consumes this compiled tree for authored move
        # validation and, in later Phase D steps, authored defender replies
        # and hints.
        try:
            model.authored_solution_tree = solution_tree_from_data(rec["SolutionTree"])
        except ValueError as exc:
            raise LoadingError(
                f"Invalid compiled solution tree for YACPDB #{rec['YACPDBId']}: {exc}"
            ) from exc
        model.authored_solution = rec["Solution"]
        model.yacpdb_id = rec["YACPDBId"]

        return model
