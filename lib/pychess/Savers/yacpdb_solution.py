"""Parse orthodox YACPDB/Popeye solution text into a move tree.

The YACPDB puzzle corpus stores authored solutions in Popeye-style long
algebraic notation.  This module turns that text into a small tree whose real
moves are normalized to UCI/AN using PyChess's own move parser and legality
checks.

The tree intentionally keeps null nodes.  Popeye omits a ply for set play and
for threats; retaining that missing ply preserves the authored variation
structure without ever exposing the null node as a playable move.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from pychess.Utils.Cord import Cord
from pychess.Utils.const import (
    BISHOP,
    KING,
    KNIGHT,
    NORMAL_MOVE,
    PAWN,
    QUEEN,
    ROOK,
)
from pychess.Utils.lutils import lmove
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmovegen import newMove


class SolutionParseError(ValueError):
    """Raised when authored solution text cannot be compiled safely."""


_COMMENT_RE = re.compile(r"\{[^{}]*\}")
_MOVE_HEAD_RE = re.compile(r"^(?:(?P<number>\d+)(?P<dots>\.{1,3})\s*)?(?P<body>.*)$")
_MOVE_RE = re.compile(
    r"^(?P<move>"
    r"(?:[KQRBSP]?[a-h][1-8][\-*][a-h][1-8](?:=[QRBS])?(?:\s+ep\.)?)"
    r"|(?:0-0(?:-0)?)"
    r")(?P<tail>.*)$",
    re.IGNORECASE,
)
_EXPLICIT_MOVE_RE = re.compile(
    r"^(?P<piece>[KQRBSP]?)(?P<from>[a-h][1-8])[\-*](?P<to>[a-h][1-8])"
    r"(?:=(?P<promotion>[QRBS]))?(?:\s+ep\.)?$",
    re.IGNORECASE,
)
_MARK_RE = re.compile(r"(?<!\w)(!!|\?\?|!\?|\?!|!|\?)(?!\w)")
_MOVE_START_RE = re.compile(
    r"(?:but:?\s*)?\d+\.{1,3}\s*(?=(?:[KQRBSP]?[a-h][1-8]|0-0))",
    re.IGNORECASE,
)


@dataclass
class SolutionNode:
    """One node in an authored solution tree.

    ``kind`` is ``root`` or ``move`` for real nodes, and ``set``/``threat``
    for the implicit null plies used by Popeye's solution notation.
    """

    depth: int
    kind: str = "move"
    raw: str | None = None
    uci: str | None = None
    mark: str = ""
    is_refutation: bool = False
    declares_threat: bool = False
    children: list[SolutionNode] = field(default_factory=list)

    @property
    def is_null(self) -> bool:
        return self.kind in {"set", "threat", "null"}

    @property
    def is_try(self) -> bool:
        return "?" in self.mark

    def real_children(self, *, include_tries: bool = False) -> list[SolutionNode]:
        """Return directly playable authored children, skipping null plies.

        Set-play branches are not playable from the initial puzzle position;
        threat null nodes *are* traversed so callers can inspect the move that
        follows the hypothetical opponent pass.
        """
        result: list[SolutionNode] = []
        for child in self.children:
            if child.kind == "set":
                continue
            if child.is_null:
                result.extend(child.real_children(include_tries=include_tries))
            elif include_tries or not child.is_try:
                result.append(child)
        return result


@dataclass(frozen=True)
class _ParsedPly:
    depth: int
    raw: str
    mark: str
    is_refutation: bool
    declares_threat: bool


def _strip_comments(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = _COMMENT_RE.sub("\n", text)
    return text


def _ply_depth(number: int, dots: str) -> int:
    # Direct mates start with White.  Popeye prints ``1.`` for White and
    # ``1...`` for Black.  Be liberal and treat two-or-more dots as Black.
    return number * 2 if len(dots) >= 2 else number * 2 - 1


def _split_move_segments(line: str) -> list[str]:
    starts = [match.start() for match in _MOVE_START_RE.finditer(line)]
    if len(starts) <= 1:
        return [line]
    if starts[0] != 0:
        starts.insert(0, 0)
    starts.append(len(line))
    return [line[starts[i] : starts[i + 1]].strip() for i in range(len(starts) - 1)]


def _parse_solution_lines(solution: str) -> list[_ParsedPly]:
    plies: list[_ParsedPly] = []
    pending_threat = False
    pending_refutation = False
    solution = _strip_comments(solution)

    for line_number, original_line in enumerate(solution.splitlines(), 1):
        for original in _split_move_segments(original_line.strip().strip('"')):
            line = original.strip()
            if not line:
                continue

            lower = line.lower()
            if lower in {"threat:", "threat"}:
                if not plies:
                    raise SolutionParseError(
                        f"line {line_number}: threat marker has no preceding move"
                    )
                pending_threat = True
                continue
            if lower in {"zugzwang.", "zugzwang"}:
                continue
            if lower in {"but", "but:"}:
                pending_refutation = True
                continue

            is_refutation = pending_refutation
            pending_refutation = False
            but_match = re.match(r"^but:?\s*", line, flags=re.IGNORECASE)
            if but_match:
                is_refutation = True
                line = line[but_match.end() :].lstrip()

            head = _MOVE_HEAD_RE.match(line)
            assert head is not None
            number_text = head.group("number")
            dots = head.group("dots")
            body = head.group("body").strip()

            move_match = _MOVE_RE.match(body)
            if move_match is None:
                raise SolutionParseError(
                    f"line {line_number}: unsupported solution syntax: "
                    f"{original.strip()!r}"
                )

            raw_move = move_match.group("move")
            tail = move_match.group("tail")
            mark_match = _MARK_RE.search(tail)
            mark = mark_match.group(1) if mark_match else ""
            declares_threat = pending_threat or "threat:" in tail.lower()
            pending_threat = False

            if number_text is None:
                if not plies:
                    raise SolutionParseError(
                        f"line {line_number}: first move has no move number"
                    )
                depth = plies[-1].depth + 1
            else:
                assert dots is not None
                depth = _ply_depth(int(number_text), dots)

            plies.append(
                _ParsedPly(
                    depth=depth,
                    raw=raw_move,
                    mark=mark,
                    is_refutation=is_refutation,
                    declares_threat=declares_threat,
                )
            )

    if pending_threat:
        raise SolutionParseError("solution ends immediately after a threat marker")
    if not plies:
        raise SolutionParseError("solution contains no moves")
    return plies


# Tree construction follows the Popeye ply-depth semantics used by Olive and
# Py2Web (GPL-3.0), adapted here to PyChess move validation and data types.
def _unflatten(plies: list[_ParsedPly]) -> SolutionNode:
    root = SolutionNode(depth=0, kind="root")
    stack = [root]

    for ply in plies:
        if ply.depth < 1:
            raise SolutionParseError(f"invalid ply depth {ply.depth}")

        while stack[-1].depth >= ply.depth:
            stack.pop()
        parent = stack[-1]

        while parent.depth + 1 < ply.depth:
            if parent.depth == 0:
                kind = "set"
            elif parent.declares_threat:
                kind = "threat"
            else:
                kind = "null"
            null_node = SolutionNode(depth=parent.depth + 1, kind=kind)
            parent.children.append(null_node)
            parent = null_node
            stack.append(parent)

        if parent.depth + 1 != ply.depth:
            raise SolutionParseError(
                f"cannot attach ply {ply.raw!r} at depth {ply.depth}"
            )

        node = SolutionNode(
            depth=ply.depth,
            raw=ply.raw,
            mark=ply.mark,
            is_refutation=ply.is_refutation,
            declares_threat=ply.declares_threat,
        )
        parent.children.append(node)
        stack.append(node)

    return root


def _parse_authored_move(board: LBoard, raw: str) -> int:
    if raw.startswith("0-0"):
        return lmove.parseSAN(board, raw.replace("0", "O"))

    match = _EXPLICIT_MOVE_RE.match(raw)
    if match is None:
        raise SolutionParseError(f"unsupported authored move {raw!r}")

    piece_name = match.group("piece").upper() or "P"
    piece_name = "S" if piece_name == "N" else piece_name
    piece_types = {
        "K": KING,
        "Q": QUEEN,
        "R": ROOK,
        "B": BISHOP,
        "S": KNIGHT,
        "P": PAWN,
    }
    from_square = match.group("from")
    from_cord = Cord(from_square).cord
    expected_piece = piece_types.get(piece_name)
    if expected_piece is None or board.arBoard[from_cord] != expected_piece:
        raise SolutionParseError(
            f"authored move {raw!r} does not match the piece on {from_square}"
        )

    promotion = match.group("promotion")
    suffix = ""
    if promotion:
        suffix = {"S": "n"}.get(promotion.upper(), promotion.lower())
    return lmove.parseAN(board, match.group("from") + match.group("to") + suffix)


def _resolve_tree(node: SolutionNode, board: LBoard) -> None:
    for child in node.children:
        branch = board.clone()
        if child.is_null:
            branch.applyMove(newMove(0, 0, NORMAL_MOVE))
        else:
            assert child.raw is not None
            try:
                move = _parse_authored_move(branch, child.raw)
            except (lmove.ParsingError, IndexError, KeyError, ValueError) as exc:
                raise SolutionParseError(
                    f"cannot parse authored move {child.raw!r} at ply "
                    f"{child.depth}: {exc}"
                ) from exc
            if not lmove.validateMove(branch, move):
                raise SolutionParseError(
                    f"authored move {child.raw!r} is illegal at ply {child.depth} "
                    f"from {branch.asFen()}"
                )
            child.uci = lmove.toAN(branch, move, short=True)
            branch.applyMove(move)
        _resolve_tree(child, branch)


def parse_solution(solution: str, fen: str) -> SolutionNode:
    """Compile Popeye solution text into a validated normalized move tree."""
    board = LBoard()
    board.applyFen(fen)
    root = _unflatten(_parse_solution_lines(solution))
    _resolve_tree(root, board)
    return root
