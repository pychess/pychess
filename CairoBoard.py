# -*- coding: UTF-8 -*-

import pygtk
pygtk.require("2.0")
import gtk, gtk.gdk, re
from gobject import *
from Numeric import arange
from gfx.Pieces import piece as getPiece
from Utils.History import History
from Utils.Cord import Cord
from Utils.Move import Move
from math import floor
from Utils.validator import validate, getLegalMoves

def intersects (r1, r2):
    r = r1.intersect(r2)
    return r.width+r.height > 0

def grow (r, grow = 0):
    r.x -= grow
    r.y -= grow
    r.width += grow
    r.height += grow
    return r

class CairoBoard(gtk.DrawingArea):
    
    __gsignals__ = {
        'piece_moved' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'shown_changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,)),
        'history_changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,))
    }
    
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.connect("expose_event", self.expose)
        self.widgets = gtk.glade.XML("glade/promotion.glade")
    
    _history = None
    def _get_history(self):
        return self._history
    def _set_history(self, history):
        self._history = history
        self.emit("history_changed", self.history)
        self.redraw_canvas()
    history = property(_get_history, _set_history)
    
    _shown = 0
    def _get_shown(self):
        return self._shown
    def _set_shown(self, shown):
        if self.history and 0 <= shown < len(self.history):
            self._shown = shown
            self.emit("shown_changed", self.shown)
            idle_add(self.redraw_canvas)
    shown = property(_get_shown, _set_shown)
    
    def move (self, move, animate):
        self.history.add(move)
        self.shown += 1
    
    def emit_move_signal (self, cord0, cord1):
        
        if not validate(Move(self.history, (cord0, cord1)), self.history):
            return
        
        promotion = "q"
        if len(self.history) > 0 and self.history[-1][cord0] != None and \
                self.history[-1][cord0].sign == "p" and cord1.y in [0,7]:
            res = int(self.widgets.get_widget("promotionDialog").run())
            self.widgets.get_widget("promotionDialog").hide()
            if res == int(gtk.RESPONSE_DELETE_EVENT):
                return
            promotion = ["q","r","b","n"][res]
            
        move = Move(self.history, (cord0, cord1), promotion)
        self.emit("piece_moved", move)
    
    #          Drawing          #
    
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        rect = (event.area.x, event.area.y, event.area.width, event.area.height)
        context.rectangle(*rect)
        context.clip()
        self.draw(context, event.area)
        return False
    
    def draw(self, context, rect):
        r = self.get_allocation()
        square = float(min(r.width, r.height)) -4
        xc = float(r.width)/2 - square/2
        yc = float(r.height)/2 - square/2 -2
        s = square/8
        self.square = (xc, yc, square, s)
    
        self.drawBoard (context)
        self.drawSpecial (context)
        if not self.history: return
        pieces = self.history[self.shown]
        self.drawPieces (context, pieces, rect)
    
    def drawBoard(self, context):
        xc, yc, square, s = self.square
        for x in range(8):
            for y in range(8):
                if x % 2 + y % 2 == 1:
                    context.rectangle(xc+x*s,yc+y*s,s,s)
        
        state = gtk.STATE_NORMAL
        if self.history and self.shown != len(self.history)-1:
            state = gtk.STATE_INSENSITIVE
        context.set_source_color(self.get_style().dark[state])
        
        context.fill_preserve()
        context.new_path()
    
    def drawPieces(self, context, pieces, rect):
        xc, yc, square, s = self.square
        context.set_source_color(self.get_style().black)
        for y in xrange(len(pieces)):
            for x in xrange(len(pieces[y])):
                piece = pieces[y][x]
                if not piece: continue
                if not intersects(self.cord2Rect(Cord(x,y)), rect):
                    continue
                str = piece.name[:1].upper() + piece.name[1:].lower()
                cx, cy = self.cord2Point(Cord(x,y))
                getPiece(piece.color+str, context, s, cx, cy)
        context.fill_preserve()
        context.new_path()
    
    def drawSpecial (self, context):
        used = []
        for cord, state in ((self.active, gtk.STATE_ACTIVE),
                            (self.selected, gtk.STATE_SELECTED),
                            (self.hover, gtk.STATE_PRELIGHT)):
            if not cord: continue
            if cord in used: continue
            used += [cord]
            xc, yc, square, s = self.square
            x, y = self.cord2Point(cord)
            context.rectangle(x, y, s, s)
            style = self.isLight(cord) and self.get_style().bg or self.get_style().dark
            context.set_source_color(style[state])
            context.fill_preserve()
            context.new_path()
    
    def redraw_canvas(self, rect=None):
        if self.window:
            if not rect:
                alloc = self.get_allocation()
                rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    _selected = None
    def _set_selected (self, cord):
        self._active = None
        if self._selected == cord: return
        if self._selected:
            r = self.cord2Rect(self._selected)
            if cord: r = r.union (self.cord2Rect(cord))
        elif cord: r = self.cord2Rect(cord)
        self._selected = cord
        self.redraw_canvas(grow(r))
        if cord == None: self.legalMoves = []
        else: self.legalMoves = getLegalMoves(self.history, cord)
    def _get_selected (self):
        return self._selected
    selected = property(_get_selected, _set_selected)
    
    _hover = None
    def _set_hover (self, cord):
        if self._hover == cord: return
        if self._hover:
            r = self.cord2Rect(self._hover)
            if cord: r = r.union (self.cord2Rect(cord))
        elif cord: r = self.cord2Rect(cord)
        self._hover = cord
        self.redraw_canvas(grow(r))
    def _get_hover (self):
        return self._hover
    hover = property(_get_hover, _set_hover)
    
    _active = None
    def _set_active (self, cord):
        if self._active == cord: return
        if self._active:
            r = self.cord2Rect(self._active)
            if cord: r = r.union (self.cord2Rect(cord))
        elif cord: r = self.cord2Rect(cord)
        self._active = cord
        self.redraw_canvas(grow(r))
    def _get_active (self):
        return self._active
    active = property(_get_active, _set_active)
    
    _fromWhite = True
    def _set_fromWhite (self, fromWhite):
        self._fromWhite = fromWhite
        self.redraw_canvas()
    def _get_fromWhite (self):
        return self._fromWhite
    fromWhite = property(_get_fromWhite, _set_fromWhite)
    
    def isLight (self, cord):
        x, y = cord.cords
        return x % 2 + y % 2 == 1
    
    legalMoves = []
    def isSelectable (self, cord):
        if not self.history: return False
        if not cord: return False

        if self.shown != len(self.history)-1:
            return False

        if cord in self.legalMoves:
            return True
        if self.history[-1][cord] == None:
            return False

        color = len(self.history) % 2 == 0 and "black" or "white"
        if self.history[-1][cord].color != color:
            return False
        
        return True
    
    def point2Cord (self, x, y):
        xc, yc, square, s = self.square
        y -= yc; x -= xc
        if (x < 0 or x >= square or y < 0 or y >= square):
            return None
        x = floor(x/s); y = floor(y/s)
        if self.fromWhite: return Cord(x, 7-y)
        return Cord(7-x, y)

    def cord2Rect (self, cord):
        xc, yc, square, s = self.square
        x = (self.fromWhite and [cord.x] or [7-cord.x])[0]
        y = (self.fromWhite and [7-cord.y] or [cord.y])[0]
        r = (xc+x*s, yc+y*s, s, s)
        return gtk.gdk.Rectangle (*[int(v) for v in r])

    def cord2Point (self, cord):
        r = self.cord2Rect(cord)
        return (r.x, r.y)
    
    def button_press (self, widget, event):
        self.eventbox.grab_focus()
        cord = self.point2Cord (event.x, event.y)
        
        if not self.isSelectable(cord):
            self.active = None
        else: self.active = cord
    
    def button_release (self, widget, event):
        cord = self.point2Cord (event.x, event.y)
        if self.selected == cord or cord == None:
            self.selected = None
        elif cord == self.active:
            color = len(self.history) % 2 == 0 and "black" or "white"
            if self.history[-1][cord] != None and self.history[-1][cord].color == color:
                self.selected = self.point2Cord (event.x, event.y)
            elif self.selected:
                self.emit_move_signal(self.selected, cord)
                self._hover = cord
                self.selected = None
            else: self.selected = self.point2Cord (event.x, event.y)
        else: self.active = None
    
    def motion_notify (self, widget, event):
        cord = self.point2Cord (event.x, event.y)
        if cord == None: return
        if not self.isSelectable(cord):
            self.hover = None
        else: self.hover = cord

    def leave_notify (self, widget, event):
        a = self.get_allocation()
        if not (0 <= event.x < a.width and 0 <= event.y < a.height):
            self.hover = None
    
    def focus_out (self, widget, event):
        pass
    #    self.selected = None
    #    self.active = None
