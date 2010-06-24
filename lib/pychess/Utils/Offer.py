class Offer:
    def __init__(self, offerType, param=None):
        self.offerType = offerType
        self.param = param
    
    def __hash__(self):
        return hash((self.offerType,self.param))
    
    def __cmp__(self, other):
        return cmp((self.offerType,self.param), other)
