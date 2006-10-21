#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from Utils.Cord import Cord
from System.Log import log

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
    def pop (self, history, move, promotion="q"):
        if len(self.objects) <= 0:
            return Move(history, move, promotion)
        mv = self.objects.pop()
        mv.init(history, move, promotion)
        return mv
    def add (self, move):
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
    
    def __init__ (self, history, move, promotion="q"):
        """(history, notat) or
           (history, (cord0, cord1), [promotion]) or
           (history, (strcord1, strcord2), [promotion])
           Promotion will be set to None, if not aplieable"""
           
        self.enpassant = None # None or Cord
        self.castling = None # None or (rookCordSide, rookCordMiddle)
        self.promotion = None # "q" or "r" or "b" or "k" or "n"
        
        #try:
        self.init (history, move, promotion)
        #except Exception, e:
        #    log.error(str(e))
        #    import traceback
        #    r = doDialog (move, traceback.format_exc())
        #    if not r:
        #        log.error("Could not parse %s. User did not specify" % str(move))
        #        import sys; sys.exit()
        #    self.cord0, self.cord1 = r
        #    self.promotion = "q"
        
    def init (self, history, move, promotion):
        board = history[-1]
        self.promotion = promotion
        
        if type(move) in (list, tuple):
            if type(move[0]) == str:
                self.cord0, self.cord1 = [Cord(a) for a in move]
            else: self.cord0, self.cord1 = move
            if board[self.cord0].sign == "k":
                r = self.cord0.y
                if self.cord0.x - self.cord1.x == -2:
                    self.castling = (Cord(7,r),Cord(5,r))
                elif self.cord0.x - self.cord1.x == 2:
                    self.castling = (Cord(0,r),Cord(3,r))
            elif board[self.cord0].sign == "p" and self.cord0.y in (3,4):
                if self.cord0.x != self.cord1.x and board[self.cord1] == None:
                    self.enpassant = Cord(self.cord1.x, self.cord0.y)
        
        else:
            notat = move
            notat = notat.replace("0","o").replace("O","o")
            notat = notat.replace("=","").replace("+","").replace("#","")
            notat = notat.strip()
            if notat[-1].lower() in ("q", "r", "b", "n"):
                self.promotion = notat[-1].lower()
                notat = notat[:-1]
            color = history.curCol()
            
            if notat.startswith("o-o"):
                if color == "white":
                    row = "1"
                else: row = "8"
                self.cord0 = Cord("e"+row)
                if notat == "o-o":
                    self.cord1 = Cord("g"+row)
                    self.castling = (Cord("h"+row), Cord("f"+row))
                else:
                    self.cord1 = Cord("c"+row)
                    self.castling = (Cord("a"+row), Cord("d"+row))
                return
    
            if "x" in notat:
                since, then = notat.split("x")
                self.cord1 = Cord(then)
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
                self.cord1 = Cord(notat)
            from Utils.validator import getMovePointingAt
            cord0 = getMovePointingAt(history, self.cord1, color, sign, row, col)
            if cord0 == None: raise ParsingError, "Unable to parse move %s" % move
            self.cord0 = cord0

            if board[self.cord0].sign == "p" and self.cord0.y in [3,4]:
                if self.cord0.x != self.cord1.x and board[self.cord1] == None:
                    self.enpassant = Cord(self.cord1.x, self.cord0.y)

    def algNotat (self, history):
        """Note: History should have thismove as last element in its .moves list"""
        
        if len(history) > 0:
            board = history[-2]
        else: board = history[-1]
        
        idea = {
            "white": {"k":"♔", "q":"♕", "r":"♖", "b":"♗", "n":"♘", "p":"♙"},
            "black": {"k":"♚", "q":"♛", "r":"♜", "b":"♝", "n":"♞", "p":"♟"}
        }
        
        c0, c1 = self.cords
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
                    if self.cord1 in cord1s and not cord0.__eq__(self.cord0) and \
                            board[cord0].sign == board[self.cord0].sign:
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
                        move = movePool.pop(hisclon, (cord0, self.cord1))
                        from validator import validate
                        if validate (move, hisclon, False):
                            xs.append(cord0.x)
                            ys.append(cord0.x)
                        movePool.add(move)

            if xs or ys:
                if not self.cord0.y in ys and not self.cord0.x in xs:
                    part0 += self.cord0.cx
                elif self.cord0.y in ys and not self.cord0.x in xs:
                    part0 += self.cord0.cx
                elif self.cord0.x in xs and not self.cord0.y in ys:
                    part0 += self.cord0.cy
                else: part0 += str(self.cord0)
                

        if board[c1] != None:
            part1 = "x" + part1
            if board[c0].sign == "p":
                part0 += c0.cx
        
        notat = part0 + part1
        if board[c0].sign == "p" and c1.y in [0,7]:
            notat += "="+self.promotion.upper()
        
        from Utils import validator
        if history.status in (validator.WHITEWON, validator.BLACKWON):
            notat += "#"
        elif validator.isCheck(history, history.curCol()):
            notat += "+"
            
        return notat
    
    def gnuchess (self, board):
        s = str(self.cord0) + str(self.cord1)
        if board[self.cord0].sign == "p" and self.cord1.y in (0,7):
            return s + self.promotion
        return s

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
