#!/usr/bin/env python3
"""Probe current YACPDB data for a PyChess puzzle-corpus refresh.

This is a maintainer utility. It reads complete problem records from YACPDB's
public Query Language gateway. It does not modify PyChess's packaged puzzle
corpus.

Examples::

    python3 utilities/yacpdb_probe.py --composer "Loyd, Samuel"
    python3 utilities/yacpdb_probe.py --composer "Loyd, Samuel" --all-pages
    python3 utilities/yacpdb_probe.py --query 'Id("12345")' --show 1
    python3 utilities/yacpdb_probe.py --position \
        "Ka7 Qh6 Be4 Sd7 Pe5" "Kg8 Rg7 Pe7 Pe6"
    python3 utilities/yacpdb_probe.py --input loyd-yacpdb.json --audit-solutions
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

QL_URL = "https://yacpdb.org/gateway/ql"
USER_AGENT = "PyChess YACPDB corpus probe (+https://github.com/pychess/pychess)"
DIRECT_MATE_RE = re.compile(r"^#([1-9][0-9]*)$")
ORTHODOX_PIECE_RE = re.compile(r"^[KQRBSP][a-h][1-8]$")


def quote_ql_string(value: str) -> str:
    """Quote a string for use inside YACPDB's QL syntax."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def composer_query(composer: str) -> str:
    return f'Author("{quote_ql_string(composer)}%")'


def exact_position_query(white: list[str], black: list[str]) -> str:
    """Build the exact-position QL used by YACPDB/FEN Tool searches."""
    pieces = [f"w{piece}" for piece in white] + [f"b{piece}" for piece in black]
    matrix = " ".join(pieces)
    return (
        f'MatrixExtended("{matrix}", false, false, "None") '
        f"AND PCount(*) = {len(pieces)}"
    )


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


def query_url(query: str, *, page: int = 1) -> str:
    params: dict[str, Any] = {"q": query}
    if page != 1:
        # YACPDB's SPA encodes result pages as .../#q/<query>/<page>; the
        # gateway forwards the same page number as its short ``p`` parameter.
        params["p"] = page
    return f"{QL_URL}?{urlencode(params)}"


