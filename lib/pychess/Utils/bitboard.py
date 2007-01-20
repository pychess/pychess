from const import *

def setBit (board, i):
    return board | bitPosArray[i]

def clearBit (board, i):
    return board & notBitPosArray[i]

def moveBit (board, i, j):
    board = clearBit(board,i)
    return setBit(board, j)

def firstBit (board):
    """ Returns the index of the first non-zero bit from left """
    if (board >> 48): return lzArray[board >> 48]
    if (board >> 32): return lzArray[board >> 32] + 16
    if (board >> 16): return lzArray[board >> 16] + 32
    return lzArray[board] + 48

def lastBit (board):
    return firstBit (board & ((~board)+1))

def bitLength (board):
    return bitCount [   board >> 48 ] + \
           bitCount [ ( board >> 32) & 0xffff] + \
           bitCount [ ( board >> 16) & 0xffff] + \
           bitCount [   board & 0xffff ]

def iterBits (board):
    while board:
        cord = firstBit(board)
        board = clearBit(board, cord)
        yield cord

def toString (board):
    s = []
    last = -1
    
    while board:
        cord = firstBit (board)
        board = clearBit (board, cord)
        for c in range(cord-last-1):
            s.append(" -")
        s.append(" #")
        last = cord
    while len(s) < 64: s.append(" -")
    
    s2 = ""
    for i in range(64,0,-8):
        a = s[i-8:i]
        s2 += "".join(a) + "\n"
    return s2

# This array is used when the position of the leading non-zero bit is required.
# Leftmost is 0, rightmost is 63

NBITS = 16
lzArray = [0]* (1 << NBITS)

s = n = 1
for i in range(NBITS):
    for j in range (s, s + n):
        lzArray[j] = NBITS - 1 - i
    s += n
    n += n

# BitPosArray[i] returns the bitboard whose ith bit (FROM LEFT) is set to 1 and
# every other bits 0. This is about double speed compared to do shifting all the
# time (On my computer). It also computes the NotBitPosArray = ~BitPosArray.

notBitPosArray = [None]*64
bitPosArray = [None]*64

b = 1
for i in range(63,-1,-1):
    bitPosArray[i] = b
    notBitPosArray[i] = ~b
    b <<= 1

# The bitCount array returns the no. of bits present in the 16 bit
# input argument. This is use for counting the number of bits set
# in a BitBoard (e.g. for mobility count).

bitCount = [None]*65536
bitCount[0] = 0
bitCount[1] = 1

i = 1
for n in range(2,17):
    i <<= 1
    for j in range (i, i*2):
        bitCount[j] = 1 + bitCount[j-i]

################################################################################
#  Other boards                                                                #
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
#  For each square, there are 8 rays.  The first 4 rays are diagonals 
#  for the bishops and the next 4  are file/rank for the rooks.  
#  The queen uses all 8 rays.
#  These rays are used for move generation rather than MoveArray[].
#  Also initialize the directions[][] array.  directions[f][t] returns
#  the index into Ray[f] array allow us to find the ray in that direction.
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
              clearBit (bishop45Attack[cord+1][map], cord1-8) << 1 & MAXBITBOARD
                
    for cord1, cord2 in itranges (range(H2, H8+1,  8),
                                  range(B8, H8+1,  1)):
        for cord in range(cord1, cord2+1, 7):
                bishop315Attack[cord][map] = bishop315Attack[cord-8][map] >> 8
    
    for cord1, cord2 in itranges (range(G1, A1-1, -1),
                                  range(A7, A1-1, -8)):
        for cord in range(cord1, cord2+1, 7):
            bishop315Attack[cord][map] = \
             clearBit (bishop315Attack[cord+1][map], cord2+8) << 1 & MAXBITBOARD
