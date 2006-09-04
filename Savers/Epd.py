import History

from Format import Format
class Epd (Format):
    def endings (self):
        return ("epd", "fen")

    def save (self, uri, history):
        """Saves history to file"""
        file = open(uri, "w")
        pieces = history[-1]
        sign = lambda p: p.color == "white" and p.sign.upper() or p.sign
        for i in range(len(pieces)):
            row = pieces[i]
            empty = 0;
            for j in range(len(row)):
                piece = row[j]
                if piece == None:
                    empty += 1
                    if j == 7:
                        file.write(str(empty))
                else:
                    if empty > 0:
                        file.write(str(empty))
                    file.write(sign(piece))
            if i != 7:
                file.write("/")
        file.write(" ")
        
        if len(history) % 2 == 0:
            file.write("w")
        else: file.write("b")
        file.write(" ")
        
        if history.castling == 0:
            file.write("-")
        else:
            if history.castling & History.WHITE_OO:
                file.write("K")
            if history.castling & History.WHITE_OOO:
                file.write("Q")
            if history.castling & History.BLACK_OO:
                file.write("k")
            if history.castling & History.BLACK_OOO:
                file.write("q")
        file.write(" ")
        
        if history.enPassant:
            file.write(history.enPassant)
        else: file.write("-")

    def load (self, uri):
        pass

if __name__ == "__main__":
    epd = Epd()
    epd.save("/home/thomas/ud.epd", History.History())