def fetch_query_page(
    query: str, *, page: int, timeout: float
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    payload = request_json(query_url(query, page=page), timeout=timeout)
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
    unusable = len(entries) - len(normalized)
    metadata = {key: value for key, value in result.items() if key != "entries"}
    return normalized, metadata, unusable


def result_count(metadata: dict[str, Any]) -> int | None:
    value = metadata.get("count")
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count >= 0 else None


def debug_page(
    *,
    query: str,
    page: int,
    entries: list[dict[str, Any]],
    metadata: dict[str, Any],
    unusable: int,
    cumulative_usable: int,
    cumulative_unusable: int,
) -> None:
    ids = [problem_id for entry in entries if (problem_id := entry_id(entry))]
    raw_rows = len(entries) + unusable
    if ids:
        id_summary = f"first={ids[0]} last={ids[-1]} min={min(ids)} max={max(ids)}"
    else:
        id_summary = "none"
    print(
        "DEBUG YACPDB "
        f"page={page} raw={raw_rows} usable={len(entries)} unusable={unusable} "
        f"cumulative_usable={cumulative_usable} "
        f"cumulative_unusable={cumulative_unusable} "
        f"accounted={cumulative_usable + cumulative_unusable} "
        f"count={result_count(metadata)!r} ids=[{id_summary}]",
        file=sys.stderr,
    )
    print(f"DEBUG YACPDB url={query_url(query, page=page)}", file=sys.stderr)


def fetch_query(
    query: str,
    *,
    timeout: float,
    page: int = 1,
    all_pages: bool = False,
    debug: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], int, int]:
    first_entries, metadata, unusable = fetch_query_page(
        query, page=page, timeout=timeout
    )
    if debug:
        debug_page(
            query=query,
            page=page,
            entries=first_entries,
            metadata=metadata,
            unusable=unusable,
            cumulative_usable=len(first_entries),
            cumulative_unusable=unusable,
        )
    if not all_pages:
        return first_entries, metadata, 1, unusable

    if page != 1:
        raise ValueError("all-pages queries must start at page 1")

    expected = result_count(metadata)
    accounted = len(first_entries) + unusable
    if expected is None or expected <= accounted:
        return first_entries, metadata, 1, unusable

    if not first_entries and unusable == 0:
        return first_entries, metadata, 1, unusable

    entries = list(first_entries)
    seen_ids = {problem_id for entry in entries if (problem_id := entry_id(entry))}
    if len(seen_ids) != len(entries):
        raise RuntimeError("YACPDB gateway returned a record without a valid ID")
    page_number = 1
    page_capacity = len(first_entries) + unusable
    previous_raw_rows = page_capacity
    last_data_page = 1

    while len(seen_ids) + unusable < expected:
        page_number += 1
        page_entries, page_metadata, page_unusable = fetch_query_page(
            query, page=page_number, timeout=timeout
        )
        if debug:
            debug_page(
                query=query,
                page=page_number,
                entries=page_entries,
                metadata=page_metadata,
                unusable=page_unusable,
                cumulative_usable=len(entries) + len(page_entries),
                cumulative_unusable=unusable + page_unusable,
            )
        raw_rows = len(page_entries) + page_unusable
        if raw_rows == 0:
            if previous_raw_rows < page_capacity:
                # The gateway's reported count can include records which are
                # not actually pageable. A short page followed by an empty
                # page is authoritative evidence that the result set ended.
                break
            raise RuntimeError(
                f"YACPDB page {page_number} was empty before all {expected} "
                "records were returned"
            )

        page_ids = {
            problem_id
            for entry in page_entries
            if (problem_id := entry_id(entry)) is not None
        }
        if len(page_ids) != len(page_entries):
            raise RuntimeError(
                f"YACPDB page {page_number} returned a record without a valid ID"
            )

        new_ids = page_ids - seen_ids
        if len(new_ids) != len(page_ids):
            raise RuntimeError(
                f"YACPDB page {page_number} repeated already-seen IDs; "
                "gateway pagination may have changed"
            )

        entries.extend(page_entries)
        seen_ids.update(new_ids)
        unusable += page_unusable
        page_capacity = max(page_capacity, raw_rows)
        previous_raw_rows = raw_rows
        last_data_page = page_number

        page_count = result_count(page_metadata)
        if page_count is not None and page_count != expected:
            raise RuntimeError(
                f"YACPDB result count changed while paging ({expected} -> {page_count})"
            )

    accounted = len(seen_ids) + unusable
    if accounted != expected and previous_raw_rows >= page_capacity:
        raise RuntimeError(
            "YACPDB pagination accounting mismatch: "
            f"{len(seen_ids)} usable + {unusable} unusable rows, expected {expected}"
        )

    return entries, metadata, last_data_page, unusable


def entry_id(entry: dict[str, Any]) -> int | None:
    value = entry.get("id")
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


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

    Multi-position/role-reversed records and records explicitly marked cooked,
    unsound, or retro are not suitable for PyChess's ordinary one-position
    Learn puzzles and are therefore excluded from the core candidate set.
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
    if (
        not isinstance(solution, str)
        or not solution.strip()
        or solution.strip().lower() == "none"
    ):
        traits.append("missing-solution")

    twins = entry.get("twins")
    if twins not in (None, {}, [], ""):
        traits.append("has-twins")

    options = entry.get("options")
    if isinstance(options, list) and options:
        traits.append("has-options")
        if any(str(option).lower() == "duplex" for option in options):
            traits.append("has-duplex")
    elif options not in (None, [], ""):
        traits.append("has-options")

    keywords = entry.get("keywords")
    if isinstance(keywords, list):
        normalized_keywords = {str(keyword).lower() for keyword in keywords}
        if "cooked" in normalized_keywords:
            traits.append("cooked")
        if "unsound" in normalized_keywords:
            traits.append("unsound")
        if "retro" in normalized_keywords:
            traits.append("retro")

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
        "has-twins",
        "has-duplex",
        "cooked",
        "unsound",
        "retro",
    }
    if not core_failures.intersection(traits):
        traits.insert(0, "candidate")

    return tuple(traits)


