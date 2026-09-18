import asyncio

from gi.repository import GObject

from pychess.Utils.const import (
    BLACKWON,
    WHITEWON,
    DRAW,
    UNDOABLE_STATES,
    CANCELLED,
    PRACTICE_GOAL_REACHED,
    BLACK,
    WHITE,
    LECTURE,
    LESSON,
    PUZZLE,
    ENDGAME,
)
from pychess.Savers.yacpdb_solution import (
    matching_solution_children,
    solution_nodes_after_moves,
)
from pychess.Utils.GameModel import GameModel
from pychess.Utils.lutils import lmove

learn2str = {
    LECTURE: "Lecture",
    PUZZLE: "Puzzle",
    LESSON: "Lesson",
    ENDGAME: "Endgame",
}

MATE, MATE_IN, DRAW_IN, EQUAL_IN, EVAL_IN, PROMOTION = range(6)


class Goal:
    def __init__(self, termination):
        self.termination = termination
        # print(termination)

        if termination.startswith("mate in"):
            self.result = MATE_IN
            self.moves = int(termination.split()[-1])
            self.cp = None
        elif termination.startswith("draw in"):
            self.result = DRAW_IN
            self.moves = int(termination.split()[-1])
            self.cp = None
        elif termination.startswith("equalize in"):
            self.result = EQUAL_IN
            self.moves = int(termination.split()[-1])
            self.cp = None
        elif "cp in" in termination:
            self.result = EVAL_IN
            parts = termination.split()
            self.moves = int(parts[-1])
            self.cp = int(parts[0][1:-2])
        elif "promotion with" in termination:
            self.result = PROMOTION
            self.moves = None
            parts = termination.split()
            self.cp = int(parts[-1][1:-2])
        else:
            self.result = MATE
            self.moves = None
            self.cp = None
            # print("No termination tag, expecting MATE", termination)


