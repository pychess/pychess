# -*- coding: UTF-8 -*-
from __future__ import unicode_literals


NAME = "PyChess"

# Player types
LOCAL, ARTIFICIAL, REMOTE = range(3)

# Engine strengths
EASY, INTERMEDIATE, EXPERT = range(3)

# Player colors
WHITE, BLACK = range(2)

# Game states
WAITING_TO_START, PAUSED, RUNNING, DRAW, WHITEWON, BLACKWON, KILLED, \
    ADJOURNED, ABORTED, UNKNOWN_STATE = range(10)
reprResult = ["*", "*", "*", "1/2-1/2", "1-0", "0-1", "*", "*", "*", "*"]

UNDOABLE_STATES = (DRAW, WHITEWON, BLACKWON)
UNFINISHED_STATES = (WAITING_TO_START, PAUSED, RUNNING, UNKNOWN_STATE)

# Chess variants
NORMALCHESS, CORNERCHESS, SHUFFLECHESS, FISCHERRANDOMCHESS, RANDOMCHESS, \
    ASYMMETRICRANDOMCHESS, UPSIDEDOWNCHESS, PAWNSPUSHEDCHESS, PAWNSPASSEDCHESS, \
    THEBANCHESS, PAWNODDSCHESS, KNIGHTODDSCHESS, ROOKODDSCHESS, QUEENODDSCHESS, \
    BLINDFOLDCHESS, HIDDENPAWNSCHESS, HIDDENPIECESCHESS, ALLWHITECHESS, \
    ATOMICCHESS, BUGHOUSECHESS, CRAZYHOUSECHESS, LOSERSCHESS, SUICIDECHESS, \
    WILDCASTLECHESS, WILDCASTLESHUFFLECHESS, KINGOFTHEHILLCHESS, THREECHECKCHESS, \
    ASEANCHESS, MAKRUKCHESS, SITTUYINCHESS, CAMBODIANCHESS, AIWOKCHESS, \
    EUROSHOGICHESS, SETUPCHESS = range(34)

ASEAN_VARIANTS = (ASEANCHESS, MAKRUKCHESS, CAMBODIANCHESS, AIWOKCHESS,
                  SITTUYINCHESS)
DROP_VARIANTS = (BUGHOUSECHESS, CRAZYHOUSECHESS, EUROSHOGICHESS, SITTUYINCHESS,
                 SETUPCHESS)
UNSUPPORTED = (BUGHOUSECHESS, AIWOKCHESS, EUROSHOGICHESS, SETUPCHESS)

# Chess variant groups
VARIANTS_BLINDFOLD, VARIANTS_ODDS, VARIANTS_SHUFFLE, VARIANTS_OTHER, \
    VARIANTS_OTHER_NONSTANDARD, VARIANTS_ASEAN = range(6)

# Action errors
ACTION_ERROR_NOT_OUT_OF_TIME, \
    ACTION_ERROR_CLOCK_NOT_STARTED, ACTION_ERROR_SWITCH_UNDERWAY, \
    ACTION_ERROR_CLOCK_NOT_PAUSED, ACTION_ERROR_TOO_LARGE_UNDO, \
    ACTION_ERROR_NONE_TO_ACCEPT, ACTION_ERROR_NONE_TO_WITHDRAW, \
    ACTION_ERROR_NONE_TO_DECLINE, = range(8)

# Game state reasons
ABORTED_ADJUDICATION, ABORTED_AGREEMENT, ABORTED_COURTESY, ABORTED_EARLY, \
    ABORTED_SERVER_SHUTDOWN, ADJOURNED_COURTESY, ABORTED_DISCONNECTION, \
    ADJOURNED_AGREEMENT, ADJOURNED_LOST_CONNECTION, ADJOURNED_SERVER_SHUTDOWN, \
    ADJOURNED_COURTESY_WHITE, ADJOURNED_COURTESY_BLACK, \
    ADJOURNED_LOST_CONNECTION_WHITE, ADJOURNED_LOST_CONNECTION_BLACK, \
    DRAW_50MOVES, DRAW_ADJUDICATION, DRAW_AGREE, DRAW_CALLFLAG, DRAW_INSUFFICIENT, \
    DRAW_EQUALMATERIAL, DRAW_LENGTH, DRAW_REPITITION, DRAW_STALEMATE, \
    DRAW_BLACKINSUFFICIENTANDWHITETIME, DRAW_WHITEINSUFFICIENTANDBLACKTIME, \
    WON_ADJUDICATION, WON_CALLFLAG, WON_DISCONNECTION, WON_MATE, WON_RESIGN, \
    WON_LESSMATERIAL, WON_NOMATERIAL, WON_KINGEXPLODE, WON_KINGINCENTER, \
    WON_THREECHECK, \
    WHITE_ENGINE_DIED, BLACK_ENGINE_DIED, DISCONNECTED, UNKNOWN_REASON = range(39)

UNDOABLE_REASONS = (DRAW_50MOVES, DRAW_INSUFFICIENT, DRAW_LENGTH,
                    DRAW_REPITITION, DRAW_STALEMATE, DRAW_AGREE, DRAW_CALLFLAG,
                    DRAW_BLACKINSUFFICIENTANDWHITETIME,
                    DRAW_WHITEINSUFFICIENTANDBLACKTIME,
                    WON_MATE, WON_NOMATERIAL, WON_CALLFLAG, WON_RESIGN)

UNRESUMEABLE_REASONS = (DRAW_50MOVES, DRAW_INSUFFICIENT, DRAW_LENGTH,
                        DRAW_REPITITION, DRAW_STALEMATE, WON_MATE, WON_NOMATERIAL)

