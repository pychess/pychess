from Utils.History import History, startBoard, WHITE_OO, WHITE_OOO, BLACK_OO, BLACK_OOO
from Utils.Cord import Cord
from Utils.Board import Board
from Utils.Piece import Piece
from Utils.Move import Move
from Utils import validator

__label__ = _("Chess Position")
__endings__ = "epd", "fen"

def save (file, history):
    """Saves history to file"""
    
    pieces = history[-1].data
    sign = lambda p: p.color == "white" and p.sign.upper() or p.sign
    for i in range(len(pieces))[::-1]:
        row = pieces[i]
        empty = 0
        for j in range(len(row)):
            piece = row[j]
            if piece == None:
                empty += 1
                if j == 7:
                    file.write(str(empty))
            else:
                if empty > 0:
                    file.write(str(empty))
                    empty = 0
                file.write(sign(piece))
        if i != 0:
            file.write("/")
    file.write(" ")
    
    file.write(history.curCol()[:1])
    file.write(" ")
    
    if history.castling == 0:
        file.write("-")
    else:
        if history.castling & WHITE_OO:
            file.write("K")
        if history.castling & WHITE_OOO:
            file.write("Q")
        if history.castling & BLACK_OO:
            file.write("k")
        if history.castling & BLACK_OOO:
            file.write("q")
    file.write(" ")
    
    if len(history) >= 2:
        move = history.moves[-1]
        if abs(move.cord0.y - move.cord1.y) == 2 and \
                history[-1][move.cord1].sign == "p":
            file.write(str(Cord(move.cord0.x,(move.cord0.y+move.cord1.y)/2)))
            return
    file.write("-")
    #Closing the file prevents us from using StringIO
    #file.close()
    
def load (file, history):
    data = None
    for line in file:
        if line.strip():
            data = line.strip()
            break
    if not data:
        return
    
    data = data.split(" ")
    if len(data) < 4:
        return
    
    history.reset(mvlist=False)
    
    rows = []
    for row in data[0].split("/"):
        rows.append([])
        for c in row:
            if c.isdigit():
                rows[-1] += [None]*int(c)
            else:
                color = c.islower() and "black" or "white"
                rows[-1].append(Piece(color, c.lower()))
    rows.reverse()
    board = Board(rows)
    
    starter = data[1].lower()
    
    if data[3] != "-":
        if history.curCol()[0] == starter:
            history.setStartingColor("black")
    
        c = Cord(data[3])
        dy = starter == "w" and -1 or 1
        lastb = board.clone()
        c0 = Cord(c.x,c.y-dy)
        c1 = Cord(c.x,c.y+dy)
        lastb[c0] = lastb[c1]
        lastb[c1] = None
        
        history.boards = [lastb]
        history.add(Move(history,(c0,c1)), mvlist=True)

    else:
        if history.curCol()[0] != starter:
            history.setStartingColor("black")
            
        history.boards = [board]
        history.movelist.append(validator.findMoves(history))
        history.emit("changed")
        
    dic = {"K": WHITE_OO, "Q": WHITE_OOO, "k": BLACK_OO, "q": BLACK_OOO}
    for char in data[2]:
        if char in dic:
            history.castling |= dic[char]
    
