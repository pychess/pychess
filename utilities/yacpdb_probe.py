#!/usr/bin/env python3
"""Probe current YACPDB data for a PyChess puzzle-corpus refresh.

This is a maintainer utility. It discovers records through YACPDB's public
Query Language gateway and then fetches the complete JSON record for every
returned ID. It does not modify PyChess's packaged puzzle corpus.

Examples::

    python3 utilities/yacpdb_probe.py --composer "Loyd, Samuel"
    python3 utilities/yacpdb_probe.py --query 'Id("12345")' --show 1
    python3 utilities/yacpdb_probe.py --composer "Loyd, Samuel" \
        --output /tmp/loyd-yacpdb.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

QL_URL = "https://yacpdb.org/gateway/ql"
ENTRY_URL = "https://www.yacpdb.org/json.php"
USER_AGENT = "PyChess YACPDB corpus probe (+https://github.com/pychess/pychess)"
DIRECT_MATE_RE = re.compile(r"^#([1-9][0-9]*)$")
ORTHODOX_PIECE_RE = re.compile(r"^[KQRBSP][a-h][1-8]$")


def default_cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base) / "pychess" / "yacpdb"
    return Path.home() / ".cache" / "pychess" / "yacpdb"


def quote_ql_string(value: str) -> str:
    """Quote a string for use inside YACPDB's QL syntax."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def composer_query(composer: str) -> str:
    return f'Author("{quote_ql_string(composer)}%")'


def request_json(url: str, *, timeout: float) -> Any:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON returned by {url}") from exc


def fetch_query(query: str, *, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = f"{QL_URL}?{urlencode({'q': query})}"
    payload = request_json(url, timeout=timeout)
    if not isinstance(payload, dict):
        raise RuntimeError("YACPDB QL response is not a JSON object")
    if not payload.get("success"):
        raise RuntimeError(f"YACPDB QL query failed: {payload!r}")

    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("YACPDB QL response has no result object")
    entries = result.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("YACPDB QL response has no result.entries list")

    normalized = [entry for entry in entries if isinstance(entry, dict)]
    metadata = {key: value for key, value in result.items() if key != "entries"}
    return normalized, metadata


def entry_id(entry: dict[str, Any]) -> int | None:
    value = entry.get("id")
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def load_cached_entry(cache_dir: Path, problem_id: int) -> dict[str, Any] | None:
    path = cache_dir / f"{problem_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def save_cached_entry(cache_dir: Path, problem_id: int, entry: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{problem_id}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")


def fetch_entry(
    problem_id: int,
    *,
    timeout: float,
    cache_dir: Path,
    refresh: bool,
    delay: float,
) -> tuple[dict[str, Any] | None, bool]:
    """Return (entry, from_cache)."""
    if not refresh:
        cached = load_cached_entry(cache_dir, problem_id)
        if cached is not None:
            return cached, True

    url = f"{ENTRY_URL}?{urlencode({'entry': '', 'id': problem_id})}"
    data = request_json(url, timeout=timeout)
    if delay:
        time.sleep(delay)
    if not isinstance(data, dict) or not data:
        return None, False

    save_cached_entry(cache_dir, problem_id, data)
    return data, False


def position_pieces(entry: dict[str, Any]) -> tuple[list[str], list[str]] | None:
    algebraic = entry.get("algebraic")
    if not isinstance(algebraic, dict):
        return None
    white = algebraic.get("white")
    black = algebraic.get("black")
    if not isinstance(white, list) or not isinstance(black, list):
        return None
    if not all(isinstance(piece, str) for piece in white + black):
        return None
    return white, black


def classify(entry: dict[str, Any]) -> tuple[str, ...]:
    """Return factual traits useful for deciding what PyChess can package.

    This intentionally reports rather than guesses about YACPDB options and
    legends. The first refresh should tell us which of those occur in otherwise
    orthodox direct mates before we turn them into rejection rules.
    """
    traits: list[str] = []

    stipulation = entry.get("stipulation")
    if not isinstance(stipulation, str) or not DIRECT_MATE_RE.fullmatch(stipulation):
        traits.append("not-direct-mate")

    pieces = position_pieces(entry)
    if pieces is None:
        traits.append("invalid-position")
    else:
        white, black = pieces
        if not all(ORTHODOX_PIECE_RE.fullmatch(piece) for piece in white + black):
            traits.append("non-orthodox-piece")
        if sum(piece.startswith("K") for piece in white) != 1:
            traits.append("white-king-count")
        if sum(piece.startswith("K") for piece in black) != 1:
            traits.append("black-king-count")

    solution = entry.get("solution")
    if not isinstance(solution, str) or not solution.strip():
        traits.append("missing-solution")

    options = entry.get("options")
    if isinstance(options, list) and options:
        traits.append("has-options")
    elif options not in (None, [], ""):
        traits.append("has-options")

    legend = entry.get("legend")
    if isinstance(legend, dict) and legend:
        traits.append("has-legend")
    elif isinstance(legend, list) and legend:
        traits.append("has-legend")
    elif legend not in (None, {}, [], ""):
        traits.append("has-legend")

    core_failures = {
        "not-direct-mate",
        "invalid-position",
        "non-orthodox-piece",
        "white-king-count",
        "black-king-count",
        "missing-solution",
    }
    if not core_failures.intersection(traits):
        traits.insert(0, "candidate")

    return tuple(traits)


