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

from collections.abc import Callable
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
_LONG_MOVE_RE = re.compile(
    r"^(?P<move>"
    r"(?:[KQRBSPNDL]?[a-h][1-8][\-*][a-h][1-8](?:=[QRBSN])?(?:\s+ep\.)?)"
    r"|(?:0-0(?:-0)?)"
    r")",
    re.IGNORECASE,
)
_SAN_MOVE_RE = re.compile(
    r"^(?P<move>"
    r"(?:[KQRBSNDL]?[a-h1-8]{0,2}x?[a-h][1-8](?:=?[QRBSN])?[+#]?)"
    r"|(?:0-0(?:-0)?)"
    r")",
    re.IGNORECASE,
)
_EXPLICIT_MOVE_RE = re.compile(
    r"^(?P<piece>[KQRBSPNDL]?)(?P<from>[a-h][1-8])[\-*](?P<to>[a-h][1-8])"
    r"(?:=(?P<promotion>[QRBSN]))?(?:\s+ep\.)?$",
    re.IGNORECASE,
)
_MARK_RE = re.compile(r"^(!!|\?\?|!\?|\?!|!|\?)")
_THEMATIC_LABEL_RE = re.compile(r"^\[[A-Za-z]\]")
_ANNOTATION_ONLY_RE = re.compile(
    r"^(?P<mark>!!|\?\?|!\?|\?!|!|\?)(?:\s+(?:zugzwang\.?|zz))?$",
    re.IGNORECASE,
)
_MOVE_START_RE = re.compile(r"(?:but:?\s*)?\d+\.{1,3}\s*", re.IGNORECASE)


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


def direct_solution_children(nodes: list[SolutionNode]) -> list[SolutionNode]:
    """Return authored moves on the immediately following ply.

    Unlike :meth:`SolutionNode.real_children`, this deliberately does not
    traverse threat null nodes.  Runtime defender selection must distinguish
    explicit authored defences from a threat continuation that follows an
    omitted, otherwise irrelevant defensive move.
    """
    children: list[SolutionNode] = []
    seen: set[int] = set()
    for node in nodes:
        for child in node.children:
            if child.is_null or child.is_try or id(child) in seen:
                continue
            children.append(child)
            seen.add(id(child))
    return children


def playable_solution_moves(nodes: list[SolutionNode]) -> list[str]:
    """Return unique authored playable moves from a runtime node frontier.

    Threat null nodes are traversed by :meth:`SolutionNode.real_children`, so
    this is suitable for solver hints both on ordinary branches and after an
    omitted threat defence.  Tries and set-play branches remain excluded.
    """
    moves: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        for child in node.real_children():
            if child.uci is not None and child.uci not in seen:
                moves.append(child.uci)
                seen.add(child.uci)
    return moves


def matching_solution_children(
    nodes: list[SolutionNode], move: str
) -> list[SolutionNode]:
    """Return every authored child matching ``move`` from a node frontier.

    Historical solution text can repeat the same move in separate authored
    branches.  Keep every matching node instead of arbitrarily choosing one,
    so later continuations remain available to runtime puzzle play.
    """
    matches: list[SolutionNode] = []
    seen: set[int] = set()
    for node in nodes:
        for child in node.real_children():
            if child.uci == move and id(child) not in seen:
                matches.append(child)
                seen.add(id(child))
    return matches


def _matching_direct_solution_children(
    nodes: list[SolutionNode], move: str
) -> list[SolutionNode]:
    return [child for child in direct_solution_children(nodes) if child.uci == move]


def _threat_solution_nodes(nodes: list[SolutionNode]) -> list[SolutionNode]:
    threats: list[SolutionNode] = []
    seen: set[int] = set()
    for node in nodes:
        for child in node.children:
            if child.kind == "threat" and id(child) not in seen:
                threats.append(child)
                seen.add(id(child))
    return threats


def solution_nodes_after_moves(
    root: SolutionNode, moves: list[str]
) -> list[SolutionNode]:
    """Replay normalized game moves through an authored solution tree.

    An empty result means the played history has left the authored tree.
    Multiple nodes are retained when identical authored moves occur in more
    than one branch.

    Popeye threat notation omits an irrelevant defender ply.  On defender
    turns, prefer an explicit authored defence; if the played legal move is not
    one of those and the current authored node declares a threat, consume the
    threat null node instead.  Runtime legality is still enforced by GameModel;
    this function only maps that already-played move onto the authored tree.
    """
    nodes = [root]
    for index, move in enumerate(moves):
        if index % 2 == 1:
            matches = _matching_direct_solution_children(nodes, move)
            nodes = matches or _threat_solution_nodes(nodes)
        else:
            nodes = matching_solution_children(nodes, move)
        if not nodes:
            break
    return nodes