class LearnModel(GameModel):
    __gsignals__ = {
        # goal_checked is emitted after puzzle game goal check finished
        "goal_checked": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "learn_success": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def isChanged(self):
        """Never save learn games changes to .pgn"""
        return False

    def set_learn_data(
        self, learn_type, source, current_index=None, game_count=None, from_lesson=False
    ):
        self.learn_type = learn_type
        self.source = source
        self.current_index = current_index
        self.game_count = game_count
        self.from_lesson = from_lesson

        self.hints = {}
        self.goal = None
        self.failed_playing_best = False
        self.authored_move_checked = False
        self.authored_solution_nodes = []
        self.authored_solution_node = None

        if learn_type == LECTURE:
            self.offline_lecture = True
            self.lecture_skip_event = asyncio.Event()  # set when 'Go on' button pressed
            self.lecture_pause_event = (
                asyncio.Event()
            )  # set when 'Pause' button pressed
            self.lecture_exit_event = asyncio.Event()  # set when 'Exit' button pressed

        elif learn_type == PUZZLE:
            self.puzzle_game = True
            self.goal = Goal(self.tags["Termination"])
            if getattr(self, "authored_solution_tree", None) is not None:
                self._sync_authored_solution_nodes()
                self.connect("game_changed", self._on_authored_game_changed)
                self.connect("moves_undone", self._on_authored_moves_undone)

        elif learn_type == LESSON:
            self.lesson_game = True

        elif learn_type == ENDGAME:
            self.end_game = True

    def add_hints(self, hint):
        ply, move = hint
        self.hints[ply] = [(move, 10000)]

    def _normalized_authored_moves(self, count=None):
        if count is None:
            count = len(self.moves)
        return [
            lmove.toAN(self.boards[index].board, self.moves[index].move, short=True)
            for index in range(count)
        ]

    def _sync_authored_solution_nodes(self):
        tree = getattr(self, "authored_solution_tree", None)
        if tree is None:
            self.authored_solution_nodes = []
            self.authored_solution_node = None
            return

        nodes = solution_nodes_after_moves(tree, self._normalized_authored_moves())
        self.authored_solution_nodes = nodes
        self.authored_solution_node = nodes[0] if len(nodes) == 1 else None

    def _on_authored_game_changed(self, gamemodel, ply):
        self._sync_authored_solution_nodes()

    def _on_authored_moves_undone(self, gamemodel, moves):
        self._sync_authored_solution_nodes()

    def _check_authored_solution_move(self):
        """Validate the latest solver move against the authored tree when possible.

        Return ``None`` when prior play has already left the authored tree, in
        which case the existing engine-based Learn validation remains the
        fallback until authored defender replies are wired in.
        """
        tree = getattr(self, "authored_solution_tree", None)
        if tree is None or not self.moves:
            return None

        prefix_moves = self._normalized_authored_moves(len(self.moves) - 1)
        nodes = solution_nodes_after_moves(tree, prefix_moves)
        if not nodes:
            return None

        latest_move = self._normalized_authored_moves()[-1]
        return bool(matching_solution_children(nodes, latest_move))

    def check_failed_playing_best(self, status):
        self.authored_move_checked = False
        authored_move_ok = self._check_authored_solution_move()
        if authored_move_ok is not None:
            self.authored_move_checked = True
            return not authored_move_ok
        if self.ply - 1 in self.hints:
            best_score = self.hints[self.ply - 1][0][1]
            best_moves = [
                hint[0]
                for hint in self.hints[self.ply - 1]
                if abs(hint[1] - best_score) <= 10
            ]
        else:
            best_moves = []

        if self.puzzle_game:
            # No need to check in best moves (and let add more time to analyzer) in trivial cases
            if self.goal.result in (MATE, MATE_IN) and (
                (status == BLACKWON and self.starting_color == BLACK)
                or (status == WHITEWON and self.starting_color == WHITE)
            ):
                return False
            elif self.goal.result == DRAW_IN and status == DRAW:
                return False
            elif self.goal.result in (MATE_IN, DRAW_IN, EQUAL_IN, EVAL_IN, PROMOTION):
                expect_best = True
            else:
                expect_best = False
        else:
            expect_best = False

        failed = expect_best and self.moves[-1].as_uci() not in best_moves
        return failed

    def check_goal(self, status, reason):
        if self.end_game:
            if status in UNDOABLE_STATES:
                self.end(status, reason)
            self.emit("goal_checked")
            return

        full_moves = (self.ply - self.lowply) // 2 + 1
        # print("Is Goal not reached?", self.goal.result, status, full_moves, self.goal.moves, self.failed_playing_best, self.tags, self.hints)

        authored_move_ok = not (self.authored_move_checked and self.failed_playing_best)

        if authored_move_ok and (
            (
                self.goal.result == DRAW_IN
                and status == DRAW
                and full_moves <= self.goal.moves
            )
            or (
                self.goal.result == MATE_IN
                and status == WHITEWON
                and full_moves <= self.goal.moves
                and self.starting_color == WHITE
            )
            or (
                self.goal.result == MATE_IN
                and status == BLACKWON
                and full_moves <= self.goal.moves
                and self.starting_color == BLACK
            )
            or (
                self.goal.result in (EVAL_IN, EQUAL_IN)
                and full_moves == self.goal.moves
                and not self.failed_playing_best
            )
            or (self.goal.result == MATE and status in (WHITEWON, BLACKWON))
            or (self.goal.result == PROMOTION and self.moves[-1].promotion)
        ):
            if status in UNDOABLE_STATES:
                self.end(status, PRACTICE_GOAL_REACHED)
            else:
                self.end(CANCELLED, PRACTICE_GOAL_REACHED)
        else:
            if status in UNDOABLE_STATES:
                # print("check_goal() status in UNDOABLE_STATES -> self.end(status, reason)")
                self.failed_playing_best = True
                self.end(status, reason)
            # print("Goal not reached yet.", self.goal.result, status, full_moves, self.goal.moves, self.failed_playing_best)

        self.emit("goal_checked")
        return