def fetch_entries(
    ids: list[int],
    *,
    jobs: int,
    timeout: float,
    cache_dir: Path,
    refresh: bool,
    delay: float,
) -> tuple[list[dict[str, Any]], int, int]:
    entries: list[dict[str, Any]] = []
    cache_hits = 0
    failures = 0

    def one(problem_id: int) -> tuple[int, dict[str, Any] | None, bool]:
        try:
            entry, from_cache = fetch_entry(
                problem_id,
                timeout=timeout,
                cache_dir=cache_dir,
                refresh=refresh,
                delay=delay,
            )
        except RuntimeError as exc:
            print(f"warning: YACPDB #{problem_id}: {exc}", file=sys.stderr)
            return problem_id, None, False
        return problem_id, entry, from_cache

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(one, problem_id): problem_id for problem_id in ids}
        for future in as_completed(futures):
            problem_id, entry, from_cache = future.result()
            if entry is None:
                failures += 1
                continue
            entry.setdefault("id", problem_id)
            entries.append(entry)
            cache_hits += int(from_cache)

    entries.sort(key=lambda entry: entry_id(entry) or 0)
    return entries, cache_hits, failures


def print_summary(
    *,
    query: str,
    gateway_entries: list[dict[str, Any]],
    metadata: dict[str, Any],
    entries: list[dict[str, Any]],
    cache_hits: int,
    failures: int,
    show: int,
) -> None:
    ids = [problem_id for entry in gateway_entries if (problem_id := entry_id(entry))]
    traits = Counter(trait for entry in entries for trait in classify(entry))

    print(f"QL query: {query}")
    print(f"Gateway entries: {len(gateway_entries)}")
    print(f"Gateway entries with IDs: {len(ids)}")
    if metadata:
        print("Gateway metadata:")
        print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Gateway metadata: (none returned)")
    print(f"Full records fetched: {len(entries)}")
    print(f"Cache hits: {cache_hits}")
    print(f"Fetch failures: {failures}")
    print()
    print("Record traits:")
    for trait, count in sorted(traits.items()):
        print(f"  {trait:22} {count}")

    candidates = [entry for entry in entries if "candidate" in classify(entry)]
    print(f"\nCore PyChess candidates: {len(candidates)}")
    print(
        "  (direct #N + orthodox 8x8 pieces + one king each + non-empty solution;"
        " options/legend are reported but not rejected yet)"
    )

    for entry in candidates[:show]:
        problem_id = entry_id(entry)
        authors = entry.get("authors") or []
        if isinstance(authors, list):
            author_text = ", ".join(str(author) for author in authors)
        else:
            author_text = str(authors)
        source = entry.get("source") or ""
        print(
            f"\n#{problem_id}  {entry.get('stipulation', '?')}  "
            f"{author_text or '(unknown author)'}"
        )
        if source:
            print(f"  source: {source}")
        solution = str(entry.get("solution") or "").strip().replace("\n", " ")
        if solution:
            suffix = "..." if len(solution) > 180 else ""
            print(f"  solution: {solution[:180]}{suffix}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--composer",
        help='composer name for a YACPDB Author(...) query, e.g. "Loyd, Samuel"',
    )
    source.add_argument("--query", help="raw YACPDB Query Language expression")
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="fetch only the first N IDs (useful for a quick API probe)",
    )
    parser.add_argument("--show", type=int, default=3, help="show N candidate samples")
    parser.add_argument("--jobs", type=int, default=4, help="parallel full-record requests")
    parser.add_argument("--delay", type=float, default=0.05, help="delay after each live request")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=default_cache_dir(),
        help="full-record cache directory",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="ignore cached full records and fetch them again",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write fetched full records as UTF-8 JSON for inspection",
    )
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if args.max_records is not None and args.max_records < 1:
        parser.error("--max-records must be at least 1")
    if args.show < 0:
        parser.error("--show cannot be negative")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    query = args.query or composer_query(args.composer)

    try:
        gateway_entries, metadata = fetch_query(query, timeout=args.timeout)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    ids = sorted(
        {
            problem_id
            for entry in gateway_entries
            if (problem_id := entry_id(entry)) is not None
        }
    )
    if args.max_records is not None:
        ids = ids[: args.max_records]

    if not ids:
        print_summary(
            query=query,
            gateway_entries=gateway_entries,
            metadata=metadata,
            entries=[],
            cache_hits=0,
            failures=0,
            show=args.show,
        )
        return 0

    entries, cache_hits, failures = fetch_entries(
        ids,
        jobs=args.jobs,
        timeout=args.timeout,
        cache_dir=args.cache_dir,
        refresh=args.refresh,
        delay=args.delay,
    )

    print_summary(
        query=query,
        gateway_entries=gateway_entries,
        metadata=metadata,
        entries=entries,
        cache_hits=cache_hits,
        failures=failures,
        show=args.show,
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {len(entries)} full records to {args.output}")

    if failures:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
