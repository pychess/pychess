#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from Utils.Cord import Cord
from System.Log import log
from threading import Lock

#import gtk.glade
#widgets = gtk.glade.XML("glade/moveerror.glade")
#dialog = widgets.get_widget("moveerror")

#def doDialog (move, stacktrace):
#    hlabel = widgets.get_widget("hlabel")
#    origtext = hlabel.get_label()
#    hlabel.set_markup(origtext % str(move))
#    textview = widgets.get_widget("trace")
#    textview.get_buffer().set_text(stacktrace)
#    response = dialog.run()
#    dialog.hide()
#    hlabel.set_markup(origtext)
#    if response != gtk.RESPONSE_OK:
#        return None
#    cbs = [widgets.get_widget("combobox%d"%i) for i in range(4)]
#    v = [cb.get_active() for cb in cbs if cb.get_active() >= 0]
#    if len(v) != 4:
#        return None
#    return (Cord(v[0], v[1]), Cord(v[2], v[3]))

class ParsingError (Exception): pass

class MovePool:
    def __init__ (self):
        self.objects = []
        self.lock = Lock()
        
    def pop (self, history, cord0, cord1, promotion="q"):
        self.lock.acquire()
        if len(self.objects) <= 0:
            self.lock.release()
            return Move(history, cord0, cord1, promotion)
        mv = self.objects.pop()
        mv.init(history, cord0, cord1, promotion)
        self.lock.release()
        return mv
        
    def add (self, move):
        if not move: return
        move.enpassant = None
        move.castling = None
        move.promotion = None
        move.cord0 = None
        move.cord1 = None
        self.objects.append(move)
movePool = MovePool()

class Move:

    def _get_cords (self):
        return (self.cord0, self.cord1)
    cords = property(_get_cords)
    
    def __init__ (self, history, cord0, cord1, promotion="q"):
        """(history, notat) or
           (history, (cord0, cord1), [promotion]) or
           (history, (strcord1, strcord2), [promotion])
           Promotion will be set to None, if not aplieable"""
           
        self.enpassant = None # None or Cord
        self.castling = None # None or (rookCordSide, rookCordMiddle)
        self.promotion = None # "q" or "r" or "b" or "k" or "n"
        
        #try:
        self.init(history, cord0, cord1, promotion)
        #except Exception, e:
        #    log.error(str(e))
        #    import traceback
        #    r = doDialog (move, traceback.format_exc())
        #    if not r:
        #        log.error("Could not parse %s. User did not specify" % str(move))
        #        import sys; sys.exit()
        #    self.cord0, self.cord1 = r
        #    self.promotion = "q"
    
    def init (self, history, cord0, cord1, promotion):
        self.cord0 = cord0
        self.cord1 = cord1
        self.promotion = promotion
        board = history[-1]
        if board[self.cord0].sign == "k":
            r = self.cord0.y
            if self.cord0.x - self.cord1.x == -2:
                self.castling = (Cord(7,r),Cord(5,r))
            elif self.cord0.x - self.cord1.x == 2:
                self.castling = (Cord(0,r),Cord(3,r))
        elif board[self.cord0].sign == "p" and self.cord0.y in (3,4):
            if self.cord0.x != self.cord1.x and board[self.cord1] == None:
                self.enpassant = Cord(self.cord1.x, self.cord0.y)
    
    def __repr__ (self):
        return str(self.cord0) + str(self.cord1)

    def __eq__ (self, other):
        if not type(self) == type(other):
            return False
        return other.cord0 == self.cord0 and \
               other.cord1 == self.cord1 and \
               other.promotion == self.promotion and \
               other.enpassant == self.enpassant and \
               other.castling == self.castling

def parseSAN (history, san):
    """ Parse a Short/Abbreviated Algebraic Notation string """
    
    cord0 = None
    cord1 = None
    promotion = "q"
    
    notat = san
    notat = notat.replace("0","o").replace("O","o")
    notat = notat.replace("=","").replace("+","").replace("#","")
    notat = notat.strip()
    if notat[-1].lower() in ("q", "r", "b", "n"):
        promotion = notat[-1].lower()
        notat = notat[:-1]
    color = history.curCol()
    
    if notat.startswith("o-o"):
        if color == "white":
            row = 0
        else: row = 7
        cord0 = Cord(4, row)
        if notat == "o-o":
            cord1 = Cord(6, row)
        else:
            cord1 = Cord(2, row)
        return movePool.pop (history, cord0, cord1, promotion)

    if "x" in notat:
        since, then = notat.split("x")
        cord1 = Cord(then)
        notat = since

    sign = "p"
    if notat[0] in ("Q", "R", "B", "K", "N"):
        sign = notat[0].lower()
        notat = notat[1:]    

    row = None
    col = None
    if notat and len(notat) != 2 and notat[0] in ("a","b","c","d","e","f","g","h"):
        col = ord(notat[0]) - ord("a")
        notat = notat[1:]
    if notat and notat[0] in ("1","2","3","4","5","6","7","8"):
        row = int(notat[0])-1
        notat = notat[1:]
    
    if notat:
        cord1 = Cord(notat)
    from Utils.validator import getMovePointingAt
    cord0 = getMovePointingAt(history, cord1, color, sign, row, col)
    if cord0 == None: raise ParsingError, "Unable to parse sanmove %s" % san
    cord0 = cord0
    
    return movePool.pop (history, cord0, cord1, promotion)
    
