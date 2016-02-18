from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from pychess.compat import strip
from .ChessFile import ChessFile, LoadingError
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import WHITE, BLACK, WON_RESIGN, WAITING_TO_START, BLACKWON, WHITEWON, DRAW
from pychess.Utils.logic import getStatus
from pychess.Utils.lutils.leval import evaluateComplete

__label__ = _("Chess Position")
__ending__ = "epd"
__append__ = True


def save(file, model, position=None):
    """Saves game to file in fen format"""

    color = model.boards[-1].color

    fen = model.boards[-1].asFen().split(" ")

    # First four parts of fen are the same in epd
    file.write(" ".join(fen[:4]))

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
        file.write(" %s %s;" % (key, value))

    ############################################################################
    # Resign opcode                                                            #
    ############################################################################
    if model.status in (WHITEWON, BLACKWON) and model.reason == WON_RESIGN:
        file.write(" resign;")

    print("", file=file)
    file.close()


def load(file):
    return EpdFile([line.strip() for line in file if line])


class EpdFile(ChessFile):
    def loadToModel(self, gameno, position, model=None):
        if not model:
            model = GameModel()

        fieldlist = self.games[gameno].split(" ")
        if len(fieldlist) == 4:
            fen = self.games[gameno]
            opcodestr = ""

        elif len(fieldlist) > 4:
            fen = " ".join(fieldlist[:4])
            opcodestr = " ".join(fieldlist[4:])

        else:
            raise LoadingError("EPD string can not have less than 4 field")

        opcodes = {}
        for opcode in map(strip, opcodestr.split(";")):
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

    def get_player_names(self, gameno):
        data = self.games[gameno]

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
