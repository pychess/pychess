import collections

from .ChessFile import ChessFile
from pychess.Utils.Cord import Cord
from pychess.Utils.GameModel import GameModel
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.const import DRAW, WHITEWON, BLACKWON, WAITING_TO_START, \
    WHITE, BLACK, KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN

__label__ = _("Chess Compositions from yacpdb.org")
__ending__ = "olv"
__append__ = True


# Note S for the knights as N is reserverd for Nightriders
chr2piece = {"K": KING,
             "Q": QUEEN,
             "R": ROOK,
             "B": BISHOP,
             "S": KNIGHT,
             "P": PAWN,
             }


def save(handle, model, position=None):
    pass


def load(handle):
    return OLVFile(handle)


class OLVFile(ChessFile):
    def __init__(self, handle):
        ChessFile.__init__(self, handle)

        self.games = self.read_games(handle)
        self.count = len(self.games)

    def read_games(self, handle):
        """ We don't return games if stipulation is not 'mate in #' """
        games = []
        rec = None
        rec_id = 1
        contains_fairy_pieces = False

        # authors is a more line list (each line starts with "-")
        in_authors = False

        # piece list are usually in one line list inside []
        # but sometimes given in more line lists
        in_white = False
        in_black = False

        for line in handle:
            line = line.rstrip()

            if in_authors and ":" in line:
                in_authors = False

            elif in_white and ":" in line:
                in_white = False

            elif in_black and ":" in line:
                in_black = False
                rec["FEN"] = self.lboard.asFen()

            # New record start
            if line == "---":
                if rec is not None and rec["Black"].startswith("Mate in ") and not contains_fairy_pieces:
                    games.append(rec)
                    rec_id += 1

                contains_fairy_pieces = False

                self.lboard = LBoard()
                self.lboard.applyFen("8/8/8/8/8/8/8/8 w - - 0 1")

                rec = collections.defaultdict(str)
                rec["Id"] = rec_id
                rec["Offset"] = 0

            elif line.startswith("authors:"):
                in_authors = True

            elif line.startswith("source:"):
                rec["Event"] = line[8:]

            elif line.startswith("source-id:"):
                rec["Event"] = "%s (%s)" % (rec["Event"], line[12:])

            elif line.startswith("date:"):
                parts = line[6:].split("-")
                parts_len = len(parts)
                if parts_len >= 3:
                    rec["Day"] = parts[2]
                if parts_len >= 2:
                    rec["Month"] = parts[1]
                if parts_len >= 1:
                    rec["Year"] = parts[0]

            elif line.startswith("distinction:"):
                rec["Site"] = line[12:]

            elif line.startswith("algebraic:"):
                pass

            elif line.startswith("  white:"):
                parts = line.split("[")
                if len(parts) > 1:
                    pieces = parts[1][:-1]
                    for piece in pieces.split(", "):
                        if piece.startswith("Royal") or piece[0] not in chr2piece:
                            contains_fairy_pieces = True
                        else:
                            cord = Cord(piece[1:3]).cord
                            piece = chr2piece[piece[0]]
                            self.lboard._addPiece(cord, piece, WHITE)
                else:
                    in_white = True

            elif line.startswith("  black:"):
                parts = line.split("[")
                if len(parts) > 1:
                    pieces = parts[1][:-1]
                    for piece in pieces.split(", "):
                        if piece.startswith("Royal") or piece[0] not in chr2piece:
                            contains_fairy_pieces = True
                        else:
                            cord = Cord(piece[1:3]).cord
                            piece = chr2piece[piece[0]]
                            self.lboard._addPiece(cord, piece, BLACK)

                    rec["FEN"] = self.lboard.asFen()
                else:
                    in_black = True

            elif line.startswith("stipulation:"):
                if line.endswith("Black to move"):
                    line = line[:-14]
                    rec["FEN"] = rec["FEN"].replace("w", "b")

                line = line.split(": ")[1]
                if "+" in line:
                    rec["Result"] = WHITEWON
                    rec["Black"] = "Win"
                elif "-" in line:
                    rec["Result"] = BLACKWON
                    rec["Black"] = "Win"
                elif "=" in line:
                    rec["Result"] = DRAW
                    rec["Black"] = "Draw"
                elif line.startswith('"#'):
                    rec["Result"] = WHITEWON
                    rec["Black"] = "Mate in %s" % line[2:-1]
                    rec["Termination"] = "mate in %s" % line[2:-1]

            elif line.startswith("solution:"):
                # TODO: solutions can be in several (sometimes rather unusual) form
                pass

            else:
                if in_authors:
                    author = line[line.find("-") + 1:].lstrip()
                    if rec["White"]:
                        rec["White"] = "%s - %s" % (rec["White"], author)
                    else:
                        rec["White"] = author

                elif in_white:
                    piece = line[line.find("-") + 1:].lstrip()
                    cord = Cord(piece[1:3]).cord
                    piece = chr2piece[piece[0]]
                    self.lboard._addPiece(cord, piece, WHITE)

                elif in_black:
                    piece = line[line.find("-") + 1:].lstrip()
                    cord = Cord(piece[1:3]).cord
                    piece = chr2piece[piece[0]]
                    self.lboard._addPiece(cord, piece, BLACK)

        # Append the latest record
        if rec is not None and rec["Black"].startswith("Mate in ") and not contains_fairy_pieces:
            games.append(rec)

        return games

    def loadToModel(self, rec, position, model=None):
        if not model:
            model = GameModel()

        model.tags['Event'] = rec["Event"]
        model.tags['Site'] = rec["Site"]
        model.tags['Date'] = self.get_date(rec)
        model.tags['Round'] = ""
        model.tags['White'] = "?"
        model.tags['Black'] = "?"
        model.tags['Termination'] = rec["Termination"]

        fen = rec["FEN"]

        model.boards = [model.variant(setup=fen)]
        model.variations = [model.boards]
        model.status = WAITING_TO_START

        return model

    def get_date(self, rec):
        year = rec['Year']
        month = rec['Month']
        day = rec['Day']
        if year and month and day:
            tag_date = "%s.%02d.%02d" % (year, int(month), int(day))
        elif year and month:
            tag_date = "%s.%02d" % (year, int(month))
        elif year:
            tag_date = "%s" % year
        else:
            tag_date = ""
        return tag_date
