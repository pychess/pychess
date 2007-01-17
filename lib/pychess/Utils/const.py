VERSION = "0.7"

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

W_OO, W_OOO, B_OO, B_OOO, W_CASTLED, B_CASTLED = [2**i for i in range(6)]

# Extended game states
DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, DRAW_INSUFFICIENT, \
    WON_RESIGN, WON_CALLFLAG, WON_MATE = range(8)

# Player actions
RESIGNATION, FLAG_CALL, DRAW_OFFER = range(3)

# Piece types
#KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = range(6)
reprPiece = ["King", "Queen", "Rook", "Bishop", "Knight", "Pawn"]

# BPAWN is a pawn that moves in the opposite direction
EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, BPAWN = range(8)

A1, B1, C1, D1, E1, F1, G1, H1, \
A2, B2, C2, D2, E2, F2, G2, H2, \
A3, B3, C3, D3, E3, F3, G3, H3, \
A4, B4, C4, D4, E4, F4, G4, H4, \
A5, B5, C5, D5, E5, F5, G5, H5, \
A6, B6, C6, D6, E6, F6, G6, H6, \
A7, B7, C7, D7, E7, F7, G7, H7, \
A8, B8, C8, D8, E8, F8, G8, H8 = range (64)

cordRepr = [
    "A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1",
    "A2", "B2", "C2", "D2", "E2", "F2", "G2", "H2",
    "A3", "B3", "C3", "D3", "E3", "F3", "G3", "H3",
    "A4", "B4", "C4", "D4", "E4", "F4", "G4", "H4",
    "A5", "B5", "C5", "D5", "E5", "F5", "G5", "H5",
    "A6", "B6", "C6", "D6", "E6", "F6", "G6", "H6",
    "A7", "B7", "C7", "D7", "E7", "F7", "G7", "H7",
    "A8", "B8", "C8", "D8", "E8", "F8", "G8", "H8"
]

# Piece signs
reprSign = ["K", "Q", "R", "B", "N", "P"]
chr2Sign = {"k":KING, "q": QUEEN, "r": ROOK, "b": BISHOP, "n": KNIGHT, "p":PAWN}

# Sound settings
MUTE, BEEP, SELECT, URI = range(4)

# Brush types. Send piece object for Piece brush
CLEAR, ENPAS = range(2)