# Player actions
RESIGNATION = "resignation"
FLAG_CALL = "flag call"
DRAW_OFFER = "draw offer"
ABORT_OFFER = "abort offer"
ADJOURN_OFFER = "adjourn offer"
PAUSE_OFFER = "pause offer"
RESUME_OFFER = "resume offer"
SWITCH_OFFER = "switch offer"
TAKEBACK_OFFER = "takeback offer"
MATCH_OFFER = "match offer"
HURRY_ACTION = "hurry action"
CHAT_ACTION = "chat action"

ACTIONS = (RESIGNATION, FLAG_CALL, DRAW_OFFER, ABORT_OFFER, ADJOURN_OFFER,
           PAUSE_OFFER, RESUME_OFFER, SWITCH_OFFER, TAKEBACK_OFFER,
           MATCH_OFFER, HURRY_ACTION, CHAT_ACTION)
OFFERS = (DRAW_OFFER, ABORT_OFFER, ADJOURN_OFFER, PAUSE_OFFER,
          RESUME_OFFER, SWITCH_OFFER, TAKEBACK_OFFER, MATCH_OFFER)
INGAME_ACTIONS = (RESIGNATION, FLAG_CALL, DRAW_OFFER, ABORT_OFFER,
                  ADJOURN_OFFER, PAUSE_OFFER, SWITCH_OFFER, HURRY_ACTION)

# A few nice to have boards
FEN_EMPTY = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
FEN_START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Search values

hashfALPHA, hashfBETA, hashfEXACT, hashfBAD = range(4)

# Engine modes
NORMAL, ANALYZING, INVERSE_ANALYZING = range(3)

# Piece types

# BPAWN is a pawn that moves in the opposite direction
EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, BPAWN, \
    ASEAN_WBISHOP, ASEAN_BBISHOP, ASEAN_QUEEN = range(11)

# Is sliding piece
sliders = [False, False, False, True, True, True, False, False, False, False,
           False]

# Piece signs
reprSign = ["", "P", "N", "B", "R", "Q", "K"]
reprSignMakruk = ["", "P", "N", "S", "R", "M", "K"]
reprSignSittuyin = ["", "P", "N", "S", "R", "F", "K"]
chr2Sign = {"k": KING,
            "q": QUEEN,
            "r": ROOK,
            "b": BISHOP,
            "n": KNIGHT,
            "p": PAWN,
            "m": QUEEN,
            "s": BISHOP,
            "f": QUEEN}
chrU2Sign = {"K": KING,
             "Q": QUEEN,
             "R": ROOK,
             "B": BISHOP,
             "N": KNIGHT,
             "P": PAWN,
             "M": QUEEN,
             "S": BISHOP,
             "F": QUEEN}

# Move values
NORMAL_MOVE, QUEEN_CASTLE, KING_CASTLE, ENPASSANT, \
    KNIGHT_PROMOTION, BISHOP_PROMOTION, ROOK_PROMOTION, \
    QUEEN_PROMOTION, KING_PROMOTION, NULL_MOVE, DROP = range(11)
PROMOTIONS = (KING_PROMOTION, QUEEN_PROMOTION, ROOK_PROMOTION,
              BISHOP_PROMOTION, KNIGHT_PROMOTION)

# Algebraic notation types: Short, Long, Figure and Simpe
SAN, LAN, FAN, AN = range(4)
# Castling notation types: e.g., O-O, e1g1, e1h1
CASTLE_SAN, CASTLE_KK, CASTLE_KR = range(3)

FAN_PIECES = [
    ["", "♙", "♘", "♗", "♖", "♕", "♔", ""],
    ["", "♟", "♞", "♝", "♜", "♛", "♚", ""]
]

# Castling values
W_OO, W_OOO, B_OO, B_OOO = [2**i for i in range(4)]
CAS_FLAGS = ((W_OOO, W_OO), (B_OOO, B_OO))
W_CASTLED, B_CASTLED = [2**i for i in range(2)]

# Cords types
A1, B1, C1, D1, E1, F1, G1, H1,\
    A2, B2, C2, D2, E2, F2, G2, H2,\
    A3, B3, C3, D3, E3, F3, G3, H3,\
    A4, B4, C4, D4, E4, F4, G4, H4,\
    A5, B5, C5, D5, E5, F5, G5, H5,\
    A6, B6, C6, D6, E6, F6, G6, H6,\
    A7, B7, C7, D7, E7, F7, G7, H7,\
    A8, B8, C8, D8, E8, F8, G8, H8 = range(64)

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

# User interface

# Hint modes
OPENING, ENDGAME, HINT, SPY = ["opening", "endgame", "hint", "spy"]

# Sound settings
SOUND_MUTE, SOUND_BEEP, SOUND_SELECT, SOUND_URI = range(4)

# Brush types. Send piece object for Piece brush
CLEAR, ENPAS = range(2)

# Main menu items
GAME_MENU_ITEMS = ("save_game1", "save_game_as1", "share_game",
                   "export_position1", "analyze_game1", "properties1",
                   "close1")
ACTION_MENU_ITEMS = ("abort", "adjourn", "draw", "pause1", "resume1", "undo1",
                     "call_flag", "resign", "ask_to_move")
VIEW_MENU_ITEMS = ("rotate_board1", "show_sidepanels", "hint_mode", "spy_mode")
EDIT_MENU_ITEMS = ("copy_pgn", "copy_fen", )
MENU_ITEMS = GAME_MENU_ITEMS + ACTION_MENU_ITEMS + VIEW_MENU_ITEMS + EDIT_MENU_ITEMS

# Subprocess
SUBPROCESS_PTY, SUBPROCESS_SUBPROCESS, SUBPROCESS_FORK = range(3)
