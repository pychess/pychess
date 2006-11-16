# -*- coding: UTF-8 -*-

import pygtk
pygtk.require("2.0")
import gtk, gtk.gdk, re
from gobject import *
from gfx.Pieces import drawPiece
from Utils.History import History
from Utils.Cord import Cord
from Utils.Move import Move
from math import floor, ceil
from Utils.validator import validate
from Utils import validator
import pango
from time import time
from Utils.const import *

def intersects (r0, r1):
    w0 = r0.width + r0.x
    h0 = r0.height + r0.y
    w1 = r1.width + r1.x
    h1 = r1.height + r1.y
    return  (w1 < r1.x or w1 > r0.x) and \
            (h1 < r1.y or h1 > r0.y) and \
            (w0 < r0.x or w0 > r1.x) and \
            (h0 < r0.y or h0 > r1.y)

def join (r0, r1):
    """ Take (x, y, w, [h]) squares """
    
    if not r0: return r1
    if not r1: return r0
    if not r0 and not r1: return None
    
    if len(r0) == 3:
        r0 = (r0[0], r0[1], r0[2], r0[2])
    if len(r1) == 3:
        r1 = (r1[0], r1[1], r1[2], r1[2])
    
    x1 = min(r0[0], r1[0])
    x2 = max(r0[0]+r0[2], r1[0]+r1[2])
    y1 = min(r0[1], r1[1])
    y2 = max(r0[1]+r0[3], r1[1]+r1[3])
    
    return (x1, y1, x2 - x1, y2 - y1)

def rect (r):
    x, y = [int(floor(v)) for v in r[:2]]
    w = int(ceil(r[2]))
    if len(r) == 4:
        h = int(ceil(r[3]))
    else: h = w
    return gtk.gdk.Rectangle (x, y, w, h)

range8 = range(8)

ANIMATION_TIME = .5

