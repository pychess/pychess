# -*- coding: UTF-8 -*-

################################################################################
# PyChess information                                                          #
################################################################################

VERSION = "0.7"

NAME = "PyChess"

################################################################################
# File locating                                                                #
################################################################################

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

################################################################################
# Player info                                                                  #
################################################################################

# Player types
LOCAL, ARTIFICIAL, REMOTE = range(3)

# Engine strengths
EASY, INTERMEDIATE, EXPERT = range(3)

# Player colors
WHITE, BLACK = range(2)
reprColor = ["White", "Black"]

################################################################################
# Game values                                                                  #
################################################################################

# Game states
WAITING_TO_START, PAUSED, RUNNING, DRAW, WHITEWON, BLACKWON, KILLED, \
        UNKNOWN_STATE = range(8)
reprResult = ["*", "*", "*", "1/2-1/2", "1-0", "0-1", "*", "?"]

# Time calling errors
NO_TIME_SETTINGS, NOT_OUT_OF_TIME = range(2)

# Game state reasons
DRAW_REPITITION, DRAW_50MOVES, DRAW_STALEMATE, DRAW_AGREE, DRAW_INSUFFICIENT, \
    WON_RESIGN, WON_CALLFLAG, WON_MATE, UNKNOWN_REASON = range(9)

# Player actions
RESIGNATION, FLAG_CALL, DRAW_OFFER = range(3)

# A few nice to have boards
FEN_EMPTY = "8/8/8/8/8/8/8/8 w KQkq - 0 1"
FEN_START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

################################################################################
# Search values                                                                #
################################################################################

hashfALPHA, hashfBETA, hashfEXACT = range(3)

# Engine modes
NORMAL, ANALYZING, INVERSE_ANALYZING = range(3)

################################################################################
# Piece types                                                                  #
################################################################################

# BPAWN is a pawn that moves in the opposite direction
EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, BPAWN = range(8)
reprPiece = ["Empty", "Pawn", "Knight", "Bishop", "Rook", "Queen", "King", "BPawn"]

# Is sliding piece
sliders = [ False, False, False, True, True, True, False, False ]

# Piece signs
reprSign = ["", "P", "N", "B", "R", "Q", "K"]
chr2Sign = {"k":KING, "q": QUEEN, "r": ROOK, "b": BISHOP, "n": KNIGHT, "p":PAWN}

# TODO: localReprSign

################################################################################
# Move values                                                                  #
################################################################################

NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, CAPTURE, ENPASSANT, \
KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, QUEEN_PROMOTION = range(9)

# Algebraic notation types: Short, Long, Figure and Simpe
SAN, LAN, FAN, AN = range(4)

FAN_PIECES = [
    ["♔", "♕", "♖", "♗", "♘", "♙"],
    ["♚", "♛", "♜", "♝", "♞", "♟"]
]

################################################################################
# Castling values                                                              #
################################################################################
W_OO, W_OOO, B_OO, B_OOO = [2**i for i in range(4)]
W_CASTLED, B_CASTLED = [2**i for i in range(2)]

################################################################################
# Cords types                                                                  #
################################################################################

A1, B1, C1, D1, E1, F1, G1, H1, \
A2, B2, C2, D2, E2, F2, G2, H2, \
A3, B3, C3, D3, E3, F3, G3, H3, \
A4, B4, C4, D4, E4, F4, G4, H4, \
A5, B5, C5, D5, E5, F5, G5, H5, \
A6, B6, C6, D6, E6, F6, G6, H6, \
A7, B7, C7, D7, E7, F7, G7, H7, \
A8, B8, C8, D8, E8, F8, G8, H8 = range (64)

reprCord = [
    "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
    "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
    "a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3",
    "a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4",
    "a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5",
    "a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6",
    "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
    "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8"
]

reprFile = ["a", "b", "c", "d", "e", "f", "g", "h"]
reprRank = ["1", "2", "3", "4", "5", "6", "7", "8"]

cordDic = {}
for cord, name in enumerate(reprCord):
    cordDic[name] = cord

################################################################################
# User interface                                                               #
################################################################################

# Hint modes
HINT, SPY = range(2)
reprMode = ["hint", "spy"]

# Sound settings
MUTE, BEEP, SELECT, URI = range(4)

# Brush types. Send piece object for Piece brush
CLEAR, ENPAS = range(2)
