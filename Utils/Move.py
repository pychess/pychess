#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from Utils.Cord import Cord
from Utils.Log import log

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

class Move:
    enpassant = None # None, Cord
    castling = None # None, (rookCordSide, rookCordMiddle)
    promotion = None # "q", "r", "b", "k", "n"

    def _get_cords (self):
        return (self.cord0, self.cord1)
    cords = property(_get_cords)
    
    def __init__ (self, history, move, promotion="q"):
        """(board, notat) or
           (board, (cord0, cord1), [promotion]) or
           (board, (strcord1, strcord2), [promotion])
           Promotion will be set to None, if not aplieable"""
        
        #try:
        self.privateInit (history, move, promotion)
        #except Exception, e:
        #    log.error(str(e))
        #    import traceback
        #    r = doDialog (move, traceback.format_exc())
        #    if not r:
        #        log.error("Could not parse %s. User did not specify" % str(move))
        #        import sys; sys.exit()
        #    self.cord0, self.cord1 = r
        #    self.promotion = "q"
        
    def privateInit (self, history, move, promotion):
        self.number = number = len(history) -1
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
            elif board[self.cord0].sign == "p" and self.cord0.y in [3,4]:
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
            color = number % 2 == 0 and "white" or "black"
            
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
                print "notat er:",notat
                self.cord1 = Cord(notat)
            from Utils.validator import getPiecesPointingAt
            mv = getPiecesPointingAt(history, self.cord1, color, sign, row, col)
            assert mv != None
            self.cord0 = mv.cord0

            if board[self.cord0].sign == "p" and self.cord0.y in [3,4]:
                if self.cord0.x != self.cord1.x and board[self.cord1] == None:
                    self.enpassant = Cord(self.cord1.x, self.cord0.y)

    def algNotat (self, history):
        """Note: History should have thismove as last element in its .move list"""
        
        #FIXME: Don't know the rule, of setting row/collum in front
        #FIXME!!!!!! Don't set the enpassant variabel
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
                return "o-o-o"
            elif c0.x - c1.x == -2:
                return "o-o"
        
        part0 = part1 = ""
        
        if board[c0].sign != "p":
            part0 += board[c0].sign.upper()
        #part0 += idea[board[c0].color][board[c0].sign]
        
        part1 = str(c1)
        
        if board[c1] != None:
            part1 = "x" + part1
            if board[c0].sign == "p":
                part0 += c0.cx
                
        notat = part0 + part1
        if board[c0].sign == "p" and c1.y in [0,7]:
            notat += self.promotion
        
        from Utils.validator import _isChess
        opcolor = board[c0].color == "white" and "black" or "white"
        if _isChess(history, opcolor):
            notat += "+"
            
        return notat
    
    def gnuchess (self, board):
        s = str(self.cord0) + str(self.cord1)
        if board[self.cord0].sign == "p" and self.cord1.y in (0,7):
            return s + self.promotion
        return s

    def __repr__ (self):
        return str(self.cord0) + str(self.cord1)

    def __eqal__ (self, other):
        return other.cord0 == self.cord0 and other.cord1 == self.cord1
