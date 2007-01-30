
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
    return bitsArray0[bitboard >> 48] + \
           bitsArray1[bitboard >> 32 & 0xffff] + \
           bitsArray2[bitboard >> 16 & 0xffff] + \
           bitsArray3[bitboard & 0xffff]
    
    # Gnuchess uses this version, but it is about 7 times slower
    #while bitboard:
    #    cord = firstBit(bitboard)
    #    bitboard = clearBit(bitboard, cord)
    #    yield cord

from pychess.Utils.const import *

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
lzArray = [0]*65536

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

# This array is used when the position of the bits are required

import os, time
from array import array

# FIXME:
# This is a try to make pychess catche bitsArray information, to save a few
# secconds on startup time. While the global locking works fine, the actual
# reading from file to arrays seems to not work.
while False:
    pidpath = os.path.expanduser("~/.pychess/bitsArray.pid")
    try:
        os.mkdir(pidpath)
    except OSError:
        time.sleep(0.1)
        continue
    
    path = os.path.expanduser("~/.pychess/bitsArray.pickle")
    if os.path.isfile(path):
        f = open(path)
        try:
            t = time.time()
            bitsArray0 = []
            bitsArray1 = []
            bitsArray2 = []
            bitsArray3 = []
            d = f.read()
            last = -1
            for j in range(4):
                bitsArray = locals()["bitsArray%d"%j]
                for i in xrange(65536):
                    cur = d.find("@", last)+1
                    ar = array("B")
                    f.seek(last+1)
                    ar.fromfile(f, cur-last-1)
                    bitsArray.append(ar)
                    last = cur
            f.close()
        except:
            f.close()
            os.remove(path)
    
    if not os.path.isfile(path):

        bitsArray0 = [array("B") for i in xrange (65536)]
        bitsArray1 = [array("B") for i in xrange (65536)]
        bitsArray2 = [array("B") for i in xrange (65536)]
        bitsArray3 = [array("B") for i in xrange (65536)]
    
        for bits in xrange(65536):
            origbits = bits
            while bits:
                b = firstBit(bits)
                bits = clearBit(bits, b)
                bitsArray0[origbits].append(b-48)
                bitsArray1[origbits].append(b-32)
                bitsArray2[origbits].append(b-16)
                bitsArray3[origbits].append(b)
        
        f = open(path, "w")
        for bitsArray in (bitsArray0, bitsArray1, bitsArray2, bitsArray3):
            for ar in bitsArray:
                ar.tofile(f)
                f.write("@")
        f.close()
    
    os.rmdir(pidpath)
    break

bitsArray0 = [array("B") for i in xrange (65536)]
bitsArray1 = [array("B") for i in xrange (65536)]
bitsArray2 = [array("B") for i in xrange (65536)]
bitsArray3 = [array("B") for i in xrange (65536)]

for bits in xrange(65536):
    origbits = bits
    while bits:
        b = firstBit(bits)
        bits = clearBit(bits, b)
        bitsArray0[origbits].append(b-48)
        bitsArray1[origbits].append(b-32)
        bitsArray2[origbits].append(b-16)
        bitsArray3[origbits].append(b)

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
