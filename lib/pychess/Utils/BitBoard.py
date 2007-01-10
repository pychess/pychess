
class BitBoard:

    def __init__ (self, data=0):
    	self.data = data

   	def setBit (self, bit):
   		self.data |= fullBoard[bit]

   	def clearBit (self, bit):
		self.data &= emptyBoard[bit]

    def firstBit (self):
        """ Returns the index of the first non-zero bit from left """
        if (self.data >> 48): return lzArray[self.data >> 48]
        if (self.data >> 32): return lzArray[self.data >> 32] + 16
        if (self.data >> 16): return lzArray[self.data >> 16] + 32
        return lzArray[b] + 48
    
    def lastBit (self):
        return self.firstBit ( (self.data) & ((~self.data) + 1) )
    
    def __len__ (self):
        return BitCount [   self.data >> 48 ] +
               BitCount [ ( self.data >> 32) & 0xffff] +
               BitCount [ ( self.data >> 16) & 0xffff] +
               BitCount [   self.data & 0xffff ]

# This array is used when the position of the leading non-zero bit is required.
# Leftmost is 0, rightmost is 63
# Algorithm nailed from gnuchess

NBITS = 16
lzArray = [None]*64

s = n = 1
for i in range(NBITS):
    for j in range (s, s + n):
        lzArray[j] = BitBoard(NBITS - 1 - i);
    s += n
    n += n

# BitPosArray[i] returns the bitboard whose ith bit is set to 1 and every other
# bits 0. This is about double speed compared to do shifting all the time (On
# my computer). It also computes the NotBitPosArray = ~BitPosArray.
# Algorithm nailed from gnuchess

notBitPosArray = [None]*64
bitPosArray = [None]*64

b = 1
for i in range(63,-1,-1):
    bitPosArray[i] = b
    notBitPosArray[i] = ~b
    b <<= 1

# The BitCount array returns the no. of bits present in the 16 bit
# input argument.  This is use for counting the number of bits set
# in a BitBoard (e.g. for mobility count).
# Algorithm nailed from gnuchess

BitCount = [None]*65536
BitCount[0] = BirBoard(0)
BitCount[1] = BirBoard(1)

i = 1
for n in range(2,17):
    i <<= 1
    for j in range (i, i*2):
        BitCount[j] = BitBoard( 1+BitCount[j-i].data )