def entry_fen(entry: dict[str, Any]) -> str:
    """Build an orthodox FEN from a YACPDB algebraic position."""
    pieces = position_pieces(entry)
    if pieces is None:
        raise ValueError("record has no usable algebraic position")

    board: dict[str, str] = {}
    for color, color_pieces in (("white", pieces[0]), ("black", pieces[1])):
        for piece in color_pieces:
            if not ORTHODOX_PIECE_RE.fullmatch(piece):
                raise ValueError(f"unsupported {color} piece {piece!r}")
            square = piece[1:3]
            if square in board:
                raise ValueError(f"duplicate piece square {square}")
            symbol = "N" if piece[0] == "S" else piece[0]
            board[square] = symbol if color == "white" else symbol.lower()

    ranks: list[str] = []
    for rank in range(8, 0, -1):
        empty = 0
        parts: list[str] = []
        for file_name in "abcdefgh":
            symbol = board.get(f"{file_name}{rank}")
            if symbol is None:
                empty += 1
                continue
            if empty:
                parts.append(str(empty))
                empty = 0
            parts.append(symbol)
        if empty:
            parts.append(str(empty))
        ranks.append("".join(parts))

    # Chess-composition convention permits castling unless it can be proved
    # unavailable. The source records do not carry FEN move-right fields, so
    # preserve every castling right consistent with the diagram; applying
    # authored moves will clear rights normally afterwards.
    castling = ""
    white, black = pieces
    white_set = set(white)
    black_set = set(black)
    if "Ke1" in white_set:
        if "Rh1" in white_set:
            castling += "K"
        if "Ra1" in white_set:
            castling += "Q"
    if "Ke8" in black_set:
        if "Rh8" in black_set:
            castling += "k"
        if "Ra8" in black_set:
            castling += "q"

    return f"{'/'.join(ranks)} w {castling or '-'} - 0 1"


def solution_failure_category(message: str) -> str:
    if "unsupported solution syntax" in message:
        return "unsupported-syntax"
    if " is illegal at ply " in message:
        return "illegal-move"
    if "cannot parse authored move" in message:
        return "move-parse"
    if "cannot attach ply" in message or "null" in message:
        return "tree-structure"
    return "other"


def audit_solutions(
    entries: list[dict[str, Any]],
) -> tuple[Counter[str], list[tuple[int | None, str, str]]]:
    """Compile all core candidates and categorize parser failures."""
    repo_lib = Path(__file__).resolve().parents[1] / "lib"
    repo_lib_text = str(repo_lib)
    if repo_lib_text not in sys.path:
        sys.path.insert(0, repo_lib_text)

    from pychess.Savers.yacpdb_solution import SolutionParseError, parse_solution

    counts: Counter[str] = Counter()
    failures: list[tuple[int | None, str, str]] = []
    for entry in entries:
        if "candidate" not in classify(entry):
            continue
        counts["candidates"] += 1
        try:
            solution = entry["solution"]
            assert isinstance(solution, str)
            parse_solution(solution, entry_fen(entry))
        except (SolutionParseError, ValueError) as exc:
            category = solution_failure_category(str(exc))
            counts["failed"] += 1
            counts[category] += 1
            failures.append((entry_id(entry), category, str(exc)))
        else:
            counts["compiled"] += 1

    return counts, failures


def print_solution_audit(entries: list[dict[str, Any]], *, show_failures: int) -> None:
    counts, failures = audit_solutions(entries)
    candidates = counts["candidates"]
    compiled = counts["compiled"]
    failed = counts["failed"]

    print("\nSolution tree audit:")
    print(f"  candidates             {candidates}")
    print(f"  compiled               {compiled}")
    print(f"  failed                 {failed}")
    if candidates:
        print(f"  success                {compiled / candidates:.1%}")

    categories = [
        (name, count)
        for name, count in counts.items()
        if name not in {"candidates", "compiled", "failed"}
    ]
    if categories:
        print("  failure categories:")
        for name, count in sorted(categories):
            print(f"    {name:20} {count}")

    if failures and show_failures:
        print(f"\nParser failure samples ({min(show_failures, len(failures))}):")
        for problem_id, category, message in failures[:show_failures]:
            print(f"  #{problem_id or '?'} [{category}] {message}")