class BoardView (gtk.DrawingArea):
    
    __gsignals__ = {
        'shown_changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,))
    }
    
    def __init__(self):
        gtk.DrawingArea.__init__(self)
        self.history = History(special=True)
        self.connect("expose_event", self.expose)
        self.history.connect_after("changed", self.move)
        self.history.connect("cleared", self.reset)
        self.set_size_request(300,300)
        
        self.animationID = -1
        self.animationStart = time()
        self.lastShown = None
        self.deadlist = []
        
        self.padding = 0 # Set to self.pad when setcords is active
        self.square = None # An object global variable with the current board size
        self.pad = 0.13 # Used when setcords is active
        self._selected = None
        self._hover = None
        self._active = None
        self._redarrow = None
        self._greenarrow = None
        self._bluearrow = None
        self._shown = 0
        self._fromWhite = True
        self._showCords = False
        self.lastMove = None
        
    def move (self, history):
        if self.shown+2 < len(history):
            return
        self.shown = len(history)-1
    
    def reset (self, history):
        self.shown = 0
        self.lastMove = None
    
    ###############################
    #          Animation          #
    ###############################
    
    def _get_shown(self):
        return self._shown
        
    def _set_shown(self, shown):
        
        if not self.history or not 0 <= shown < len(self.history):
            return
        
        if len(self.history) == 1 and shown == 0:
            self._shown = shown
            idle_add(self.redraw_canvas)
            return
        
        step = shown > self.shown and 1 or -1
        
        self.deadlist = []
        for i in range(self.shown, shown, step):
            board0 = self.history[i]
            board1 = self.history[i+step]
            
            for y, row in enumerate(board0.data):
                for x, piece in enumerate(row):
                    if not piece: continue
                    if piece.x != None:
                        # Skip if already moving
                        continue
                    if piece != board1.data[y][x]:
                        next = Cord (x, y + (board0.color == WHITE and 1 or -1))
                        if step > 0 and (board1.data[y][x] != None or \
                           board0.enpassant == next and \
                           board1[board0.enpassant] != None):
                            # A piece is dying
                            self.deadlist.append((piece,x,y))
                        else:
                            # It has moved
                            piece.x = x
                            piece.y = y
                    
        
        self._shown = shown
        self.emit("shown_changed", self.shown)
        
        if self.animationID != -1:
            source_remove(self.animationID)
        
        self.animationStart = time()
        def do():
            if self.lastMove:
                paintBox = self.cord2Rect(self.lastMove.cord0)
                paintBox = join(paintBox, self.cord2Rect(self.lastMove.cord1))
                self.lastMove = None
                self.redraw_canvas(rect(paintBox))
            if self.shown != 0:
                self.lastMove = self.history.moves[self.shown-1]
            else: self.lastMove = None
            self.runAnimation(redrawMisc = True)
            self.animationID = idle_add(self.runAnimation)
        idle_add(do)
        
    shown = property(_get_shown, _set_shown)
    
    def runAnimation (self, redrawMisc=False):
        mod = min(1.0, (time()-self.animationStart)/ANIMATION_TIME)
        board = self.history[self.shown]

        paintBox = None
        
        for y, row in enumerate(board.data):
            for x, piece in enumerate(row):
                if not piece: continue
                
                if piece.x != None:
                    newx = piece.x + (x-piece.x)*mod
                    newy = piece.y + (y-piece.y)*mod
                    
                    if not paintBox:
                        paintBox = self.fcord2Rect(piece.x, piece.y)
                    else: paintBox = join(paintBox, self.fcord2Rect(piece.x, piece.y))
                    paintBox = join(paintBox, self.fcord2Rect(newx, newy))
                    
                    if (newx <= x <= piece.x or newx >= x >= piece.x) and \
                       (newy <= y <= piece.y or newy >= y >= piece.y) or \
                       abs(newx-x) < 0.01 and abs(newy-y) < 0.01:
                        piece.x = None
                        piece.y = None
                    else:
                        piece.x = newx
                        piece.y = newy
                
                if piece.opacity < 1:
                    if piece.x != None:
                        px = piece.x
                        py = piece.y
                    else:
                        px = x
                        py = y
                        
                    if not paintBox:
                        paintBox = self.fcord2Rect(px, py)
                    else: paintBox = join(paintBox, self.fcord2Rect(px, py))
                    
                    newOp = piece.opacity + (1-piece.opacity)*mod
                    
                    if newOp >= 1 >= piece.opacity or abs(1-newOp) < 0.01:
                        piece.opacity = 1
                    else: piece.opacity = newOp
        
        for i, (piece, x, y) in enumerate(self.deadlist):
            if not paintBox:
                paintBox = self.fcord2Rect(x, y)
            else: paintBox = join(paintBox, self.fcord2Rect(x, y))
            
            newOp = piece.opacity + (0-piece.opacity)*mod
            
            if newOp <= 0 <= piece.opacity or abs(0-newOp) < 0.01:
                del self.deadlist[i]
            else: piece.opacity = newOp
            
        if redrawMisc:
            for cord in (self.selected, self.hover, self.active):
                if cord:
                    paintBox = join(paintBox, self.cord2Rect(cord))
            for arrow in (self.redarrow, self.greenarrow, self.bluearrow):
                if arrow:
                    paintBox = join(paintBox, self.cord2Rect(arrow[0]))
                    paintBox = join(paintBox, self.cord2Rect(arrow[1]))
            if self.lastMove:
                paintBox = join(paintBox, self.cord2Rect(self.lastMove.cord0))
                paintBox = join(paintBox, self.cord2Rect(self.lastMove.cord1))
        
        if paintBox:
            self.redraw_canvas(rect(paintBox))
        
        return paintBox and True or False
    
    def startAnimation (self):
        self.animationStart = time()
        def do():
            self.runAnimation(redrawMisc = True)
            self.animationID = idle_add(self.runAnimation)
        idle_add(do)
    
    #############################
    #          Drawing          #
    #############################
    
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        r = (event.area.x, event.area.y, event.area.width, event.area.height)
        context.rectangle(r[0]-.5, r[1]-.5, r[2]+1, r[3]+1)
        context.clip()
        
        if False:
            import profile
            profile.runctx("self.draw(context, event.area)", locals(), globals(), "/tmp/pychessprofile")
            from pstats import Stats
            s = Stats("/tmp/pychessprofile")
            s.sort_stats('cumulative')
            s.print_stats()
        else:
            self.draw(context, event.area)
        
        return False
    
    def draw(self, context, r):
        p = (1-self.padding)
        alloc = self.get_allocation()
        square = float(min(alloc.width, alloc.height))*p
        xc = alloc.width/2. - square/2
        yc = alloc.height/2. - square/2
        s = square/8
        self.square = (xc, yc, square, s)
        
        self.drawBoard (context)
        self.drawCords (context)
        if not self.history: return
        pieces = self.history[self.shown]
        self.drawSpecial (context)
        self.drawArrows (context)
        self.drawPieces (context, pieces, r)
        self.drawLastMove (context)
        
        #context.rectangle(r.x,r.y,r.width,r.height)
        #context.set_source_rgb(1,0,0)
        #context.stroke()
        
    def drawCords (self, context):
        thickness = 0.01
        signsize = 0.04
        
        if not self.showCords: return
        xc, yc, square, s = self.square
        t = thickness*square
        ss = signsize*square
        
        context.rectangle(xc-t*1.5,yc-t*1.5,square+t*3,square+t*3)
        context.set_source_color(self.get_style().dark[gtk.STATE_NORMAL])
        context.set_line_width(t)
        context.set_line_join(gtk.gdk.JOIN_ROUND)
        context.stroke()
        
        pangoScale = float(pango.SCALE)
        
        for n in range8:
            o = (self.fromWhite and [n] or [7-n])[0]
            
            layout = self.create_pango_layout("%d" % (8-o))
            layout.set_font_description(pango.FontDescription("bold %d" % ss))
            
            w = layout.get_extents()[1][2]/pangoScale
            h = layout.get_extents()[0][3]/pangoScale
            
            context.move_to(xc-t*2.5-w, s*n+yc+h/2+t)
            context.show_layout(layout)
            
            context.move_to(xc+square+t*2.5, s*n+yc+h/2+t)
            context.show_layout(layout)
            
            layout = self.create_pango_layout(chr(o+ord("A")))
            layout.set_font_description(pango.FontDescription("bold %d" % ss))
            
            w = layout.get_pixel_size()[0]
            h = layout.get_pixel_size()[1]
            y = layout.get_extents()[1][1]/pangoScale
            
            context.move_to(xc+s*n+s/2.-w/2., yc-h-t*1.5)
            context.show_layout(layout)
            
            context.move_to(xc+s*n+s/2.-w/2., yc+square+t*1.5+abs(y))
            context.show_layout(layout)
    
    def drawBoard(self, context):
        xc, yc, square, s = self.square
        for x in range8:
            for y in range8:
                if x % 2 + y % 2 == 1:
                    context.rectangle(xc+x*s,yc+y*s,s,s)
        
        context.set_source_color(self.get_style().dark[gtk.STATE_NORMAL])
        context.fill()
        #context.new_path()
    
    def drawPieces(self, context, pieces, r):
        xc, yc, square, s = self.square
        
        for piece, x, y in self.deadlist:
            x = (self.fromWhite and [x] or [7-x])[0]
            y = (self.fromWhite and [7-y] or [y])[0]
            context.move_to(xc+x*s, yc+y*s)
            context.set_source_rgba(0,0,0,piece.opacity)
            drawPiece(piece, context, s)
            context.fill()
            
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
                if not piece or piece.opacity == 1:
                    continue
                cx, cy = self.cord2Point(Cord(x,y))
                context.move_to(cx, cy)
                context.set_source_rgba(0,0,0,piece.opacity)
                drawPiece(piece, context, s)
                context.fill()
                
        context.set_source_rgb(0,0,0)
        
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
                if not piece or piece.x != None or piece.opacity < 1:
                    continue
                if not intersects(rect(self.cord2Rect(Cord(x,y))), r):
                    continue
                cx, cy = self.cord2Point(Cord(x,y))
                context.move_to(cx, cy)
                drawPiece(piece, context, s)
        
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
                if not piece or piece.x == None or piece.opacity < 1:
                    continue
                x = (self.fromWhite and [piece.x] or [7-piece.x])[0]
                y = (self.fromWhite and [7-piece.y] or [piece.y])[0]
                context.move_to(xc+x*s, yc+y*s)
                drawPiece(piece, context, s)
        
        context.fill()
    
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
            context.fill()
            #context.new_path()
    
    def drawLastMove (self, context):
        if not self.lastMove: return
    
        wh = 0.27 # Width of marker
        p0 = 0.155 # Padding on last cord
        p1 = 0.085 # Padding on current cord
        sw = 0.02 # Stroke width
        
        context.save()
        
        d0 = {-1:1-p0,1:p0}
        d1 = {-1:1-p1,1:p1}
        ms = ((1,1),(-1,1),(-1,-1),(1,-1))
        
        r = self.cord2Rect(self.lastMove.cord0)
        for m in ms:
            context.move_to(
                r[0]+(d0[m[0]]+wh*m[0])*r[2],
                r[1]+(d0[m[1]]+wh*m[1])*r[2])
            context.rel_line_to(
                0, -wh*r[2]*m[1])
            context.rel_curve_to(
                0, wh*r[2]*m[1]/2.0,
                -wh*r[2]*m[0]/2.0, wh*r[2]*m[1],
                -wh*r[2]*m[0], wh*r[2]*m[1])
            context.close_path()
        
        r = self.cord2Rect(self.lastMove.cord1)
        for m in ms:
            context.move_to(
                r[0]+d1[m[0]]*r[2],
                r[1]+d1[m[1]]*r[2])
            context.rel_line_to(
                wh*r[2]*m[0], 0)
            context.rel_curve_to(
                -wh*r[2]*m[0]/2.0, 0,
                -wh*r[2]*m[0], wh*r[2]*m[1]/2.0,
                -wh*r[2]*m[0], wh*r[2]*m[1])
            context.close_path()
        
        context.set_source_rgba(.929, .831, 0, 0.8)
        context.fill_preserve()
        context.set_source_rgba(.769, 0.627, 0, 0.5)
        context.set_line_width(sw*r[2])
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
            if not self.fromWhite:
                lvx = -1*lvx
                lvy = -1*lvy
            from math import sqrt
            l = float(sqrt(lvx**2+lvy**2))
            vx = lvx/l
            vy = lvy/l
            v1x = -vy
            v1y = vx
            r = self.cord2Rect(cords[0])
            px = r[0]+r[2]/2.0
            py = r[1]+r[2]/2.0
            ax = v1x*r[2]*aw/2
            ay = v1y*r[2]*aw/2
            context.move_to(px+ax, py+ay)
            p1x = px+(lvx-vx*ahh)*r[2]
            p1y = py+(lvy-vy*ahh)*r[2]
            context.line_to(p1x+ax, p1y+ay)
            lax = v1x*r[2]*ahw/2
            lay = v1y*r[2]*ahw/2
            context.line_to(p1x+lax, p1y+lay)
            context.line_to(px+lvx*r[2], py+lvy*r[2])
            context.line_to(p1x-lax, p1y-lay)
            context.line_to(p1x-ax, p1y-ay)
            context.line_to(px-ax, py-ay)
            context.close_path()
            
            context.set_source_rgba(*fillc)
            context.fill_preserve()
            context.set_line_join(gtk.gdk.JOIN_ROUND)
            context.set_line_width(asw*r[2])
            context.set_source_rgba(*strkc)
            context.stroke()
            context.restore()
            
        if self.greenarrow:
            drawArrow(self.greenarrow, (.54,.886,.2,0.9), (.306,.604,.024,1))
        if self.redarrow:
            drawArrow(self.redarrow, (.937,.16,.16,0.9), (.643,0,0,1))
        if self.bluearrow:
            drawArrow(self.bluearrow, (.447,.624,.812,0.9), (.204,.396,.643,1))
    
    def redraw_canvas(self, r=None):
        if self.window:
            if not r:
                alloc = self.get_allocation()
                r = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
            self.window.invalidate_rect(r, True)
            self.window.process_updates(True)

    ###############################
    #          Cord vars          #
    ###############################

    def _set_selected (self, cord):
        self._active = None
        if self._selected == cord: return
        if self._selected:
            r = rect(self.cord2Rect(self._selected))
            if cord: r = r.union(rect(self.cord2Rect(cord)))
        elif cord: r = rect(self.cord2Rect(cord))
        self._selected = cord
        self.redraw_canvas(r)
    def _get_selected (self):
        return self._selected
    selected = property(_get_selected, _set_selected)
    
    def _set_hover (self, cord):
        if self._hover == cord: return
        if self._hover:
            r = rect(self.cord2Rect(self._hover))
            if cord: r = r.union(rect(self.cord2Rect(cord)))
        elif cord: r = rect(self.cord2Rect(cord))
        self._hover = cord
        self.redraw_canvas(r)
    def _get_hover (self):
        return self._hover
    hover = property(_get_hover, _set_hover)
    
    def _set_active (self, cord):
        if self._active == cord: return
        if self._active:
            r = rect(self.cord2Rect(self._active))
            if cord: r = r.union(rect(self.cord2Rect(cord)))
        elif cord: r = rect(self.cord2Rect(cord))
        self._active = cord
        self.redraw_canvas(r)
    def _get_active (self):
        return self._active
    active = property(_get_active, _set_active)
    
    ################################
    #          Arrow vars          #
    ################################
    
    def _set_redarrow (self, cords):
        if cords == self._redarrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._redarrow: paintCords += self._redarrow
        r = rect(self.cord2Rect(paintCords[0]))
        for cord in paintCords[1:]:
            r = r.union(rect(self.cord2Rect(cord)))
        self._redarrow = cords
        idle_add(self.redraw_canvas, r)
    def _get_redarrow (self):
        return self._redarrow
    redarrow = property(_get_redarrow, _set_redarrow)
    
    def _set_greenarrow (self, cords):
        if cords == self._greenarrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._greenarrow: paintCords += self._greenarrow
        r = rect(self.cord2Rect(paintCords[0]))
        for cord in paintCords[1:]:
            r = r.union(rect(self.cord2Rect(cord)))
        self._greenarrow = cords
        idle_add(self.redraw_canvas, r)
    def _get_greenarrow (self):
        return self._greenarrow
    greenarrow = property(_get_greenarrow, _set_greenarrow)
    
    def _set_bluearrow (self, cords):
        if cords == self._bluearrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._bluearrow: paintCords += self._bluearrow
        r = rect(self.cord2Rect(paintCords[0]))
        for cord in paintCords[1:]:
            r = r.union(rect(self.cord2Rect(cord)))
        self._bluearrow = cords
        idle_add(self.redraw_canvas, r)
    def _get_bluearrow (self):
        return self._bluearrow
    bluearrow = property(_get_bluearrow, _set_bluearrow)
    
    ################################
    #          Other vars          #
    ################################
    
    def _set_fromWhite (self, fromWhite):
        self._fromWhite = fromWhite
        self.redraw_canvas()
    def _get_fromWhite (self):
        return self._fromWhite
    fromWhite = property(_get_fromWhite, _set_fromWhite)
    
    def _set_showCords (self, showCords):
        if not showCords:
            self.padding = 0
        else: self.padding = self.pad
        self._showCords = showCords
        self.redraw_canvas()
    def _get_showCords (self):
        return self._showCords
    showCords = property(_get_showCords, _set_showCords)
        
    ###########################
    #          Other          #
    ###########################
    
    def fcord2Rect (self, x, y):
        xc, yc, square, s = self.square
        x = (self.fromWhite and [x] or [7-x])[0]
        y = (self.fromWhite and [7-y] or [y])[0]
        r = (xc+x*s, yc+y*s, s)
        return r
    
    def cord2Rect (self, cord):
        xc, yc, square, s = self.square
        x = (self.fromWhite and [cord.x] or [7-cord.x])[0]
        y = (self.fromWhite and [7-cord.y] or [cord.y])[0]
        r = (xc+x*s, yc+y*s, s)
        return r
    
    def cord2Point (self, cord):
        r = self.cord2Rect(cord)
        return r[:2]

    def isLight (self, cord):
        x, y = cord.cords
        return x % 2 + y % 2 == 1
