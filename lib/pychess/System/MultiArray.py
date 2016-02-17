
class MultiArray:
    def __init__(self, oneLineData, *lengths):
        self.lengths = lengths
        self.data = oneLineData

    def get(self, *indexes):
        index = 0
        for depth, i in enumerate(indexes[::-1]):
            index += i * self.lengths[depth]**depth
        return self.data[index]
