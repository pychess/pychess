class Format:
    def endings (self):
        """Returns a touple of legal endings for this format"""
        abstract
    def save (self, uri, history):
        """Saves history to file"""
        abstract
    def load (self, uri):
        """Returns history object from file"""
        abstract
