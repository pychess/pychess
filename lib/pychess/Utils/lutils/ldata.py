from array import array
from operator import or_
from pychess.Utils.const import *
from bitboard import *

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
KING_VALUE = 2000
PIECE_VALUES = [0, PAWN_VALUE, KNIGHT_VALUE,
                BISHOP_VALUE, ROOK_VALUE, QUEEN_VALUE, KING_VALUE]

MATE_VALUE = MAXVAL = 99999

# How many points does it give to have the piece standing i cords from the
# opponent king
pawnTScale = [0, 40, 20, 12, 9, 6, 4, 2, 1, 0]
bishopTScale = [0, 50, 25, 15, 7, 5, 3, 2, 2, 1]
knightTScale = [0, 50, 70, 35, 10, 3, 2, 2, 1, 1]
rookTScale = [0, 50, 40, 15, 5, 2, 1, 1, 1, 0]
queenTScale = [0, 100, 60, 20, 10, 7, 5, 4, 3, 2]

passedScores = (
    ( 0, 48, 48, 120, 144, 192, 240, 0 ),
    ( 0, 240, 192, 144, 120, 48, 48, 0 )
)

# Penalties for one or more isolated pawns on a given file 
isolani_normal = ( -8, -10, -12, -14, -14, -12, -10, -8 )
# Penalties if the file is half-open (i.e. no enemy pawns on it)
isolani_weaker = ( -22, -24, -26, -28, -28, -26, -24, -22 )

from math import sqrt

distance = [[0]*64 for i in range(64)]
for fcord in range(64):
    for tcord in range(64):
        fx = fcord >> 3
        fy = fcord & 7
        tx = tcord >> 3
        ty = tcord & 7
        distance[fcord][tcord] = int(sqrt((fx-tx)**2+(fy-ty)**2))

pawnScoreBoard = (
   (0,  0,  0,  0,  0,  0,  0,  0,
    5,  5,  5,-10,-10,  5,  5,  5,
   -2, -2, -2,  6,  6, -2, -2, -2,
    0,  0,  0, 25, 25,  0,  0,  0,
    2,  2, 12, 16, 16, 12,  2,  2,
    4,  8, 12, 16, 16, 12,  4,  4,
    4,  8, 12, 16, 16, 12,  4,  4,
    0,  0,  0,  0,  0,  0,  0,  0),
    
   (0,  0,  0,  0,  0,  0,  0,  0,
    4,  8, 12, 16, 16, 12,  4,  4,
    4,  8, 12, 16, 16, 12,  4,  4,
    2,  2, 12, 16, 16, 12,  2,  2,
    0,  0,  0, 25, 25,  0,  0,  0,
   -2, -2, -2,  6,  6, -2, -2, -2,
    5,  5,  5,-10,-10,  5,  5,  5,
    0,  0,  0,  0,  0,  0,  0,  0)
)

outpost = (
   (0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 0, 0, 1, 1, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0),
    
   (0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 1, 1, 0, 0, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 1, 1, 1, 1, 1, 1, 0,
    0, 0, 1, 1, 1, 1, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0)
)

d2e2    = (createBoard(0x0018000000000000), createBoard(0x0000000000001800))
brank7  = (createBoard(0x000000000000FF00), createBoard(0x00FF000000000000))
brank8  = (createBoard(0x00000000000000FF), createBoard(0xFF00000000000000))
brank67 = (createBoard(0x0000000000FFFF00), createBoard(0x00FFFF0000000000))
brank58 = (createBoard(0x00000000FFFFFFFF), createBoard(0xFFFFFFFF00000000))
brank48 = (createBoard(0x000000FFFFFFFFFF), createBoard(0xFFFFFFFFFF000000))

# Penalties if the file is half-open (i.e. no enemy pawns on it)
isolani_weaker = (-22, -24, -26, -28, -28, -26, -24, -22)

stonewall = [createBoard(0), createBoard(0)]
# D4, E3, F4
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - # - # - -
# - - - - # - - -
# - - - - - - - -
# - - - - - - - -
stonewall[WHITE] = createBoard(0x81400000000)

# D5, E6, F5
# - - - - - - - -
# - - - - - - - -
# - - - - # - - -
# - - - # - # - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
stonewall[BLACK] = createBoard(0x81400000000)

# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - # - - - - # -
# # # - - - - # #
# - - - - - - - -
qwwingpawns1 = bitPosArray[A2] | bitPosArray[B2]
qwwingpawns2 = bitPosArray[A2] | bitPosArray[B3]
kwwingpawns1 = bitPosArray[G2] | bitPosArray[H2]
kwwingpawns2 = bitPosArray[G3] | bitPosArray[H2]