def print_summary(
    *,
    query: str,
    entries: list[dict[str, Any]],
    metadata: dict[str, Any],
    gateway_pages: int,
    unusable_rows: int,
    show: int,
) -> None:
    ids = [problem_id for entry in entries if (problem_id := entry_id(entry))]
    traits = Counter(trait for entry in entries for trait in classify(entry))

    print(f"QL query: {query}")
    print(f"Gateway records: {len(entries)}")
    print(f"Gateway records with IDs: {len(ids)}")
    print(f"Gateway pages fetched: {gateway_pages}")
    if unusable_rows:
        print(f"Gateway unusable rows: {unusable_rows}")
    if metadata:
        print("Gateway metadata:")
        print(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Gateway metadata: (none returned)")

    print()
    print("Record traits:")
    for trait, count in sorted(traits.items()):
        print(f"  {trait:22} {count}")

    candidates = [entry for entry in entries if "candidate" in classify(entry)]
    print(f"\nCore PyChess candidates: {len(candidates)}")
    print(
        "  (sound non-retro single-position non-duplex direct #N + orthodox "
        "8x8 pieces + one king each + authored solution)"
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
        "--input",
        type=Path,
        help="read previously downloaded YACPDB gateway records from JSON",
    )
    source.add_argument(
        "--composer",
        help='composer name for a YACPDB Author(...) query, e.g. "Loyd, Samuel"',
    )
    source.add_argument("--query", help="raw YACPDB Query Language expression")
    source.add_argument(
        "--position",
        nargs=2,
        metavar=("WHITE", "BLACK"),
        help=(
            "exact orthodox position as two space-separated piece lists, "
            'e.g. --position "Ka7 Qh6 Be4" "Kg8 Rg7"'
        ),
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="QL result page to inspect (default: 1)",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="walk every QL result page using the gateway result count",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="inspect only the first N records returned by the gateway",
    )
    parser.add_argument("--show", type=int, default=3, help="show N candidate samples")
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="HTTP timeout in seconds"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print per-page YACPDB pagination diagnostics to stderr",
    )
    parser.add_argument(
        "--audit-solutions",
        action="store_true",
        help="compile every core candidate solution and report parser failures",
    )
    parser.add_argument(
        "--show-failures",
        type=int,
        default=20,
        help="show N solution-parser failures when auditing (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write selected gateway records as UTF-8 JSON for inspection",
    )
    args = parser.parse_args(argv)
    if args.page < 1:
        parser.error("--page must be at least 1")
    if args.all_pages and args.page != 1:
        parser.error("--all-pages cannot be combined with --page other than 1")
    if args.max_records is not None and args.max_records < 1:
        parser.error("--max-records must be at least 1")
    if args.show < 0:
        parser.error("--show cannot be negative")
    if args.show_failures < 0:
        parser.error("--show-failures cannot be negative")
    if args.input and (args.all_pages or args.page != 1 or args.debug):
        parser.error("--input cannot be combined with --all-pages, --page, or --debug")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.input:
        query = f"input:{args.input}"
        try:
            payload = json.loads(args.input.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.input}: {exc}", file=sys.stderr)
            return 1
        if not isinstance(payload, list) or not all(
            isinstance(entry, dict) for entry in payload
        ):
            print(
                f"error: {args.input} must contain a JSON array of problem objects",
                file=sys.stderr,
            )
            return 1
        entries = payload
        metadata = {"count": len(entries), "source": str(args.input)}
        gateway_pages = 0
        unusable_rows = 0
    else:
        if args.query:
            query = args.query
        elif args.composer:
            query = composer_query(args.composer)
        else:
            white, black = (pieces.split() for pieces in args.position)
            query = exact_position_query(white, black)

        try:
            entries, metadata, gateway_pages, unusable_rows = fetch_query(
                query,
                timeout=args.timeout,
                page=args.page,
                all_pages=args.all_pages,
                debug=args.debug,
            )
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        gateway_accounted = len(entries) + unusable_rows
        expected = result_count(metadata)
        if args.all_pages and expected is not None and gateway_accounted != expected:
            print(
                "warning: YACPDB reported "
                f"{expected} matches, but pagination returned {gateway_accounted} rows "
                f"({len(entries)} usable + {unusable_rows} unusable); "
                "using the pageable result set",
                file=sys.stderr,
            )

    if args.max_records is not None:
        entries = entries[: args.max_records]

    print_summary(
        query=query,
        entries=entries,
        metadata=metadata,
        gateway_pages=gateway_pages,
        unusable_rows=unusable_rows,
        show=args.show,
    )

    if args.audit_solutions:
        print_solution_audit(entries, show_failures=args.show_failures)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nWrote {len(entries)} gateway records to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
