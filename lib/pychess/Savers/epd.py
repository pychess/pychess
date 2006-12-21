from pychess.Utils.History import History, startBoard
from pychess.Utils.Cord import Cord
from pychess.Utils.Board import Board
from pychess.Utils.Piece import Piece
from pychess.Utils.Move import Move
from pychess.Utils.Game import Game
from pychess.Utils import validator
from pychess.Utils.const import *

__label__ = _("Chess Position")
__endings__ = "epd", "fen"
__append__ = True

def save (file, game):
    """Saves game to file in fen format"""
    
    if isinstance (game, Game):
        history = game.history
    else: history = game
    
    pieces = history[-1].data
    sign = lambda p: p.color == WHITE and reprSign[p.sign][0] or reprSign[p.sign][0].lower()
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
    
    file.write(history.curCol() == WHITE and "w" or "b")
    file.write(" ")
    
    if not sum([history[-1].castling & c for c in \
            (WHITE_OO, WHITE_OOO, BLACK_OO, BLACK_OOO)]):
        file.write("-")
    else:
        if history[-1].castling & WHITE_OO:
            file.write("K")
        if history[-1].castling & WHITE_OOO:
            file.write("Q")
        if history[-1].castling & BLACK_OO:
            file.write("k")
        if history[-1].castling & BLACK_OOO:
            file.write("q")
    file.write(" ")
    
    if history[-1].enpassant:
    	file.write(repr(history[-1].enpassant))
    else:
	    file.write("-")
    file.write(" ")
    
    file.write(str(history[-1].fifty))
    file.write(" ")
    
    fullmove = len(history)/2+1
    file.write(str(fullmove))
    
    #Closing the file prevents us from using StringIO
    #file.close()
    
def load (file):
    games = []
    for line in file:
        if line.strip():
            games.append(line.strip())
    return EpdFile (games)

from ChessFile import ChessFile

class EpdFile (ChessFile):
    
    def loadToHistory (self, gameno, position, history=None):
        if not history: history = History(mvlist=False)
        else: history.reset(mvlist=False)
        
        data = self.games[gameno].split()
        if len(data) < 5:
            # It is actually in six parts, the sixth being the fullmove number
            # We don't use that one though, so no need to fail if it is missing
            raise ValueError, "Bad epd string "+ repr(self.games[gameno])
        
        rows = []
        for row in data[0].split("/"):
            rows.append([])
            for c in row:
                if c.isdigit():
                    rows[-1] += [None]*int(c)
                else:
                    color = c.islower() and BLACK or WHITE
                    sign = reprSign.index(c.upper())
                    rows[-1].append(Piece(color, sign))
        rows.reverse()
        board = Board(rows)
        
        starter = data[1].lower()
        startc = starter == "b" and BLACK or WHITE
        
        if data[3] != "-":
            c = Cord(data[3])
            dy = startc == WHITE and -1 or 1
            data = board.clone().data
            c0 = Cord(c.x,c.y-dy)
            c1 = Cord(c.x,c.y+dy)
            data[c0.y][c0.x] = data[c1.y][c1.x]
            data[c1.y][c1.x] = None
            oldboard = Board(data)
            
            history.boards = [oldboard, board]
            history.moves = [Move(c0,c1)]
        else:
            history.boards = [board]
        
        if position != -1:
            if (len(history.boards[:position+1]) - len(history.boards)) % 2 != 0:
                startc = 1-startc
            history.boards = history.boards[:position+1]
            history.moves = history.moves[:position]
        
        if history.curCol() != startc:
            history.setStartingColor(BLACK)
        else:
            history.setStartingColor(WHITE)
        
        history[-1].movelist = validator.findMoves(history[-1])
        
        dic = {"K": WHITE_OO, "Q": WHITE_OOO, "k": BLACK_OO, "q": BLACK_OOO}
        for char in data[2]:
            if char in dic:
                history[-1].castling |= dic[char]
        
        history[-1].fifty = int(data[4])
        
        if len(history) > 1:
            history.emit("changed")
        
        return history