# - - - - - - - -
# # # - - - - # #
# - # - - - - # -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
qbwingpawns1 = bitPosArray[A7] | bitPosArray[B7]
qbwingpawns2 = bitPosArray[A7] | bitPosArray[B6]
kbwingpawns1 = bitPosArray[G7] | bitPosArray[H7]
kbwingpawns2 = bitPosArray[G6] | bitPosArray[H7]

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
#  Ranks and files                                                             #
################################################################################

rankBits = [createBoard(255 << i*8) for i in xrange(7,-1,-1)]
fileBits = [createBoard(0x0101010101010101 << i) for i in xrange(7,-1,-1)]

################################################################################
################################################################################
##   Bit boards                                                               ##
################################################################################
################################################################################

WHITE_SQUARES = createBoard(0x55AA55AA55AA55AA)
BLACK_SQUARES = createBoard(0xAA55AA55AA55AA55)

# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
# - - - # # - - -
# - - - # # - - -
# - - - - - - - -
# - - - - - - - -
# - - - - - - - -
CENTER_FOUR = createBoard(0x0000001818000000)

# - - - - - - - -
# - - - - - - - -
# - - # # # # - -
# - - # # # # - -
# - - # # # # - -
# - - # # # # - -
# - - - - - - - -
# - - - - - - - -
sbox = createBoard(0x00003C3C3C3C0000)

# - - - - - - - -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - # # # # # # -
# - - - - - - - -
lbox = createBoard(0x007E7E7E7E7E7E00)

# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
# - - - - - # # #
right = fileBits[5] | fileBits[6] | fileBits[7]

# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
# # # # - - - - -
left = fileBits[0] | fileBits[1] | fileBits[2]

################################################################################
#  The IsolaniMask variable is used to determine if a pawn is an isolani.      #
#  This mask is basically all 1's on files beside the file the pawn is on.     #
#  Other bits will be set to zero.                                             #
#  E.g. isolaniMask[d-file] = 1's in c-file & e-file, 0 otherwise.             #
################################################################################

isolaniMask = [0]*8

isolaniMask[0] = fileBits[1]
isolaniMask[7] = fileBits[6]
for i in xrange (1, 7):
    isolaniMask[i] = fileBits[i-1] | fileBits[i+1]

################################################################################
#  Generate the move bitboards.  For e.g. the bitboard for all                 #
#  the moves of a knight on f3 is given by MoveArray[knight][21].              #
################################################################################

dir = [
    None,
    [ 9, 11 ], # Only capture moves are included
    [ -21, -19, -12, -8, 8, 12, 19, 21 ],
    [ -11, -9, 9, 11 ],
    [ -10, -1, 1, 10 ],
    [ -11, -10, -9, -1, 1, 9, 10, 11 ],
    [ -11, -10, -9, -1, 1, 9, 10, 11 ],
    [ -9, -11 ],
    
    # Following are for front and back walls. Will be removed from list after
    # the loop
    [ 9, 10, 11],
    [ -9, -10, -11]
]

sliders += [False, False]

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

moveArray = [[createBoard(0)]*64 for i in xrange(len(dir))] # moveArray[8][64]

for piece in xrange(1,len(dir)):
    for fcord in xrange(120):
        f = map[fcord]
        if f == -1:
            # We only generate moves for squares inside the board
            continue
        # Create a new bitboard
        b = createBoard(0)
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

frontWall = (moveArray[8], moveArray[9])
del moveArray[9]; del moveArray[8]
del dir[9]; del dir[8]
del sliders[9]; del sliders[8]

################################################################################
#  For each square, there are 8 rays.  The first 4 rays are diagonals          #
#  for the bishops and the next 4  are file/rank for the rooks.                #
#  The queen uses all 8 rays.                                                  #
#  These rays are used for move generation rather than MoveArray[].            #
#  Also initialize the directions[][] array.  directions[f][t] returns         #
#  the index into rays[f] array allow us to find the ray in that direction.    #
################################################################################

directions = [[-1]*64 for i in xrange(64)] # directions[64][64]
rays = [[createBoard(0)]*8 for i in xrange(64)] # rays[64][8]

for fcord in xrange(120):
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

fromToRay = [[createBoard(0)]*64 for i in xrange(64)] # fromToRay[64][64]

for piece in BISHOP, ROOK:
    for fcord in xrange (120):
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
#  The PassedPawnMask variable is used to determine if a pawn is passed.       #
#  This mask is basically all 1's from the square in front of the pawn to      #
#  the promotion square, also duplicated on both files besides the pawn        #
#  file.  Other bits will be set to zero.                                      #
#  E.g. PassedPawnMask[white][b3] = 1's in a4-c4-c8-a8 rect, 0 otherwise.      #
################################################################################

passedPawnMask = [[createBoard(0)]*64, [createBoard(0)]*64]

