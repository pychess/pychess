#!/usr/bin/env python3
"""Build deterministic packaged PyChess puzzle corpora from YACPDB snapshots.

The inputs are raw JSON arrays previously downloaded with ``yacpdb_probe.py``.
Only records accepted by the probe's core-candidate rules and whose complete
solution text compiles successfully are emitted.  Runtime PyChess therefore
never needs network access to YACPDB.

Example::

    python3 utilities/yacpdb_build.py \
        ~/.cache/pychess/yacpdb/*-yacpdb.json \
        --output-dir learn/puzzles
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

if __package__:
    from .yacpdb_probe import classify, entry_fen, entry_id, solution_failure_category
else:
    from yacpdb_probe import classify, entry_fen, entry_id, solution_failure_category

FORMAT_NAME = "pychess-yacpdb"
FORMAT_VERSION = 1
INPUT_SUFFIX = "-yacpdb.json"
OUTPUT_SUFFIX = ".yacpdb.json"


def _repo_lib() -> Path:
    return Path(__file__).resolve().parents[1] / "lib"


def _load_solution_compiler():
    repo_lib = str(_repo_lib())
    if repo_lib not in sys.path:
        sys.path.insert(0, repo_lib)

    from pychess.Savers.yacpdb_solution import (  # noqa: PLC0415
        SolutionParseError,
        parse_solution,
        solution_tree_to_data,
    )

    return SolutionParseError, parse_solution, solution_tree_to_data


def collection_name(path: Path) -> str:
    if not path.name.endswith(INPUT_SUFFIX):
        raise ValueError(f"input filename must end with {INPUT_SUFFIX!r}: {path}")
    return path.name[: -len(INPUT_SUFFIX)]


def load_snapshot(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, list) or not all(
        isinstance(entry, dict) for entry in payload
    ):
        raise ValueError(f"{path} must contain a JSON array of problem objects")
    return payload


def _copy_json_object(value: object, *, field: str) -> dict[str, Any] | None:
    if value in (None, {}, ""):
        return None
    if not isinstance(value, dict):
        raise ValueError(f"YACPDB {field} must be an object when present")
    # JSON round-tripping guarantees the generated corpus does not retain any
    # mutable objects owned by the source snapshot.
    return json.loads(json.dumps(value, ensure_ascii=False))


def build_record(entry: dict[str, Any]) -> dict[str, Any]:
    problem_id = entry_id(entry)
    if problem_id is None:
        raise ValueError("core candidate has no stable positive YACPDB ID")

    authors = entry.get("authors")
    if (
        not isinstance(authors, list)
        or not authors
        or not all(isinstance(author, str) and author.strip() for author in authors)
    ):
        raise ValueError(f"YACPDB #{problem_id} has no usable authors list")

    stipulation = entry.get("stipulation")
    solution = entry.get("solution")
    assert isinstance(stipulation, str)
    assert isinstance(solution, str)

    SolutionParseError, parse_solution, solution_tree_to_data = (
        _load_solution_compiler()
    )
    fen = entry_fen(entry)
    try:
        tree = parse_solution(solution, fen)
    except SolutionParseError:
        raise

    record: dict[str, Any] = {
        "id": problem_id,
        "authors": list(authors),
        "fen": fen,
        "stipulation": stipulation,
        "solution": solution,
        "tree": solution_tree_to_data(tree),
    }

    source = _copy_json_object(entry.get("source"), field="source")
    if source is not None:
        record["source"] = source
    award = _copy_json_object(entry.get("award"), field="award")
    if award is not None:
        record["award"] = award
    return record


def build_corpus(
    entries: list[dict[str, Any]], *, collection: str
) -> tuple[dict[str, Any], Counter[str], list[tuple[int | None, str, str]]]:
    SolutionParseError, _, _ = _load_solution_compiler()
    counts: Counter[str] = Counter(source_records=len(entries))
    failures: list[tuple[int | None, str, str]] = []
    records: list[dict[str, Any]] = []

    for entry in entries:
        if "candidate" not in classify(entry):
            counts["excluded"] += 1
            continue
        counts["candidates"] += 1
        try:
            record = build_record(entry)
        except (SolutionParseError, ValueError) as exc:
            category = solution_failure_category(str(exc))
            counts["failed"] += 1
            counts[category] += 1
            failures.append((entry_id(entry), category, str(exc)))
            continue
        records.append(record)
        counts["compiled"] += 1

    records.sort(key=lambda record: record["id"])
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"collection {collection!r} contains duplicate YACPDB IDs")

    corpus = {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "collection": collection,
        "source_records": counts["source_records"],
        "candidate_records": counts["candidates"],
        "puzzles": records,
    }
    return corpus, counts, failures


def write_corpus(path: Path, corpus: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(corpus, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help=f"raw YACPDB snapshots named *{INPUT_SUFFIX}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory for generated *.yacpdb.json corpora",
    )
    parser.add_argument(
        "--show-failures",
        type=int,
        default=0,
        help="show the first N skipped candidate compiler failures per collection",
    )
    args = parser.parse_args(argv)
    if args.show_failures < 0:
        parser.error("--show-failures cannot be negative")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    seen_collections: set[str] = set()
    total: Counter[str] = Counter()

    for input_path in sorted(args.inputs):
        try:
            collection = collection_name(input_path)
            if collection in seen_collections:
                raise ValueError(f"duplicate collection name {collection!r}")
            seen_collections.add(collection)
            entries = load_snapshot(input_path)
            corpus, counts, failures = build_corpus(entries, collection=collection)
            output_path = args.output_dir / f"{collection}{OUTPUT_SUFFIX}"
            write_corpus(output_path, corpus)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        total.update(counts)
        print(
            f"{collection:12} source={counts['source_records']:4} "
            f"candidates={counts['candidates']:4} compiled={counts['compiled']:4} "
            f"failed={counts['failed']:3} -> {output_path}"
        )
        for problem_id, category, message in failures[: args.show_failures]:
            print(f"  #{problem_id or '?'} [{category}] {message}")

    print(
        "total        "
        f"source={total['source_records']:4} candidates={total['candidates']:4} "
        f"compiled={total['compiled']:4} failed={total['failed']:3}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
