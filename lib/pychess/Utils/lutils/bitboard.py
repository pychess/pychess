import os
import sys

try:
    from gmpy import mpz
    uselp = False
except ImportError:
    uselp = True
    from array import array

#===============================================================================
# createBoard returns a new bitboard in the format preferred by this module
#===============================================================================

def createBoard (number):
    return mpz(number)

if uselp:
    def createBoard (number):
        return number



#===============================================================================
# clearBit returns a bitboard with the ith bit set
#===============================================================================

def setBit (bitboard, i):
    return bitboard.setbit(63-i)

if True or uselp:
    def setBit (bitboard, i):
        return bitboard | bitPosArray[i]

    bitPosArray = [2**(63-i) for i in xrange(64)]



#===============================================================================
# clearBit returns the bitboard with the ith bit unset
#===============================================================================

def clearBit (bitboard, i):
    return bitboard & notBitPosArray[i]

notBitPosArray = [~2**(63-i) for i in xrange(64)]



#===============================================================================
# firstBit returns the bit closest to 0 (A4) that is set in the board
#===============================================================================

def firstBit (bitboard):
    return 64-bitboard.numdigits(2)

if uselp:
    def firstBit (bitboard):
        """ Returns the index of the first non-zero bit from left """
        if (bitboard >> 48): return lzArray[bitboard >> 48]
        if (bitboard >> 32): return lzArray[bitboard >> 32] + 16
        if (bitboard >> 16): return lzArray[bitboard >> 16] + 32
        return lzArray[bitboard] + 48
    
    # The bitCount array returns the leading non-zero bit in the 16 bit
    # input argument.
    
    lzArray = array('B',[0]*65536)
    
    s = n = 1
    for i in range(16):
        for j in range (s, s + n):
            lzArray[j] = 16 - 1 - i
        s += n
        n += n



#===============================================================================
# lastBit returns the bit closest to 63 (H8) that is set in the board
#===============================================================================

def lastBit (bitboard):
    return 63-bitboard.scan1(0)

if uselp:
    def lastBit (bitboard):
        return lsb [bitboard & -bitboard]
    
    lsb = {}
    for i in xrange(64):
        lsb[2**i] = 63-i



#===============================================================================
# bitLength returns the number of set bits in a bitboard. This can be used to
# count the number of pieces, or calculate mobility
#===============================================================================

def bitLength (bitboard):
    return bitboard.popcount()

if uselp:
    def bitLength (bitboard):
        return bitCount [   bitboard >> 48 ] + \
               bitCount [ ( bitboard >> 32) & 0xffff] + \
               bitCount [ ( bitboard >> 16) & 0xffff] + \
               bitCount [   bitboard & 0xffff ]
    
    # The bitCount array returns the no. of bits present in the 16 bit
    # input argument.
    
    bitCount = array('H',[0]*65536)
    bitCount[0] = 0
    bitCount[1] = 1
    
    i = 1
    for n in range(2,17):
        i <<= 1
        for j in range (i, i*2):
            bitCount[j] = 1 + bitCount[j-i]



#===============================================================================
# iterBits yields, or returns a list of, the positions of all set bits in a
# bitboard. There is no guarantee of the order.
#===============================================================================

def iterBits (bitboard):
    scan = bitboard.scan1
    last = -1
    for i in xrange(bitboard.popcount()):
        last = scan(last+1)
        yield 63-last

if uselp:
    def iterBits (bitboard):
        while bitboard:
            bit = bitboard & -bitboard
            yield lsb[bit]
            bitboard -= bit



#===============================================================================
# toString returns a representation of the bitboard for debugging
#===============================================================================

def toString (bitboard):
    chars = bitboard.digits(2).zfill(64)
    chars = chars.replace("0", "- ").replace("1", "# ")
    return "\n".join(chars[i:i+16] for i in xrange(0,128,16))

if uselp:
    def toString (bitboard):
        s = []
        last = -1
        
        while bitboard:
            cord = firstBit (bitboard)
            bitboard = clearBit (bitboard, cord)
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