#  Do for white pawns first
for cord in xrange(64):
    passedPawnMask[WHITE][cord] = rays[cord][7]
    passedPawnMask[BLACK][cord] = rays[cord][4]
    if cord & 7 != 0:
        #  If file is not left most
        passedPawnMask[WHITE][cord] |= rays[cord-1][7]
        passedPawnMask[BLACK][cord] |= rays[cord-1][4]
    if cord & 7 != 7:
        #  If file is not right most
        passedPawnMask[WHITE][cord] |= rays[cord+1][7]
        passedPawnMask[BLACK][cord] |= rays[cord+1][4]

################################################################################
#  These tables are used to calculate rook, queen and bishop moves             #
################################################################################

ray00  = [rays[cord][5]|rays[cord][6] | 1<<(63-cord) for cord in xrange(64)]
ray45  = [rays[cord][0]|rays[cord][3] | 1<<(63-cord) for cord in xrange(64)]
ray90  = [rays[cord][4]|rays[cord][7] | 1<<(63-cord) for cord in xrange(64)]
ray135 = [rays[cord][1]|rays[cord][2] | 1<<(63-cord) for cord in xrange(64)]

attack00 = [{} for i in xrange(64)]
attack45 = [{} for i in xrange(64)]
attack90 = [{} for i in xrange(64)]
attack135 = [{} for i in xrange(64)]

cmap = [ 128, 64, 32, 16, 8, 4, 2, 1 ]
rot1 = [ A1, A2, A3, A4, A5, A6, A7, A8 ]
rot2 = [ A1, B2, C3, D4, E5, F6, G7, H8 ]
rot3 = [ A8, B7, C6, D5, E4, F3, G2, H1 ]

# To save time, we init a main line for each of the four directions, and next
# we will translate it for each possible cord
for cord in xrange(8):
    for map in xrange(1, 256):
        
        # Skip entries without cord set, as cord will always be set
        if not map & cmap[cord]:
            continue
        
        # Find limits inclusive
        cord1 = cord2 = cord
        while cord1 > 0:
            cord1 -= 1
            if cmap[cord1] & map: break
        while cord2 < 7:
            cord2 += 1
            if cmap[cord2] & map: break
        
        # Remember A1 is the left most bit
        map00 = createBoard(map << 56)
        
        attack00[cord][map00] = \
                fromToRay[cord][cord1] | \
                fromToRay[cord][cord2]
        
        map90 = createBoard(reduce(or_, (1 << 63-rot1[c] for c in iterBits(map00))))
        attack90[rot1[cord]][map90] = \
                fromToRay[rot1[cord]][rot1[cord1]] | \
                fromToRay[rot1[cord]][rot1[cord2]]
        
        map45 = createBoard(reduce(or_, (1 << 63-rot2[c] for c in iterBits(map00))))
        attack45[rot2[cord]][map45] = \
                fromToRay[rot2[cord]][rot2[cord1]] | \
                fromToRay[rot2[cord]][rot2[cord2]]
        
        map135 = createBoard(reduce(or_, (1 << 63-rot3[c] for c in iterBits(map00))))
        attack135[rot3[cord]][map135] = \
                fromToRay[rot3[cord]][rot3[cord1]] | \
                fromToRay[rot3[cord]][rot3[cord2]]


MAXBITBOARD = (1<<64)-1

for r in xrange(A2,A8+1,8):
	for cord in iterBits(ray00[r]):
		attack00[cord] = dict((map >> 8, ray >> 8)
                              for map,ray in attack00[cord-8].iteritems())

for r in xrange(B1,H1+1):
	for cord in iterBits(ray90[r]):
		attack90[cord] = dict((map >> 1, ray >> 1)
                              for map,ray in attack90[cord-1].iteritems())

# Bottom right
for r in xrange(B1,H1+1):
    for cord in iterBits(ray45[r]):
        attack45[cord] = dict((map << 8 & MAXBITBOARD, ray << 8 & MAXBITBOARD)
                              for map,ray in attack45[cord+8].iteritems())

# Top left
for r in reversed(xrange(A8,H8)):
    for cord in iterBits(ray45[r]):
        attack45[cord] = dict((map >> 8, ray >> 8)
                              for map,ray in attack45[cord-8].iteritems())

# Top right
for r in xrange(B8,H8+1):
    for cord in iterBits(ray135[r]):
        attack135[cord] = dict((map >> 8, ray >> 8)
                               for map,ray in attack135[cord-8].iteritems())

# Bottom left
for r in reversed(xrange(A1,H1)):
    for cord in iterBits(ray135[r]):
        attack135[cord] = dict((map << 8 & MAXBITBOARD, ray << 8 & MAXBITBOARD)
                               for map,ray in attack135[cord+8].iteritems())
