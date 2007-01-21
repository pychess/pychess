from pychess.Utils.const import *
from bitboard import *
from sys import maxint

################################################################################
################################################################################
##   Evaluating constants                                                     ##
################################################################################
################################################################################

PAWN_VALUE = 100
KNIGHT_VALUE = 300
BISHOP_VALUE = 330
ROOK_VALUE = 500
QUEEN_VALUE = 900
KING_VALUE = maxint
PIECE_VALUES = (None, PAWN_VALUE, KNIGHT_VALUE,
				BISHOP_VALUE, ROOK_VALUE, QUEEN_VALUE, KING_VALUE)

# How many points does it give to have the piece standing i cords from the
# opponent king
pawnTScale = [0, 40, 20, 12, 9, 6, 4, 2, 1, 0]
bishopTScale = [0, 50, 25, 15, 7, 5, 3, 2, 2, 1]
knightTScale = [0, 50, 70, 35, 10, 3, 2, 2, 1, 1]
rookTScale = [0, 50, 40, 15, 5, 2, 1, 1, 1, 0]
queenTScale = [0, 100, 60, 20, 10, 7, 5, 4, 3, 2]

from math import sqrt

distance = [[0]*64 for i in range(64)]
for fcord in range(64):
    for tcord in range(64):
        fx = fcord >> 3
        fy = fcord & 7
        tx = tcord >> 3
        ty = tcord & 7
        distance[fcord][tcord] = int(sqrt((fx-tx)**2+(fy-ty)**2))

################################################################################
################################################################################
##   Array boards                                                             ##
################################################################################
################################################################################

shift00 = [
    56, 56, 56, 56, 56, 56, 56, 56,
    48, 48, 48, 48, 48, 48, 48, 48,
    40, 40, 40, 40, 40, 40, 40, 40,
    32, 32, 32, 32, 32, 32, 32, 32,
    24, 24, 24, 24, 24, 24, 24, 24,
    16, 16, 16, 16, 16, 16, 16, 16,
     8,  8,  8,  8,  8,  8,  8,  8,
     0,  0,  0,  0,  0,  0,  0,  0
]

r90 = [
    A8, A7, A6, A5, A4, A3, A2, A1,
    B8, B7, B6, B5, B4, B3, B2, B1,
    C8, C7, C6, C5, C4, C3, C2, C1,
    D8, D7, D6, D5, D4, D3, D2, D1,
    E8, E7, E6, E5, E4, E3, E2, E1,
    F8, F7, F6, F5, F4, F3, F2, F1,
    G8, G7, G6, G5, G4, G3, G2, G1,
    H8, H7, H6, H5, H4, H3, H2, H1
]

shift90 = [
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56,
    0, 8, 16, 24, 32, 40, 48, 56
]

r45 = [
    E4, F3, H2, C2, G1, D1, B1, A1,
    E5, F4, G3, A3, D2, H1, E1, C1,
    D6, F5, G4, H3, B3, E2, A2, F1, 
    B7, E6, G5, H4, A4, C3, F2, B2,
    G7, C7, F6, H5, A5, B4, D3, G2, 
    C8, H7, D7, G6, A6, B5, C4, E3, 
    F8, D8, A8, E7, H6, B6, C5, D4, 
    H8, G8, E8, B8, F7, A7, C6, D5
]

shift45 = [
    28, 36, 43, 49, 54, 58, 61, 63,
    21, 28, 36, 43, 49, 54, 58, 61,
    15, 21, 28, 36, 43, 49, 54, 58,
    10, 15, 21, 28, 36, 43, 49, 54,
     6, 10, 15, 21, 28, 36, 43, 49,
     3,  6, 10, 15, 21, 28, 36, 43,
     1,  3,  6, 10, 15, 21, 28, 36,
     0,  1,  3,  6, 10, 15, 21, 28
]

mask45 = [
    0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01,
    0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 
    0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 
    0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 
    0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 
    0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 
    0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 
    0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF
]

r315 = [
    A1, C1, F1, B2, G2, E3, D4, D5,
    B1, E1, A2, F2, D3, C4, C5, C6,
    D1, H1, E2, C3, B4, B5, B6, A7,
    G1, D2, B3, A4, A5, A6, H6, F7,
    C2, A3, H3, H4, H5, G6, E7, B8,
    H2, G3, G4, G5, F6, D7, A8, E8,
    F3, F4, F5, E6, C7, H7, D8, G8,
    E4, E5, D6, B7, G7, C8, F8, H8
]

