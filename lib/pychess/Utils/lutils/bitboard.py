from array import array


# setBit returns a bitboard with the ith bit set
def setBit(bitboard, i):
    return bitboard | bitPosArray[i]


bitPosArray = [2**(63 - i) for i in range(64)]


# clearBit returns the bitboard with the ith bit unset
def clearBit(bitboard, i):
    return bitboard & notBitPosArray[i]


notBitPosArray = [~2**(63 - i) for i in range(64)]


# firstBit returns the bit closest to 0 (A4) that is set in the board
def firstBit(bitboard):
    """ Returns the index of the first non-zero bit from left """
    if (bitboard >> 48):
        return lzArray[bitboard >> 48]
    if (bitboard >> 32):
        return lzArray[bitboard >> 32] + 16
    if (bitboard >> 16):
        return lzArray[bitboard >> 16] + 32
    return lzArray[bitboard] + 48

# The bitCount array returns the leading non-zero bit in the 16 bit
# input argument.

lzArray = array('B', [0] * 65536)

s = n = 1
for i in range(16):
    for j in range(s, s + n):
        lzArray[j] = 16 - 1 - i
    s += n
    n += n


# lastBit returns the bit closest to 63 (H8) that is set in the board
def lastBit(bitboard):
    return lsb[bitboard & -bitboard]


lsb = {}
for i in range(64):
    lsb[2**i] = 63 - i


# iterBits yields, or returns a list of, the positions of all set bits in a
# bitboard. There is no guarantee of the order.
def iterBits(bitboard):
    while bitboard:
        bit = bitboard & -bitboard
        yield lsb[bit]
        bitboard -= bit


# toString returns a representation of the bitboard for debugging
def toString(bitboard):
    s = []
    last = -1

    while bitboard:
        cord = firstBit(bitboard)
        bitboard = clearBit(bitboard, cord)
        for c in range(cord - last - 1):
            s.append(" -")
        s.append(" #")
        last = cord
    while len(s) < 64:
        s.append(" -")

    s2 = ""
    for i in range(64, 0, -8):
        a = s[i - 8:i]
        s2 += "".join(a) + "\n"
    return s2
