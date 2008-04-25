import os
import sys

from array import array

from pychess.Utils.const import *
from pychess.System.prefix import addHomePrefix

def setBit (bitboard, i):
    return bitboard | bitPosArray[i]

def clearBit (bitboard, i):
    return bitboard & notBitPosArray[i]

def moveBit (bitboard, i, j):
    bitboard = clearBit(bitboard,i)
    return setBit(bitboard, j)

def firstBit (bitboard):
    """ Returns the index of the first non-zero bit from left """
    if (bitboard >> 48): return lzArray[bitboard >> 48]
    if (bitboard >> 32): return lzArray[bitboard >> 32] + 16
    if (bitboard >> 16): return lzArray[bitboard >> 16] + 32
    return lzArray[bitboard] + 48

def lastBit (bitboard):
    return firstBit (bitboard & ((~bitboard)+1))

def bitLength (bitboard):
    return bitCount [   bitboard >> 48 ] + \
           bitCount [ ( bitboard >> 32) & 0xffff] + \
           bitCount [ ( bitboard >> 16) & 0xffff] + \
           bitCount [   bitboard & 0xffff ]

def iterBits (bitboard):
    ensureBitArraysLoaded ()
    return bitsArray0[bitboard >> 48] + \
            bitsArray1[bitboard >> 32 & 0xffff] + \
            bitsArray2[bitboard >> 16 & 0xffff] + \
            bitsArray3[bitboard & 0xffff]

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


# This array is used when the position of the leading non-zero bit is required.
# Leftmost is 0, rightmost is 63

NBITS = 16
lzArray = array('B',[0]*65536)

s = n = 1
for i in range(NBITS):
    for j in range (s, s + n):
        lzArray[j] = NBITS - 1 - i
    s += n
    n += n


# BitPosArray[i] returns the bitboard whose ith bit (FROM LEFT) is set to 1 and
# every other bits 0. This is about double speed compared to do shifting all the
# time (On my computer). It also computes the NotBitPosArray = ~BitPosArray.

notBitPosArray = [0]*64
bitPosArray = [0]*64

b = 1
for i in range(63,-1,-1):
    bitPosArray[i] = b
    notBitPosArray[i] = ~b
    b <<= 1

# These arrays are used to get the 0-63 position of the bits in a board
# We init them lazily, as they can take multiple secconds to load/create
bitsArray0, bitsArray1, bitsArray2, bitsArray3 = None, None, None, None

BITS_DONE = False
location = addHomePrefix("bitboards")
def ensureBitArraysLoaded ():
    global BITS_DONE
    if BITS_DONE:
        return
    
    global bitsArray0, bitsArray1, bitsArray2, bitsArray3

    if sys.platform == "win32":
        print "TODO: no fcntl on win32..."
    else:
        import fcntl
    
    if os.path.isfile (location):
        f = file (location, "r")
        fcntl.flock(f, fcntl.LOCK_EX)
        fcntl.flock(f, fcntl.LOCK_UN)
        
        try:
            try:
                bitsArray0 = [array('B') for i in xrange (65536)]
                bitsArray1 = [array('B') for i in xrange (65536)]
                bitsArray2 = [array('B') for i in xrange (65536)]
                bitsArray3 = [array('B') for i in xrange (65536)]
                
                ord_ = ord
                for list in (bitsArray0, bitsArray1, bitsArray2, bitsArray3):
                    for ar in list:
                        l = ord_(f.read(1))
                        ar.fromfile(f, l)
                BITS_DONE = True
            
            except EOFError, TypeError:
                # TypeError is called when f.read(1) returns bad data and 'ord'
                # can't parse it.
                pass
        finally:
            f.close()
    
    if not BITS_DONE:
        bitsArray0 = [array('B') for i in xrange (65536)]
        bitsArray1 = [array('B') for i in xrange (65536)]
        bitsArray2 = [array('B') for i in xrange (65536)]
        bitsArray3 = [array('B') for i in xrange (65536)]
        
        for bits in xrange(65536):
            origbits = bits
            while bits:
                b = firstBit(bits)
                bits = clearBit(bits, b)
                bitsArray0[origbits].append(b-48)
                bitsArray1[origbits].append(b-32)
                bitsArray2[origbits].append(b-16)
                bitsArray3[origbits].append(b)
        
        if not os.path.isfile (location):
            out = file (location, "w")
            fcntl.flock(out, fcntl.LOCK_EX)
            len_ = len
            chr_ = chr
            for ar in bitsArray0 + bitsArray1 + bitsArray2 + bitsArray3:
                out.write(chr_(len_(ar)))
                ar.tofile(out)
            fcntl.flock(out, fcntl.LOCK_UN)
            out.close()
        
        BITS_DONE = True

# The bitCount array returns the no. of bits present in the 16 bit
# input argument. This is use for counting the number of bits set
# in a BitBoard (e.g. for mobility count).

bitCount = array('H',[0]*65536)
bitCount[0] = 0
bitCount[1] = 1

i = 1
for n in range(2,17):
    i <<= 1
    for j in range (i, i*2):
        bitCount[j] = 1 + bitCount[j-i]
