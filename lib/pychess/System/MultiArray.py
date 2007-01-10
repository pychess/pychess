from array import array

class MultiArray:

    def __init__ (self, typecode, length, oneLineData):
        self.length = length
        self.data = array(typecode, oneLineData)
    
    def get (self, *indexes):
        index = 0
        for depth, i in enumerate(indexes[::-1]):
            index += i*self.length**depth
        value = self.data[index]
        return value
