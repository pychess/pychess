import collections

from .ChessFile import ChessFile, LoadingError
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import WHITE, BLACK, WON_RESIGN, WAITING_TO_START, BLACKWON, WHITEWON, DRAW, FISCHERRANDOMCHESS
from pychess.Utils.logic import getStatus
from pychess.Utils.lutils.leval import evaluateComplete
from pychess.Variants.fischerandom import FischerandomBoard

__label__ = _("Chess Position")
__ending__ = "epd"
__append__ = True


def save(handle, model, position=None, flip=False):
    """Saves game to file in fen format"""

    color = model.boards[-1].color

    fen = model.boards[-1].asFen().split(" ")

    # First four parts of fen are the same in epd
    handle.write(" ".join(fen[:4]))

    ############################################################################
    # Repetition count                                                         #
    ############################################################################
    rep_count = model.boards[-1].board.repetitionCount()

    ############################################################################
    # Centipawn evaluation                                                     #
    ############################################################################
    if model.status == WHITEWON:
        if color == WHITE:
            ceval = 32766
        else:
            ceval = -32766
    elif model.status == BLACKWON:
        if color == WHITE:
            ceval = -32766
        else:
            ceval = 32766
    elif model.status == DRAW:
        ceval = 0
    else:
        ceval = evaluateComplete(model.boards[-1].board, model.boards[-1].color)

    ############################################################################
    # Opcodes                                                                  #
    ############################################################################
    opcodes = (
        ("fmvn", fen[5]),  # In fen full move number is the 6th field
        ("hmvc", fen[4]),  # In fen halfmove clock is the 5th field

        # Email and name of receiver and sender. We don't know the email.
        ("tcri", "?@?.? %s" % repr(model.players[color]).replace(";", "")),
        ("tcsi", "?@?.? %s" % repr(model.players[1 - color]).replace(";", "")),
        ("ce", ceval),
        ("rc", rep_count), )

    for key, value in opcodes:
        handle.write(" %s %s;" % (key, value))

    ############################################################################
    # Resign opcode                                                            #
    ############################################################################
    if model.status in (WHITEWON, BLACKWON) and model.reason == WON_RESIGN:
        handle.write(" resign;")

    print("", file=handle)
    handle.close()


def load(handle):
    return EpdFile(handle)


class EpdFile(ChessFile):
    def __init__(self, handle):
        ChessFile.__init__(self, handle)

        self.games = [self.create_rec(line.strip()) for line in handle if line]
        self.count = len(self.games)

    def create_rec(self, line):
        rec = collections.defaultdict(str)
        rec["Id"] = 0
        rec["Offset"] = 0
        rec["FEN"] = line

        castling = rec["FEN"].split()[2]
        for letter in castling:
            if letter.upper() in "ABCDEFGH":
                rec["Variant"] = FISCHERRANDOMCHESS
                break

        return rec

    def loadToModel(self, rec, position, model=None):
        if not model:
            model = GameModel()

        if "Variant" in rec:
            model.variant = FischerandomBoard

        fieldlist = rec["FEN"].split(" ")
        if len(fieldlist) == 4:
            fen = rec["FEN"]
            opcodestr = ""

        elif len(fieldlist) > 4:
            fen = " ".join(fieldlist[:4])
            opcodestr = " ".join(fieldlist[4:])

        else:
            raise LoadingError("EPD string can not have less than 4 field")

        opcodes = {}
        for opcode in map(str.strip, opcodestr.split(";")):
            space = opcode.find(" ")
            if space == -1:
                opcodes[opcode] = True
            else:
                opcodes[opcode[:space]] = opcode[space + 1:]

        if "hmvc" in opcodes:
            fen += " " + opcodes["hmvc"]
        else:
            fen += " 0"

        if "fmvn" in opcodes:
            fen += " " + opcodes["fmvn"]
        else:
            fen += " 1"

        model.boards = [model.variant(setup=fen)]
        model.variations = [model.boards]
        model.status = WAITING_TO_START

        # rc is kinda broken
        # if "rc" in opcodes:
        #    model.boards[0].board.rc = int(opcodes["rc"])

        if "resign" in opcodes:
            if fieldlist[1] == "w":
                model.status = BLACKWON
            else:
                model.status = WHITEWON
            model.reason = WON_RESIGN

        if model.status == WAITING_TO_START:
            status, reason = getStatus(model.boards[-1])
            if status in (BLACKWON, WHITEWON, DRAW):
                model.status, model.reason = status, reason

        return model

    def get_player_names(self, rec):
        data = rec["FEN"]

        names = {}

        for key in "tcri", "tcsi":
            keyindex = data.find(key)
            if keyindex == -1:
                names[key] = _("Unknown")
            else:
                sem = data.find(";", keyindex)
                if sem == -1:
                    opcode = data[keyindex + len(key) + 1:]
                else:
                    opcode = data[keyindex + len(key) + 1:sem]
                name = opcode.split(" ", 1)[1]
                names[key] = name

        color = data.split(" ")[1] == "b" and BLACK or WHITE

        if color == WHITE:
            return (names["tcri"], names["tcsi"])
        else:
            return (names["tcsi"], names["tcri"])