@dataclass(frozen=True)
class _ParsedPly:
    depth: int
    raw: str
    mark: str
    is_refutation: bool
    declares_threat: bool


@dataclass(frozen=True)
class _ParsedGroup:
    """Sibling authored moves written as compact separator alternatives."""

    depth: int
    alternatives: tuple[_ParsedPly, ...]


def _strip_comments(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = _COMMENT_RE.sub("\n", text)
    return text


def _ply_depth(number: int, dots: str) -> int:
    # Direct mates start with White. Popeye prints ``1.`` for White and
    # ``1...`` for Black. Be liberal and treat two-or-more dots as Black.
    return number * 2 if len(dots) >= 2 else number * 2 - 1


def _normalize_move_number_spacing(line: str) -> str:
    # Some historical records spell a black move as ``1. ... Kd4``.
    return re.sub(r"\b(\d+)\.\s+\.\.\.\s*", r"\1...", line)


def _split_move_segments(line: str) -> list[str]:
    paren_depth = 0
    top_level = [True] * (len(line) + 1)
    for index, char in enumerate(line):
        top_level[index] = paren_depth == 0
        if char == "(":
            paren_depth += 1
        elif char == ")" and paren_depth:
            paren_depth -= 1

    starts = [
        match.start()
        for match in _MOVE_START_RE.finditer(line)
        if top_level[match.start()]
    ]
    if not starts or (len(starts) == 1 and starts[0] == 0):
        return [line]
    if starts[0] != 0:
        starts.insert(0, 0)
    starts.append(len(line))
    return [line[starts[i] : starts[i + 1]].strip() for i in range(len(starts) - 1)]


def _with_mark(ply: _ParsedPly, mark: str) -> _ParsedPly:
    return _ParsedPly(
        depth=ply.depth,
        raw=ply.raw,
        mark=mark,
        is_refutation=ply.is_refutation,
        declares_threat=ply.declares_threat,
    )


def _with_threat(ply: _ParsedPly) -> _ParsedPly:
    return _ParsedPly(
        depth=ply.depth,
        raw=ply.raw,
        mark=ply.mark,
        is_refutation=ply.is_refutation,
        declares_threat=True,
    )


def _map_group(
    group: _ParsedGroup, transform: Callable[[_ParsedPly], _ParsedPly]
) -> _ParsedGroup:
    return _ParsedGroup(
        depth=group.depth,
        alternatives=tuple(transform(ply) for ply in group.alternatives),
    )


def _consume_move(text: str) -> tuple[str, str] | None:
    match = _LONG_MOVE_RE.match(text)
    if match is None:
        match = _SAN_MOVE_RE.match(text)
    if match is None:
        return None
    return match.group("move"), text[match.end() :]


def _consume_parenthesized(text: str) -> tuple[str, str] | None:
    """Return the contents and remainder of one balanced parenthesized suffix."""
    if not text.startswith("("):
        return None

    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[1:index].strip(), text[index + 1 :]
    return None


def _parse_parenthesized_continuation(
    text: str,
    *,
    parent_depth: int,
    line_number: int,
    original: str,
) -> tuple[list[_ParsedGroup], str]:
    """Parse Popeye's parenthesized threat continuation after an authored move."""
    consumed = _consume_parenthesized(text)
    if consumed is None:
        raise SolutionParseError(
            f"line {line_number}: unsupported solution syntax: {original!r}"
        )
    contents, remainder = consumed
    if not contents:
        raise SolutionParseError(
            f"line {line_number}: unsupported solution syntax: {original!r}"
        )

    head = _MOVE_HEAD_RE.fullmatch(contents)
    assert head is not None
    number_text = head.group("number")
    dots = head.group("dots")
    if number_text is None or dots is None:
        raise SolutionParseError(
            f"line {line_number}: parenthesized continuation has no move number: "
            f"{original!r}"
        )

    depth = _ply_depth(int(number_text), dots)
    if depth != parent_depth + 2:
        raise SolutionParseError(
            f"line {line_number}: parenthesized continuation at ply {depth} does "
            f"not follow an omitted reply after ply {parent_depth}: {original!r}"
        )

    groups, pending_refutation = _parse_move_sequence(
        head.group("body").strip(),
        depth=depth,
        is_refutation=False,
        line_number=line_number,
        original=original,
    )
    if pending_refutation:
        raise SolutionParseError(
            f"line {line_number}: refutation marker inside parenthesized "
            f"continuation: {original!r}"
        )
    return groups, remainder


def _parse_move_sequence(
    body: str,
    *,
    depth: int,
    is_refutation: bool,
    line_number: int,
    original: str,
) -> tuple[list[_ParsedGroup], bool]:
    """Parse one numbered move plus compact unnumbered continuations.

    Older YACPDB records frequently put a whole line of play on one physical
    line, e.g. ``1.Rd6-d4+! e5*d4 2.Qh5-c5``. Numbered moves are split before
    this helper is called; the unnumbered replies are consumed here one ply at
    a time. Slash-separated moves at one ply are retained as sibling
    alternatives. Parenthesized continuations are retained as threat branches
    after the omitted defensive ply. Single-letter bracket labels such as
    ``[A]``/``[a]`` are thematic annotations and do not alter the move tree.
    Other unsupported syntax is rejected rather than truncated.
    """
    groups: list[_ParsedGroup] = []
    text = body.strip()
    current_depth = depth
    refutation = is_refutation
    pending_refutation = False

    while text:
        alternatives: list[_ParsedPly] = []

        while True:
            consumed = _consume_move(text)
            if consumed is None:
                raise SolutionParseError(
                    f"line {line_number}: unsupported solution syntax: {original!r}"
                )
            raw_move, text = consumed
            text = text.lstrip()
            mark = ""
            declares_threat = False

            while text:
                label_match = _THEMATIC_LABEL_RE.match(text)
                if label_match:
                    text = text[label_match.end() :].lstrip()
                    continue
                mark_match = _MARK_RE.match(text)
                if mark_match:
                    mark = mark_match.group(1)
                    text = text[mark_match.end() :].lstrip()
                    continue
                if text.startswith("+") or text.startswith("#"):
                    text = text[1:].lstrip()
                    continue
                lower = text.lower()
                if lower.startswith("zugzwang."):
                    text = text[len("zugzwang.") :].lstrip()
                    continue
                if lower.startswith("zugzwang"):
                    text = text[len("zugzwang") :].lstrip()
                    continue
                if lower.startswith("zz") and (len(text) == 2 or text[2].isspace()):
                    text = text[2:].lstrip()
                    continue
                if lower.startswith("threat:"):
                    declares_threat = True
                    text = text[len("threat:") :].lstrip()
                    break
                if lower == "threat":
                    declares_threat = True
                    text = ""
                    break
                if lower.startswith("but") and (
                    len(text) == 3 or text[3] in {":", " ", "\t"}
                ):
                    consumed_but = 4 if len(text) > 3 and text[3] == ":" else 3
                    text = text[consumed_but:].lstrip()
                    pending_refutation = True
                    break
                break

            alternatives.append(
                _ParsedPly(
                    depth=current_depth,
                    raw=raw_move,
                    mark=mark,
                    is_refutation=refutation,
                    declares_threat=declares_threat,
                )
            )

            if not text.startswith(("/", ",")):
                break
            text = text[1:].lstrip()
            if not text:
                raise SolutionParseError(
                    f"line {line_number}: unsupported solution syntax: {original!r}"
                )

        groups.append(
            _ParsedGroup(depth=current_depth, alternatives=tuple(alternatives))
        )
        refutation = False

        if text.startswith("("):
            groups[-1] = _map_group(groups[-1], _with_threat)
            continuation, text = _parse_parenthesized_continuation(
                text,
                parent_depth=current_depth,
                line_number=line_number,
                original=original,
            )
            groups.extend(continuation)
            text = text.lstrip()
            if not text:
                break
            raise SolutionParseError(
                f"line {line_number}: unsupported solution syntax: {original!r}"
            )

        if not text:
            break
        if text.startswith("["):
            raise SolutionParseError(
                f"line {line_number}: unsupported solution syntax: {original!r}"
            )
        current_depth += 1

    return groups, pending_refutation


def _parse_solution_lines(solution: str) -> list[_ParsedGroup]:
    groups: list[_ParsedGroup] = []
    pending_refutation = False
    solution = _strip_comments(solution)

    for line_number, original_line in enumerate(solution.splitlines(), 1):
        normalized_line = _normalize_move_number_spacing(
            original_line.strip().strip('"')
        )
        for original in _split_move_segments(normalized_line):
            line = original.strip()
            if not line:
                continue

            lower = line.lower()
            if lower.startswith("threat:") or lower == "threat":
                if not groups:
                    raise SolutionParseError(
                        f"line {line_number}: threat marker has no preceding move"
                    )
                groups[-1] = _map_group(groups[-1], _with_threat)
                if lower == "threat":
                    continue
                line = line[len("threat:") :].strip()
                if not line:
                    continue
                lower = line.lower()
            if lower in {"zugzwang.", "zugzwang"}:
                continue

            annotation = _ANNOTATION_ONLY_RE.fullmatch(line)
            if annotation:
                if not groups:
                    raise SolutionParseError(
                        f"line {line_number}: annotation has no preceding move"
                    )
                groups[-1] = _map_group(
                    groups[-1],
                    lambda ply: _with_mark(ply, annotation.group("mark")),
                )
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

            if number_text is None:
                if not groups:
                    raise SolutionParseError(
                        f"line {line_number}: first move has no move number"
                    )
                depth = groups[-1].depth + 1
            else:
                assert dots is not None
                depth = _ply_depth(int(number_text), dots)

            sequence, trailing_refutation = _parse_move_sequence(
                body,
                depth=depth,
                is_refutation=is_refutation,
                line_number=line_number,
                original=original.strip(),
            )
            groups.extend(sequence)
            pending_refutation = trailing_refutation

    if pending_refutation:
        raise SolutionParseError("solution ends immediately after a refutation marker")
    if not groups:
        raise SolutionParseError("solution contains no moves")
    return groups


# Tree construction follows the Popeye ply-depth semantics used by Olive and
# Py2Web (GPL-3.0), adapted here to PyChess move validation and data types.
def _unflatten(groups: list[_ParsedGroup]) -> SolutionNode:
    root = SolutionNode(depth=0, kind="root")
    frontier: dict[int, list[SolutionNode]] = {0: [root]}

    for group in groups:
        depth = group.depth
        if depth < 1:
            raise SolutionParseError(f"invalid ply depth {depth}")

        for stale_depth in [value for value in frontier if value >= depth]:
            del frontier[stale_depth]

        parent_depth = depth - 1
        if parent_depth not in frontier:
            available_depths = [value for value in frontier if value < depth]
            if not available_depths:
                raise SolutionParseError(f"cannot attach alternatives at depth {depth}")
            nearest_depth = max(available_depths)
            parents = frontier[nearest_depth]
            for missing_depth in range(nearest_depth + 1, depth):
                null_nodes: list[SolutionNode] = []
                for parent in parents:
                    if parent.depth == 0:
                        kind = "set"
                    elif parent.declares_threat:
                        kind = "threat"
                    else:
                        kind = "null"
                    null_node = SolutionNode(depth=missing_depth, kind=kind)
                    parent.children.append(null_node)
                    null_nodes.append(null_node)
                frontier[missing_depth] = null_nodes
                parents = null_nodes
        else:
            parents = frontier[parent_depth]

        nodes: list[SolutionNode] = []
        for parent in parents:
            for ply in group.alternatives:
                if ply.depth != depth:
                    raise SolutionParseError(
                        f"alternative {ply.raw!r} has inconsistent ply depth {ply.depth}"
                    )
                node = SolutionNode(
                    depth=depth,
                    raw=ply.raw,
                    mark=ply.mark,
                    is_refutation=ply.is_refutation,
                    declares_threat=ply.declares_threat,
                )
                parent.children.append(node)
                nodes.append(node)
        frontier[depth] = nodes

    return root


def _normalize_san(raw: str) -> str:
    san = raw.replace("0", "O")
    if san and san[0] in {"S", "D", "L"}:
        san = {"S": "N", "D": "Q", "L": "B"}[san[0]] + san[1:]
    san = re.sub(r"([18])=?S(?=[+#]?$)", r"\1=N", san)
    san = re.sub(r"([18])N(?=[+#]?$)", r"\1=N", san)
    return san


def _parse_authored_move(board: LBoard, raw: str) -> int:
    if raw.startswith("0-0"):
        return lmove.parseSAN(board, raw.replace("0", "O"))

    match = _EXPLICIT_MOVE_RE.match(raw)
    if match is None:
        return lmove.parseSAN(board, _normalize_san(raw))

    piece_name = match.group("piece").upper() or "P"
    piece_name = {"N": "S", "D": "Q", "L": "B"}.get(piece_name, piece_name)
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
        suffix = {"S": "n", "N": "n"}.get(promotion.upper(), promotion.lower())
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


_SERIALIZED_MOVE_RE = re.compile(r"(?:[a-h][1-8][a-h][1-8][qrbn]?|O-O(?:-O)?)$")
_SERIALIZED_MARKS = {"!", "?", "!!", "??", "!?", "?!"}
_SERIALIZED_NULL_KINDS = {"set", "threat", "null"}


def solution_tree_to_data(root: SolutionNode) -> list[dict[str, object]]:
    """Serialize a compiled tree into the packaged YACPDB JSON representation.

    The synthetic root is omitted.  Real move nodes store only normalized PyChess AN
    plus the authored annotations needed by Learn; null nodes retain their kind
    so omitted set-play/threat plies remain explicit.  The original solution
    text is stored once at puzzle-record level, so duplicating each raw move
    spelling here is unnecessary.
    """

    if root.kind != "root" or root.depth != 0:
        raise ValueError("solution tree must have a depth-0 root node")

    def serialize(node: SolutionNode) -> dict[str, object]:
        data: dict[str, object]
        if node.is_null:
            data = {"kind": node.kind}
        else:
            if node.uci is None:
                raise ValueError("cannot serialize unresolved solution move")
            data = {"move": node.uci}
            if node.mark:
                data["mark"] = node.mark
            if node.is_refutation:
                data["refutation"] = True
            if node.declares_threat:
                data["declares_threat"] = True

        if node.children:
            data["children"] = [serialize(child) for child in node.children]
        return data

    return [serialize(child) for child in root.children]


def solution_tree_from_data(data: object) -> SolutionNode:
    """Deserialize and validate a packaged YACPDB solution tree."""

    if not isinstance(data, list):
        raise ValueError("solution tree must be a list of root children")

    def deserialize(value: object, depth: int) -> SolutionNode:
        if not isinstance(value, dict):
            raise ValueError("solution tree node must be an object")

        kind = value.get("kind")
        if kind is not None:
            if kind not in _SERIALIZED_NULL_KINDS:
                raise ValueError(f"unsupported serialized null kind {kind!r}")
            allowed = {"kind", "children"}
            extra = set(value) - allowed
            if extra:
                raise ValueError(
                    f"unsupported serialized null fields: {sorted(extra)!r}"
                )
            node = SolutionNode(depth=depth, kind=kind)
        else:
            allowed = {
                "move",
                "mark",
                "refutation",
                "declares_threat",
                "children",
            }
            extra = set(value) - allowed
            if extra:
                raise ValueError(
                    f"unsupported serialized move fields: {sorted(extra)!r}"
                )

            move = value.get("move")
            if not isinstance(move, str) or not _SERIALIZED_MOVE_RE.fullmatch(move):
                raise ValueError(f"invalid serialized move {move!r}")

            mark = value.get("mark", "")
            if not isinstance(mark, str) or (mark and mark not in _SERIALIZED_MARKS):
                raise ValueError(f"invalid serialized move mark {mark!r}")

            refutation = value.get("refutation", False)
            declares_threat = value.get("declares_threat", False)
            if not isinstance(refutation, bool):
                raise ValueError("serialized refutation flag must be boolean")
            if not isinstance(declares_threat, bool):
                raise ValueError("serialized declares_threat flag must be boolean")

            node = SolutionNode(
                depth=depth,
                uci=move,
                mark=mark,
                is_refutation=refutation,
                declares_threat=declares_threat,
            )

        children = value.get("children", [])
        if not isinstance(children, list):
            raise ValueError("serialized solution children must be a list")
        node.children = [deserialize(child, depth + 1) for child in children]
        return node

    root = SolutionNode(depth=0, kind="root")
    root.children = [deserialize(child, 1) for child in data]
    return root


def parse_solution(solution: str, fen: str) -> SolutionNode:
    """Compile Popeye solution text into a validated normalized move tree."""
    board = LBoard()
    board.applyFen(fen)
    root = _unflatten(_parse_solution_lines(solution))
    _resolve_tree(root, board)
    return root
