import asyncio

from gi.repository import GObject

from pychess.Utils.const import LOCAL, RUNNING
from pychess.Utils.DecisionSupportAlgorithm import DecisionSupportAlgorithm
from pychess.Variants.setupposition import SetupBoard


class SetupMove:
    def __init__(self, move):
        self.cord0 = move[0]
        self.cord1 = move[1]
        self.flag = 0

    def is_capture(self, board):
        return False


class SetupPlayer:
    __type__ = LOCAL

    def __init__(self, board_control):
        self.queue = asyncio.Queue()
        self.board_control = board_control
        self.board_control.connect("action", self.on_action)
        self.board_control.connect("piece_moved", self.piece_moved)

    def on_action(self, bc, action, player, param):
        self.queue.put_nowait((action, param))
        if action == "SETUP":
            # force both virtual player to make_move()
            self.queue.put_nowait((action, param))

    async def make_move(self):
        item = await self.queue.get()
        return item

    def piece_moved(self, board, move, color):
        self.queue.put_nowait((SetupMove(move), color))


class SetupModel(GObject.GObject):
    __gsignals__ = {
        "game_started": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "game_changed": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "moves_undoing": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        "variation_undoing": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "game_loading": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "game_loaded": (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        "game_ended": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.stop = False
        self.lowply = 0
        self.status = RUNNING
        self.players = []
        self.moves = []
        self.variant = SetupBoard
        self.boards = [self.variant()]
        self.variations = [self.boards]

        self.lesson_game = False

        self.support_algorithm = DecisionSupportAlgorithm()

    def _get_ply(self):
        return self.boards[-1].ply

    ply = property(_get_ply)

    def getBoardAtPly(self, ply, variation=0):
        return self.boards[ply]

    def getMoveAtPly(self, ply, variation=0):
        return self.moves[ply]

    def isPlayingICSGame(self):
        # prevent hovering over fields
        return True

    def receiveSupportAlgorithm(self, x):
        return

    def start(self):
        async def coro():
            self.emit("game_started")
            while True:
                player0, player1 = await self.curplayer.make_move()

                if isinstance(player0, SetupMove):
                    # print(player0.cord0, player0.cord1, player1)
                    new_board = self.boards[-1].move(player0, player1)
                    self.moves.append(player0)
                    self.boards.append(new_board)
                    self.emit("game_changed", self.ply)
                elif player0 == "SETUP":
                    # print("SETUP", player0, player1)
                    self.emit("game_ended", 0)
                    self.boards = [self.variant(setup=player1)]
                    self.variations = [self.boards]
                    self.emit("game_loaded", 0)
                    self.emit("game_started")
                    self.emit("game_changed", 0)
                elif player0 == "CLOSE":
                    # print("CLOSE")
                    break

        asyncio.get_event_loop().create_task(coro())
