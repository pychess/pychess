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
from Utils.validator import validate
from Utils import validator

def intersects (r1, r2):
    r = r1.intersect(r2)
    return r.width+r.height > 0

# This might be an ugly hack and a bad idea,
# as four squares instead of one will be redrawn on hover.
# Until now, though, it works fine for ensuring, that no ugly "stripes"
# are left when you for example select a cord.
def grow (r, grow = 2):
    #r.x -= grow
    #r.y -= grow
    r.width += grow
    r.height += grow
    return r

class BoardView (gtk.DrawingArea):
    
    __gsignals__ = {
        'shown_changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,))
    }
    
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.history = History()
        self.connect("expose_event", self.expose)
        self.history.connect_after("changed", self.move)
        self.set_size_request(300,300)
        
    def move (self, history):
        if self.shown+2 < len(history):
            return
        self.shown += 1
    
    #############################
    #          Drawing          #
    #############################
    
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        rect = (event.area.x, event.area.y, event.area.width, event.area.height)
        context.rectangle(*rect)
        context.clip()
        self.draw(context, event.area)
        return False
    
    square = None
    def draw(self, context, rect):
        r = self.get_allocation()
        square = float(min(r.width, r.height)) -4
        xc = float(r.width)/2 - square/2
        yc = float(r.height)/2 - square/2 -2
        s = square/8
        self.square = (xc, yc, square, s)
    
        self.drawBoard (context)
        self.drawSpecial (context)
        self.drawLastMove(context)
        self.drawArrows(context)
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
    
    def drawLastMove (self, context):
        if not self.lastMove: return
    
        wh = 0.25 # Width of marker
        p0 = 0.15 # Padding on last cord
        p1 = 0.085 # Padding on current cord
        sw = 0.02 # Stroke width
        
        context.save()
        
        d0 = {-1:1-p0,1:p0}
        d1 = {-1:1-p1,1:p1}
        ms = ((1,1),(-1,1),(-1,-1),(1,-1))
        
        r = self.cord2Rect(self.lastMove.cord0)
        for m in ms:
            context.move_to(
                r.x+(d0[m[0]]+wh*m[0])*r.width,
                r.y+(d0[m[1]]+wh*m[1])*r.width)
            context.rel_line_to(
                0, -wh*r.width*m[1])
            context.rel_curve_to(
                0, wh*r.width*m[1]/2.0,
                -wh*r.width*m[0]/2.0, wh*r.width*m[1],
                -wh*r.width*m[0], wh*r.width*m[1])
            context.close_path()
        
        r = self.cord2Rect(self.lastMove.cord1)
        for m in ms:
            context.move_to(
                r.x+d1[m[0]]*r.width,
                r.y+d1[m[1]]*r.width)
            context.rel_line_to(
                wh*r.width*m[0], 0)
            context.rel_curve_to(
                -wh*r.width*m[0]/2.0, 0,
                -wh*r.width*m[0], wh*r.width*m[1]/2.0,
                -wh*r.width*m[0], wh*r.width*m[1])
            context.close_path()
        
        context.set_source_rgba(.929, .831, 0, .5)
        context.fill_preserve()
        context.set_source_rgba(.769, 0.627, 0, .7)
        context.set_line_width(sw*r.width)
        context.stroke()
        
        context.restore()
    
    def drawArrows (self, context):
        if self.shown != len(self.history.moves):
            return
    
        aw = 0.3 # Arrow width
        ahw = 0.72 # Arrow head width
        ahh = 0.64 # Arrow head height
        asw = 0.08 # Arrow stroke width
        def drawArrow (cords, fillc, strkc):
            context.save()
            
            lvx = cords[1].x-cords[0].x
            lvy = cords[0].y-cords[1].y
            from math import sqrt
            l = float(sqrt(lvx**2+lvy**2))
            vx = lvx/l
            vy = lvy/l
            v1x = -vy
            v1y = vx
            r = self.cord2Rect(cords[0])
            px = r.x+r.width/2.0
            py = r.y+r.height/2.0
            ax = v1x*r.width*aw/2
            ay = v1y*r.width*aw/2
            context.move_to(px+ax, py+ay)
            p1x = px+(lvx-vx*ahh)*r.width
            p1y = py+(lvy-vy*ahh)*r.width
            context.line_to(p1x+ax, p1y+ay)
            lax = v1x*r.width*ahw/2
            lay = v1y*r.width*ahw/2
            context.line_to(p1x+lax, p1y+lay)
            context.line_to(px+lvx*r.width, py+lvy*r.width)
            context.line_to(p1x-lax, p1y-lay)
            context.line_to(p1x-ax, p1y-ay)
            context.line_to(px-ax, py-ay)
            context.close_path()
            
            context.set_source_rgba(*fillc)
            context.fill_preserve()
            context.set_line_join(gtk.gdk.JOIN_ROUND)
            context.set_line_width(asw*r.width)
            context.set_source_rgba(*strkc)
            context.stroke()
            context.restore()
            
        if self.greenarrow:
            drawArrow(self.greenarrow, (.54,.886,0.2,0.9), (.306,.604,.024,1))
        if self.redarrow:
            drawArrow(self.redarrow, (.937,.16,0.16,0.9), (.643,0,0,1))
        
    def redraw_canvas(self, rect=None):
        if self.window:
            if not rect:
                alloc = self.get_allocation()
                rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    ###############################
    #          Cord vars          #
    ###############################

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
    
    ################################
    #          Arrow vars          #
    ################################
    
    _redarrow = None
    def _set_redarrow (self, cords):
        self._redarrow = cords
        idle_add(self.redraw_canvas)
    def _get_redarrow (self):
        return self._redarrow
    redarrow = property(_get_redarrow, _set_redarrow)
    
    _greenarrow = None
    def _set_greenarrow (self, cords):
        self._greenarrow = cords
        idle_add(self.redraw_canvas)
    def _get_greenarrow (self):
        return self._greenarrow
    greenarrow = property(_get_greenarrow, _set_greenarrow)
    
    ################################
    #          Other vars          #
    ################################
    
    _shown = 0
    def _get_shown(self):
        return self._shown
    def _set_shown(self, shown):
        if self.history and 0 <= shown < len(self.history):
            self._shown = shown
            self.emit("shown_changed", self.shown)
            if self.history.moves and self.shown:
                self.lastMove = self.history.moves[self.shown-1]
            else: self.lastMove = None
            idle_add(self.redraw_canvas)
    shown = property(_get_shown, _set_shown)
    
    _fromWhite = True
    def _set_fromWhite (self, fromWhite):
        self._fromWhite = fromWhite
        self.redraw_canvas()
    def _get_fromWhite (self):
        return self._fromWhite
    fromWhite = property(_get_fromWhite, _set_fromWhite)
    
    lastMove = None
    
    ###########################
    #          Other          #
    ###########################
    
    def cord2Rect (self, cord):
        xc, yc, square, s = self.square
        x = (self.fromWhite and [cord.x] or [7-cord.x])[0]
        y = (self.fromWhite and [7-cord.y] or [cord.y])[0]
        r = (xc+x*s, yc+y*s, s, s)
        return gtk.gdk.Rectangle (*[int(v) for v in r])
    
    def cord2Point (self, cord):
        r = self.cord2Rect(cord)
        return (r.x, r.y)

    def isLight (self, cord):
        x, y = cord.cords
        return x % 2 + y % 2 == 1
