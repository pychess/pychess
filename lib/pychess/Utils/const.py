VERSION = "0.5.2"

NAME = "PyChess"

###

from os.path import isdir, join, dirname, abspath
prefixes = ("/usr/share", "/usr/local/share", "/usr/share/games", "/usr/local/share/games")
# TODO: Locale is not located in the lang files
localePrefixes = ("/usr/share/locale", "/usr/local/share/locale")
PREFIX = ""

if __file__.find("site-packages") >= 0:
    # We are installed?
    for prefix in prefixes:
        if isdir (join (prefix, "pychess")):
            PREFIX = prefix
            break
if not PREFIX:
    # We are local
    PREFIX = abspath (join (dirname (__file__), "../../.."))

def prefix (subpath):
    return abspath (join (PREFIX, subpath))

###

WHITE, BLACK = range(2)

reprColor = ["White", "Black"]

RUNNING, DRAW, WHITEWON, BLACKWON = range(4)

reprResult = ["*", "1/2-1/2", "1-0", "0-1"]

DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, \
    WON_RESIGN, WON_CALLFLAG, WON_MATE = range(7)

KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = range(6)

reprSign = ["K", "Q", "R", "B", "N", "P"]
reprPiece = ["King", "Queen", "Rook", "Bishop", "Knight", "Pawn"]
chr2Sign = {"k":KING, "q": QUEEN, "r": ROOK, "b": BISHOP, "n": KNIGHT, "p":PAWN}

WHITE_OO, WHITE_OOO, BLACK_OO, \
    BLACK_OOO, WHITE_CASTLED, BLACK_CASTLED = map(lambda x: 2**x, range(6))