def parseLAN (history, lan):
    """ Parse a Long/Expanded Algebraic Notation string """
    
    lan = lan.lower()
    if lan.startswith("o-o"):
        color = history.curCol()
        if color == "white": row = 0
        else: row = 7
        cord0 = Cord(4, row)
        if lan == "o-o": cord1 = Cord(6, row)
        else: cord1 = Cord(2, row)
        return movePool.pop (history, cord0, cord1)
    
    promotion = "q"
    
    if lan.find("-") >= 0:
        c0, c1 = lan.split("-")
    else: c0, c1 = lan.split("x")
    
    if len(c0) == 3: c0 = c0[1:]
    
    if len(c1) > 2:
        c1 = c1[:2]
        promotion = c1[-1]
    
    return movePool.pop (history, Cord(c0), Cord(c1), promotion)

def parseAN (history, an):
    """ Parse an Algebraic Notation string """
    if not 4 <= len(an) <= 5: raise ValueError, "Bad an move, %s" % an
    c0 = Cord(an[:2])
    c1 = Cord(an[2:4])
    
    if len(an) == 5:
        return movePool.pop(history, c0, c1, an[4])
    return movePool.pop(history, c0, c1)

def toSAN (history):
    """ Returns a Short/Abbreviated Algebraic Notation string of a move 
        The move should be the last one in history"""
    
    board = history[-2]
    move = history.moves[-1]
    
    idea = {
        "white": {"k":"♔", "q":"♕", "r":"♖", "b":"♗", "n":"♘", "p":"♙"},
        "black": {"k":"♚", "q":"♛", "r":"♜", "b":"♝", "n":"♞", "p":"♟"}
    }
    
    c0, c1 = move.cords
    if board[c0].sign == "k":
        if c0.x - c1.x == 2:
            return "O-O-O"
        elif c0.x - c1.x == -2:
            return "O-O"
    
    part0 = part1 = ""
    
    if board[c0].sign != "p":
        part0 += board[c0].sign.upper()
    #part0 += idea[board[c0].color][board[c0].sign]
    
    part1 = str(c1)
    
    #Can this be moved to validator? It is quite hacky... (Because of old history)
    if len(history) >= 2 and not board[c0].sign in ("p","k"):
        xs = []
        ys = []
        
        if history.movelist[-2] != None:
            for cord0, cord1s in history.movelist[-2].iteritems():
                if move.cord1 in cord1s and not cord0.__eq__(move.cord0) and \
                        board[cord0].sign == board[move.cord0].sign:
                    xs.append(cord0.x)
                    ys.append(cord0.x)
        else:
            hisclon = history.clone()
            del hisclon.moves[-1]
            del hisclon.boards[-1]
            del hisclon.movelist[-1]
            for y, row in enumerate(board.data):
                for x, piece in enumerate(row):
                    if not piece: continue
                    if piece.sign != board[c0].sign: continue
                    if piece.color != board[c0].color: continue
                    if y == c0.y and x == c0.x: continue
                    cord0 = Cord(x, y)
                    move = movePool.pop(hisclon, cord0, move.cord1)
                    from validator import validate
                    if validate (move, hisclon, False):
                        xs.append(cord0.x)
                        ys.append(cord0.x)
                    movePool.add(move)

        if xs or ys:
            if not move.cord0.y in ys and not move.cord0.x in xs:
                part0 += move.cord0.cx
            elif move.cord0.y in ys and not move.cord0.x in xs:
                part0 += move.cord0.cx
            elif move.cord0.x in xs and not move.cord0.y in ys:
                part0 += move.cord0.cy
            else: part0 += str(move.cord0)
            

    if board[c1] != None:
        part1 = "x" + part1
        if board[c0].sign == "p":
            part0 += c0.cx
    
    notat = part0 + part1
    if board[c0].sign == "p" and c1.y in [0,7]:
        notat += "="+move.promotion.upper()
    
    from Utils import validator
    if history.status in (validator.WHITEWON, validator.BLACKWON):
        notat += "#"
    elif validator.isCheck(history, history.curCol()):
        notat += "+"
        
    return notat
    
def toLAN (history):
    """ Returns a Long/Expanded Algebraic Notation string of a move
        The move should be the last one in history"""
    
    board = history[-2]
    move = history.moves[-1]
    
    s = str(move.cord1) + "-" + str(move.cord1)
    if board[move.cord1].sign != "p":
        s = board[move.cord1].sign.upper() + s
    if board[move.cord1].sign == "p" and move.cord1.y in (0,7):
        return s + "=" + move.promotion.upper()
    return s
    
def toAN (history):
    """ Returns a Algebraic Notation string of a move
        The move should be the last one in history"""
    
    board = history[-2]
    move = history.moves[-1]
    
    s = str(move.cord0) + str(move.cord1)
    if board[move.cord0].sign == "p" and move.cord1.y in (0,7):
        return s + move.promotion
    return s

def toFAN (history, move):
    """ Returns a Figurine Algebraic Notation string of a move """
    pass