shift315 = [
    63, 61, 58, 54, 49, 43, 36, 28,
    61, 58, 54, 49, 43, 36, 28, 21,
    58, 54, 49, 43, 36, 28, 21, 15,
    54, 49, 43, 36, 28, 21, 15, 10,
    49, 43, 36, 28, 21, 15, 10,  6,
    43, 36, 28, 21, 15, 10,  6,  3,
    36, 28, 21, 15, 10,  6,  3,  1,
    28, 21, 15, 10,  6,  3,  1,  0
]

mask315 = [
    0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF,
    0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F,
    0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F,
    0x0F, 0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F,
    0x1F, 0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F,
    0x3F, 0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07,
    0x7F, 0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03,
    0xFF, 0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01
]

################################################################################
################################################################################
##   Bit boards                                                               ##
################################################################################
################################################################################

NULLBITBOARD = 0x0000000000000000
WHITE_SQUARES = 0x55AA55AA55AA55AA
BLACK_SQUARES = 0xAA55AA55AA55AA55
CENTER_FOUR = 0x0000001818000000

################################################################################
#  Ranks and files                                                             #
################################################################################

rankBits = []
fileBits = []
for i in range (8):
    rankBits.append (255 << i*8)
    fileBits.append (0x0101010101010101 << i)
rankBits.reverse()
fileBits.reverse()

################################################################################
#  Generate the move bitboards.  For e.g. the bitboard for all                 #
#  the moves of a knight on f3 is given by MoveArray[knight][21].              #
################################################################################

from bitboard import setBit, clearBit, moveBit, firstBit, lastBit, iterBits

dir = [
    None,
    [ 9, 11 ], # Only capture moves are included
    [ -21, -19, -12, -8, 8, 12, 19, 21 ],
    [ -11, -9, 9, 11 ],
    [ -10, -1, 1, 10 ],
    [ -11, -10, -9, -1, 1, 9, 10, 11 ],
    [ -11, -10, -9, -1, 1, 9, 10, 11 ],
    [ -9, -11 ]
]

map = [
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1,  0,  1,  2,  3,  4,  5,  6,  7, -1,
    -1,  8,  9, 10, 11, 12, 13, 14, 15, -1,
    -1, 16, 17, 18, 19, 20, 21, 22, 23, -1,
    -1, 24, 25, 26, 27, 28, 29, 30, 31, -1,
    -1, 32, 33, 34, 35, 36, 37, 38, 39, -1,
    -1, 40, 41, 42, 43, 44, 45, 46, 47, -1,
    -1, 48, 49, 50, 51, 52, 53, 54, 55, -1,
    -1, 56, 57, 58, 59, 60, 61, 62, 63, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
    -1, -1, -1, -1, -1, -1, -1, -1, -1, -1 
]

moveArray = [[0]*64 for i in range(8)] # moveArray[8][64]

for piece in PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, BPAWN:
    for fcord in range(120):
        f = map[fcord]
        if f == -1:
            # We only generate moves for squares inside the board
            continue
        # Create a new bitboard
        b = 0
        for d in dir[piece]:
            tcord = fcord
            while True:
                tcord += d
                t = map[tcord]
                if t == -1:
                	# If we landed outside of board, there is no more to look
                	# for
                	break
                b = setBit (b, t)
                if not sliders[piece]:
                	# If we are a slider, we should not break, but add the dir
                	# value once again
                    break
        moveArray[piece][f] = b
        
################################################################################
#  For each square, there are 8 rays.  The first 4 rays are diagonals          #
#  for the bishops and the next 4  are file/rank for the rooks.                #
#  The queen uses all 8 rays.                                                  #
#  These rays are used for move generation rather than MoveArray[].            #
#  Also initialize the directions[][] array.  directions[f][t] returns         #
#  the index into Ray[f] array allow us to find the ray in that direction.     #
################################################################################

directions = [[-1]*64 for i in range(64)] # directions[64][64]
rays = [[0]*8 for i in range(64)] # rays[64][8]

for fcord in range(120):
    f = map[fcord]
    if f == -1: continue
    ray = -1
    for piece in BISHOP, ROOK:
        for d in dir[piece]:
            ray += 1
            b = 0
            tcord = fcord
            while True:
               tcord += d
               t = map[tcord]
               if t == -1:
                   break
               rays[f][ray] = setBit (rays[f][ray], t)
               directions[f][t] = ray

