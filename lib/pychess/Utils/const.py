VERSION = "0.6"

NAME = "PyChess"

###

from os.path import isdir, join, dirname, abspath
prefixes = ("/usr/share", "/usr/local/share",
    "/usr/share/games", "/usr/local/share/games")
# TODO: Locale is not located in the lang files
localePrefixes = ("/usr/share/locale", "/usr/local/share/locale")
PREFIX = ""

if __file__.find("site-packages") >= 0:
    # We are installed?
    for prefix in prefixes:
        if isdir (join (prefix, "pychess")):
            PREFIX = join (prefix, "pychess")
            break
if not PREFIX:
    # We are local
    PREFIX = abspath (join (dirname (__file__), "../../.."))

def prefix (subpath):
    return abspath (join (PREFIX, subpath))

###

# Hint modes
HINT, SPY = range(2)
reprMode = ["hint", "spy"]

# Player types
LOCAL, ARTIFICIAL, REMOTE = range(3)

# Engine strengths
EASY, INTERMEDIATE, EXPERT = range(3)

# Engine modes
NORMAL, ANALYZING, INVERSE_ANALYZING = range(3)

# Algebraic notation types: Short, Long, Figure and Simpe
SAN, LAN, FAN, AN = range(4)

# Player colors
WHITE, BLACK = range(2)
reprColor = ["White", "Black"]

# AlphaBeta search value types
hashfALPHA, hashfBETA, hashfEXACT = range(3)

# Game states
RUNNING, DRAW, WHITEWON, BLACKWON = range(4)
reprResult = ["*", "1/2-1/2", "1-0", "0-1"]

# Castling states (logarithmic)
WHITE_OO, WHITE_OOO, BLACK_OO, \
    BLACK_OOO, WHITE_CASTLED, BLACK_CASTLED = map(lambda x: 2**x, range(6))

# Extended game states
DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, DRAW_INSUFFICIENT, \
    WON_RESIGN, WON_CALLFLAG, WON_MATE = range(8)

# Player actions
RESIGNATION, FLAG_CALL, DRAW_OFFER = range(3)

# Piece types
KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = range(6)
reprPiece = ["King", "Queen", "Rook", "Bishop", "Knight", "Pawn"]

# Piece signs
reprSign = ["K", "Q", "R", "B", "N", "P"]
chr2Sign = {"k":KING, "q": QUEEN, "r": ROOK, "b": BISHOP, "n": KNIGHT, "p":PAWN}