################################################################################
#  The FromToRay[b2][f6] gives the diagonal ray from c3 to f6;                 #
#  It also produces horizontal/vertical rays as well. If no                    #
#  ray is possible, then a 0 is returned.                                      #
################################################################################

fromToRay = [[0]*64 for i in range(64)] # fromToRay[64][64]

for piece in BISHOP, ROOK:
    for fcord in range (120):
        f = map[fcord]
        if f == -1: continue
        for d in dir[piece]:
            tcord = fcord
            t = map[tcord]
            
            while True:
                b = fromToRay[f][t]
                tcord += d
                t = map[tcord]
                if t == -1:
                    break
                fromToRay[f][t] = setBit (fromToRay[f][t], t)
                fromToRay[f][t] |= b

################################################################################
#  These tables are used to calculate rook, queen and bishop moves             #
################################################################################

rook00Attack = [[0]*256 for i in range(64)] # rook00Attack[64][256]
rook90Attack = [[0]*256 for i in range(64)] # rook90Attack[64][256]
bishop45Attack = [[0]*256 for i in range(64)] # bishop45Attack[64][256]
bishop315Attack = [[0]*256 for i in range(64)] # bishop315Attack[64][256]

cmap = [ 128, 64, 32, 16, 8, 4, 2, 1 ]
rot1 = [ A1, A2, A3, A4, A5, A6, A7, A8 ]
rot2 = [ A1, B2, C3, D4, E5, F6, G7, H8 ]
rot3 = [ A8, B7, C6, D5, E4, F3, G2, H1 ]

# First we init the tables without concerning about blockers
# For each cord we have 256   
for cord in range (A1, H1+1):
    for map in range (256):
        cord1 = cord2 = cord
        while cord1 > 0:
            cord1 -= 1
            if cmap[cord1] & map: break
        while cord2 < 7:
            cord2 += 1
            if cmap[cord2] & map: break
        rook00Attack[cord][map] = \
                fromToRay[cord][cord1] | \
                fromToRay[cord][cord2]
        rook90Attack[rot1[cord]][map] = \
                fromToRay[rot1[cord]][rot1[cord1]] | \
                fromToRay[rot1[cord]][rot1[cord2]]
        bishop45Attack[rot2[cord]][map] = \
                fromToRay[rot2[cord]][rot2[cord1]] | \
                fromToRay[rot2[cord]][rot2[cord2]]
        bishop315Attack[rot3[cord]][map] = \
                fromToRay[rot3[cord]][rot3[cord1]] | \
                fromToRay[rot3[cord]][rot3[cord2]]

def itranges (range1, range2):
    for i in range(len(range1)):
        yield (range1[i], range2[i])

MAXBITBOARD = (1<<64)-1

for map in range (256):
    # Run through all cords except the 1st rank
    for cord in range (A2, H8+1):
        rook00Attack[cord][map] = rook00Attack[cord-8][map] >> 8
    
    # Run through all cords, besides the A file
    for file in range(B1, H1+1):
        for rank in range (A1, A8+1, 8):
            cord = rank + file
            rook90Attack[cord][map] = rook90Attack[cord-1][map] >> 1
    
    for cord1, cord2 in itranges (range(B1, H1+1,  1),
                                  range(H7, H1-1, -8)):
        for cord in range(cord1, cord2+1, 9):
            bishop45Attack[cord][map] = \
                    bishop45Attack[cord+8][map] << 8 & MAXBITBOARD
    
    for cord1, cord2 in itranges (range(A2, A8+1,  8),
                                  range(G8, A8-1, -1)):
        for cord in range(cord1, cord2+1, 9):
            bishop45Attack[cord][map] = \
              clearBit (bishop45Attack[cord+1][map], cord1-8) << 1
    
    for cord1, cord2 in itranges (range(H2, H8+1,  8),
                                  range(B8, H8+1,  1)):
        for cord in range(cord1, cord2+1, 7):
                bishop315Attack[cord][map] = bishop315Attack[cord-8][map] >> 8
    
    for cord1, cord2 in itranges (range(G1, A1-1, -1),
                                  range(A7, A1-1, -8)):
        for cord in range(cord1, cord2+1, 7):
            bishop315Attack[cord][map] = \
             clearBit (bishop315Attack[cord+1][map], cord2+8) << 1
