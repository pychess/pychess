# -*- coding: UTF-8 -*-

import sys
from math import floor, ceil, pi
from time import time, sleep
from threading import Lock, RLock

import gtk, gtk.gdk, cairo
from gobject import *
import pango

from pychess.System import glock, conf, gstreamer
from pychess.System.glock import glock_connect, glock_connect_after
from pychess.System.repeat import repeat, repeat_sleep
from pychess.gfx.Pieces import drawPiece
from pychess.Utils.Piece import Piece
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import *
import preferencesDialog

def intersects (r0, r1):
    w0 = r0.width + r0.x
    h0 = r0.height + r0.y
    w1 = r1.width + r1.x
    h1 = r1.height + r1.y
    return  (w1 < r1.x or w1 > r0.x) and \
            (h1 < r1.y or h1 > r0.y) and \
            (w0 < r0.x or w0 > r1.x) and \
            (h0 < r0.y or h0 > r1.y)

def contains (r0, r1):
    w0 = r0.width + r0.x
    h0 = r0.height + r0.y
    w1 = r1.width + r1.x
    h1 = r1.height + r1.y
    return r0.x <= r1.x and w0 >= w1 and \
           r0.y <= r1.y and h0 >= h1

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

def matrixAround (rotatedMatrix, anchorX, anchorY):
    co = rotatedMatrix[0]
    si = rotatedMatrix[1]
    aysi = anchorY*si
    axsi = anchorX*si
    ayco = anchorY*(1-co)
    axco = anchorX*(1-co)
    matrix = cairo.Matrix(co, si, -si, co, axco+aysi, ayco-axsi)
    invmatrix = cairo.Matrix(co, -si, si, co, axco-aysi, ayco+axsi)
    return matrix, invmatrix

ANIMATION_TIME = 0.5

# If this is true, the board is scaled so that everything fits inside the window
# even if the board is rotated 45 degrees
SCALE_ROTATED_BOARD = False

CORD_PADDING = 1.5

class BoardView (gtk.DrawingArea):
    
    __gsignals__ = {
        'shown_changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int,))
    }
    
    def __init__(self, gamemodel=None):
        gtk.DrawingArea.__init__(self)
        
        if gamemodel == None:
            gamemodel = GameModel()
        self.model = gamemodel
        glock_connect(self.model, "game_started", self.game_started)
        glock_connect_after(self.model, "game_changed", self.game_changed)
        glock_connect_after(self.model, "moves_undoing", self.moves_undoing)
        glock_connect_after(self.model, "game_loading", self.game_loading)
        glock_connect_after(self.model, "game_loaded", self.game_loaded)
        glock_connect_after(self.model, "game_ended", self.game_ended)
        
        self.connect("expose_event", self.expose)
        self.connect_after("realize", self.on_realized)
        conf.notify_add("showCords", self.on_show_cords)
        conf.notify_add("faceToFace", self.on_face_to_face)
        self.set_size_request(350,350)
        
        self.animationStart = time()
        self.lastShown = None
        self.deadlist = []
        
        self.autoUpdateShown = True
        
        self.padding = 0 # Set to self.pad when setcords is active
        self.square = 0, 0, 8, 1 # An object global variable with the current
                                 # board size
        self.pad = 0.13 # Padding applied only when setcords is active
        
        self._selected = None
        self._hover = None
        self._active = None
        self._redarrow = None
        self._greenarrow = None
        self._bluearrow = None
        
        self._shown = self.model.ply
        self._showCords = False
        self.showCords = conf.get("showCords", False)
        self._showEnpassant = False
        self.lastMove = None
        self.matrix = cairo.Matrix()
        self.matrixPi = cairo.Matrix.init_rotate(pi)
        self.cordMatricesState = (0, 0)
        self._rotation = 0
        
        self.drawcount = 0
        self.drawtime = 0
        
        self.gotStarted = False
        self.animationLock = RLock()
        self.rotationLock = Lock()
    
    def game_started (self, model):
        if conf.get("noAnimation", False):
            self.gotStarted = True
            self.redraw_canvas()
        else:
            if model.moves:
                self.lastMove = model.moves[-1]
            self.animationLock.acquire()
            try:
                for row in self.model.boards[-1].data:
                    for piece in row:
                        if piece:
                            piece.opacity = 0
            finally:
                self.animationLock.release()
            self.gotStarted = True
            self.startAnimation()
    
    def game_changed (self, model):
        # Play sounds
        if self.model.players and self.model.status != WAITING_TO_START:
            move = model.moves[-1]
            if move.flag == ENPASSANT or model.boards[-2][move.cord1] != None:
                sound = "aPlayerCaptures"
            else: sound = "aPlayerMoves"
            
            if model.boards[-1].board.isChecked():
                sound = "aPlayerChecks"
            
            if model.players[0].__type__ == REMOTE and \
                    model.players[1].__type__ == REMOTE:
                sound = "observedMoves"
            
            preferencesDialog.SoundTab.playAction(sound)
        
        # Auto updating self.shown can be disabled. Useful for loading games.
        # If we are not at the latest game we are probably browsing the history,
        # and we won't like auto updating.
        if self.autoUpdateShown and self.shown+1 >= model.ply:
            self.shown = model.ply
            
            # Rotate board
            if conf.get("autoRotate", True):
                if self.model.players and self.model.curplayer.__type__ == LOCAL:
                    self.rotation = self.model.boards[-1].color * pi
    
    def moves_undoing (self, model, moves):
        self.shown = model.ply-moves
    
    def game_loading (self, model, uri):
        self.autoUpdateShown = False
    
    def game_loaded (self, model, uri):
        self.autoUpdateShown = True
        self._shown = model.ply
        self.emit("shown_changed", self.shown)
    
    def game_ended (self, model, reason):
        self.redraw_canvas()
        
        if self.model.players:
            sound = False
            
            if model.status == DRAW:
                sound = "gameIsDrawn"
            elif model.status == WHITEWON:
                if model.players[0].__type__ == LOCAL:
                    sound = "gameIsWon"
                elif model.players[1].__type__ == LOCAL:
                    sound = "gameIsLost"
            elif model.status == BLACKWON:
                if model.players[1].__type__ == LOCAL:
                     sound = "gameIsWon"
                elif model.players[0].__type__ == LOCAL:
                    sound = "gameIsLost"
            elif model.status in (ABORTED, KILLED):
                sound = "gameIsLost"
            
            if model.status in (DRAW, WHITEWON, BLACKWON, KILLED, ABORTED) and \
                    model.players[0].__type__ == REMOTE and \
                    model.players[1].__type__ == REMOTE:
                sound = "oberservedEnds"
            
            # This should never be false, unless status is set to UNKNOWN or
            # something strange
            if sound:
                preferencesDialog.SoundTab.playAction(sound)
    
    def on_show_cords (self, *args):
        self.showCords = conf.get("showCords", False)
    
    def on_face_to_face (self, *args):
        self.redraw_canvas()
    
    ###############################
    #          Animation          #
    ###############################
    
    def _get_shown(self):
        return self._shown
    
    def _set_shown(self, shown):
        
        # We don't do anything if we are already showing the right ply
        if shown == self._shown:
            return
        
        # This would cause IndexErrors later
        if not self.model.lowply <= shown <= self.model.ply:
            return
        
        # If there is only one board, we don't do any animation, but simply
        # redraw the entire board. Same if we are at first draw.
        if len(self.model.boards) == 1 or self.shown < self.model.lowply:
            self._shown = shown
            if shown > self.model.lowply:
                self.lastMove = self.model.getMoveAtPly(shown-1)
            self.emit("shown_changed", self.shown)
            self.redraw_canvas()
            return
        
        
        step = shown > self.shown and 1 or -1
        
        self.animationLock.acquire()
        try:
            deadset = set()
            for i in xrange(self.shown, shown, step):
                board = self.model.getBoardAtPly(i)
                board1 = self.model.getBoardAtPly(i + step)
                if step == 1:
                    move = self.model.getMoveAtPly(i)
                    moved, new, dead = board.simulateMove(board1, move)
                else:
                    move = self.model.getMoveAtPly(i-1)
                    moved, new, dead = board.simulateUnmove(board1, move)
                
                for piece, cord0 in moved:
                    # Test if the piece already has a realcoord (has been dragged)
                    if not piece.x:
                        # We don't want newly restored pieces to flew from their
                        # deadspot to their old position, as it doesn't work
                        # vice versa  
                        if piece.opacity == 1:
                            piece.x = cord0.x
                            piece.y = cord0.y
                
                for piece in dead:
                    deadset.add(piece)
                    # Reset the location of the piece to avoid a small visual
                    # jump, when it is at some other time waken to life.
                    piece.x = None
                    piece.y = None
                
                for piece in new:
                    piece.opacity = 0
        
        finally:
            self.animationLock.release()
        
        self.deadlist = []
        for y, row in enumerate(self.model.getBoardAtPly(self.shown).data):
            for x, piece in enumerate(row):
                if piece in deadset:
                    self.deadlist.append((piece,x,y))
        
        self._shown = shown
        self.emit("shown_changed", self.shown)
        
        self.animationStart = time()
        if self.lastMove:
            paintBox = self.cord2RectRelative(self.lastMove.cord0)
            paintBox = join(paintBox, self.cord2RectRelative(self.lastMove.cord1))
            self.lastMove = None
            self.redraw_canvas(rect(paintBox))
        if self.shown > self.model.lowply:
            self.lastMove = self.model.getMoveAtPly(self.shown-1)
        else:
            self.lastMove = None
       
        self.runAnimation(redrawMisc=True)
        repeat(self.runAnimation)
        
    shown = property(_get_shown, _set_shown)
    
    def runAnimation (self, redrawMisc=False):
        
        """ The animationsystem in pychess is very loosely inspired by the one of chessmonk. The idea is, that every piece has a place in an array (the board.data one) for where to be drawn. If a piece is to be animated, it can set its x and y properties, to some cord (or part cord like 0.42 for 42% right to file 0). Each time runAnimation is run, it will set those x and y properties a little closer to the location in the array. When it has reached its final location, x and y will be set to None.
        _set_shown, which starts the animation, also sets a timestamp for the acceleration to work properply. """
        
        self.animationLock.acquire()
        try:
            paintBox = None
            
            mod = min(1, (time()-self.animationStart)/ANIMATION_TIME)
            board = self.model.getBoardAtPly(self.shown)
            
            for y, row in enumerate(board.data):
                for x, piece in enumerate(row):
                    if not piece: continue
                    
                    if piece.x != None:
                        if not conf.get("noAnimation", False):
                            if piece.piece == KNIGHT:
                                #print mod, x, piece.x
                                newx = piece.x + (x-piece.x)*mod**(1.5)
                                newy = piece.y + (y-piece.y)*mod
                            else:
                                newx = piece.x + (x-piece.x)*mod
                                newy = piece.y + (y-piece.y)*mod
                        else:
                            newx, newy = x, y
                        
                        paintBox = join(paintBox, self.cord2RectRelative(piece.x, piece.y))
                        paintBox = join(paintBox, self.cord2RectRelative(newx, newy))
                        
                        if (newx <= x <= piece.x or newx >= x >= piece.x) and \
                           (newy <= y <= piece.y or newy >= y >= piece.y) or \
                           abs(newx-x) < 0.005 and abs(newy-y) < 0.005:
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
                        
                        if paintBox:
                            paintBox = join(paintBox,self.cord2RectRelative(px, py))
                        else: paintBox = self.cord2RectRelative(px, py)
                        
                        if not conf.get("noAnimation", False):
                            newOp = piece.opacity + (1-piece.opacity)*mod
                        else:
                            newOp = 1
                        
                        if newOp >= 1 >= piece.opacity or abs(1-newOp) < 0.005:
                            piece.opacity = 1
                        else: piece.opacity = newOp
            
            for i, (piece, x, y) in enumerate(self.deadlist):
                if not paintBox:
                    paintBox = self.cord2RectRelative(x, y)
                else: paintBox = join(paintBox, self.cord2RectRelative(x, y))
                
                if not conf.get("noAnimation", False):
                    newOp = piece.opacity + (0-piece.opacity)*mod
                else:
                    newOp = 0
                
                if newOp <= 0 <= piece.opacity or abs(0-newOp) < 0.005:
                    del self.deadlist[i]
                else: piece.opacity = newOp
        
        finally:
            self.animationLock.release()
        
        if redrawMisc:
            for cord in (self.selected, self.hover, self.active):
                if cord:
                    paintBox = join(paintBox, self.cord2RectRelative(cord))
            for arrow in (self.redarrow, self.greenarrow, self.bluearrow):
                if arrow:
                    paintBox = join(paintBox, self.cord2RectRelative(arrow[0]))
                    paintBox = join(paintBox, self.cord2RectRelative(arrow[1]))
            if self.lastMove:
                paintBox = join(paintBox,
                                self.cord2RectRelative(self.lastMove.cord0))
                paintBox = join(paintBox,
                                self.cord2RectRelative(self.lastMove.cord1))
        
        if paintBox:
            self.redraw_canvas(rect(paintBox))
        
        return paintBox and True or False
    
    def startAnimation (self):
        self.animationStart = time()
        self.runAnimation(redrawMisc = True)
        repeat(self.runAnimation)
    
    #############################
    #          Drawing          #
    #############################
    
    def on_realized (self, widget):
        p = (1-self.padding)
        alloc = self.get_allocation()
        square = float(min(alloc.width, alloc.height))*p
        xc = alloc.width/2. - square/2
        yc = alloc.height/2. - square/2
        s = square/8
        self.square = (xc, yc, square, s)
    
    def expose(self, widget, event):
        context = widget.window.cairo_create()
        #r = (event.area.x, event.area.y, event.area.width, event.area.height)
        #context.rectangle(r[0]-.5, r[1]-.5, r[2]+1, r[3]+1)
        #context.clip()
        
        if False:
            import profile
            profile.runctx("self.draw(context, event.area)", locals(), globals(), "/tmp/pychessprofile")
            from pstats import Stats
            s = Stats("/tmp/pychessprofile")
            s.sort_stats('cumulative')
            s.print_stats()
        else:
            self.drawcount += 1
            start = time()
            self.animationLock.acquire()
            self.draw(context, event.area)
            self.animationLock.release()
            self.drawtime += time() - start
            #if self.drawcount % 100 == 0:
            #    print "Average FPS: %0.3f - %d / %d" % \
            #      (self.drawcount/self.drawtime, self.drawcount, self.drawtime)
            
        return False
    
    ############################################################################
    #                            drawing functions                             #
    ############################################################################
    
    ###############################
    #        redraw_canvas        #
    ###############################
    
    def redraw_canvas(self, r=None, queue=False):
        if self.window:
            glock.acquire()
            try:
                if self.window:
                    if not r:
                        alloc = self.get_allocation()
                        r = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
                    assert type(r[2]) == int
                    if queue:
                        self.queue_draw_area(r.x, r.y, r.width, r.height)
                    else:
                        self.window.invalidate_rect(r, True)
                        self.window.process_updates(True)
            finally:
                glock.release()
    
    ###############################
    #            draw             #
    ###############################
    
    def draw (self, context, r):
        #context.set_antialias (cairo.ANTIALIAS_NONE)
        
        if self.shown < self.model.lowply:
            print "exiting cause to lowlpy", self.shown, self.model.lowply
            return
        
        alloc = self.get_allocation()
        
        self.matrix, self.invmatrix = matrixAround(
                self.matrix, alloc.width/2., alloc.height/2.)
        cos_, sin_ = self.matrix[0], self.matrix[1]
        context.transform(self.matrix)
        
        square = float(min(alloc.width, alloc.height))*(1-self.padding)
        if SCALE_ROTATED_BOARD:
            square /= abs(cos_)+abs(sin_)
        xc = alloc.width/2. - square/2
        yc = alloc.height/2. - square/2
        s = square/8
        self.square = (xc, yc, square, s)
        
        self.drawBoard (context, r)
        
        if min(alloc.width, alloc.height) > 32:
            self.drawCords (context, r)
        
        if self.gotStarted:
            self.drawSpecial (context, r)
            self.drawEnpassant (context, r)
            self.drawArrows (context)
            self.animationLock.acquire()
            try:
                self.drawPieces (context, r)
            finally:
                self.animationLock.release()
            self.drawLastMove (context, r)
        
        if self.model.status == KILLED:
            self.drawCross (context, r)
        
        # Unselect to mark redrawn areas - for debugging purposes
        #context.transform(self.invmatrix)
        #context.rectangle(r.x,r.y,r.width,r.height)
        #dc = self.drawcount*50
        #dc = dc % 1536
        #c = dc % 256 / 255.
        #if dc < 256:
        #    context.set_source_rgb(1,c,0)
        #elif dc < 512:
        #    context.set_source_rgb(1-c,1,0)
        #elif dc < 768:
        #    context.set_source_rgb(0,1,c)
        #elif dc < 1024:
        #    context.set_source_rgb(0,1-c,1)
        #elif dc < 1280:
        #    context.set_source_rgb(c,0,1)
        #elif dc < 1536:
        #    context.set_source_rgb(1,0,1-c)
        #context.stroke()
    
    ###############################
    #          drawCords          #
    ###############################
    
    def drawCords (self, context, r):
        thickness = 0.01
        signsize = 0.04
        
        if not self.showCords: return
        
        xc, yc, square, s = self.square
        
        if contains(rect((xc, yc, square)), r): return
        
        t = thickness*square
        ss = signsize*square
        
        context.rectangle(xc-t*1.5,yc-t*1.5,square+t*3,square+t*3)
        context.set_source_color(self.get_style().dark[gtk.STATE_NORMAL])
        context.set_line_width(t)
        context.set_line_join(gtk.gdk.JOIN_ROUND)
        context.stroke()
        
        pangoScale = float(pango.SCALE)
        
        def paint (inv):
            for n in xrange(8):
                rank = inv and n+1 or 8-n
                layout = self.create_pango_layout("%d" % rank)
                layout.set_font_description(
                        pango.FontDescription("bold %d" % ss))
                
                w = layout.get_extents()[1][2]/pangoScale
                h = layout.get_extents()[0][3]/pangoScale
                
                # Draw left side
                context.move_to(xc-t*2.5-w, s*n+yc+h/2+t)
                context.show_layout(layout)
                
                # Draw right side
                #context.move_to(xc+square+t*2.5, s*n+yc+h/2+t)
                #context.show_layout(layout)
                
                file = inv and 8-n or n+1
                layout = self.create_pango_layout(chr(file+ord("A")-1))
                layout.set_font_description(
                        pango.FontDescription("bold %d" % ss))
                
                w = layout.get_pixel_size()[0]
                h = layout.get_pixel_size()[1]
                y = layout.get_extents()[1][1]/pangoScale
                
                # Draw top
                #context.move_to(xc+s*n+s/2.-w/2., yc-h-t*1.5)
                #context.show_layout(layout)
                
                # Draw bottom
                context.move_to(xc+s*n+s/2.-w/2., yc+square+t*1.5+abs(y))
                context.show_layout(layout)
        
        matrix, invmatrix = matrixAround(
                self.matrixPi, xc+square/2., yc+square/2.)
        paint(False)
        context.transform(matrix)
        paint(True)
        context.transform(invmatrix)
    
    ###############################
    #          drawBoard          #
    ###############################
    
    def drawBoard(self, context, r):
        xc, yc, square, s = self.square
        for x in xrange(8):
            for y in xrange(8):
                if x % 2 + y % 2 == 1:
                    bounding = self.cord2RectRelative((xc+x*s,yc+y*s,s))
                    if intersects(rect(bounding), r):
                        context.rectangle(xc+x*s,yc+y*s,s,s)
        
        context.set_source_color(self.get_style().dark[gtk.STATE_NORMAL])
        context.fill()
    
    ###############################
    #         drawPieces          #
    ###############################
    
    def getCordMatrices (self, x, y, inv=False):
        xc, yc, square, s = self.square
        square_, rot_ = self.cordMatricesState
        if square != self.square or rot_ != self.rotation:
            self.cordMatrices = [None] * 64
            self.cordMatricesState = (self.square, self.rotation)
        c = x * 8 + y
        if type(c) == int and self.cordMatrices[c]:
            matrices = self.cordMatrices[c]
        else:
            cx, cy = self.cord2Point(x,y)
            matrices = matrixAround(self.matrix, cx+s/2., cy+s/2.)
            matrices += (cx, cy)
            if type(c) == int:
                self.cordMatrices[c] = matrices
        return matrices
    
    def __drawPiece(self, context, piece, x, y):
        xc, yc, square, s = self.square
        
        if not conf.get("faceToFace", False):
            matrix, invmatrix, cx, cy = self.getCordMatrices(x, y)
        else:
            cx, cy = self.cord2Point(x,y)
            if piece.color == BLACK:
                matrix, invmatrix = matrixAround((-1,0), cx+s/2., cy+s/2.)
            else:
                matrix = invmatrix = cairo.Matrix(1,0,0,1,0,0)
        
        context.transform(invmatrix)
        drawPiece(  piece, context,
                    cx+CORD_PADDING, cy+CORD_PADDING,
                    s-CORD_PADDING*2)
        context.transform(matrix)
    
    def drawPieces(self, context, r):
        pieces = self.model.getBoardAtPly(self.shown)
        xc, yc, square, s = self.square
        
        parseC = lambda c: (c.red/65535., c.green/65535., c.blue/65535.)
        fgN = parseC(self.get_style().fg[gtk.STATE_NORMAL])
        fgS = fgN
        fgA = parseC(self.get_style().fg[gtk.STATE_ACTIVE])
        fgP = parseC(self.get_style().fg[gtk.STATE_PRELIGHT])
        
        # As default we use normal foreground for selected cords, as it looks
        # less confusing. However for some themes, the normal foreground is so
        # similar to the selected background, that we have to use the selected
        # foreground.
        bgSl = parseC(self.get_style().bg[gtk.STATE_SELECTED])
        bgSd = parseC(self.get_style().dark[gtk.STATE_SELECTED])
        if min((fgN[0]-bgSl[0])**2+(fgN[1]-bgSl[1])**2+(fgN[2]-bgSl[2])**2,
               (fgN[0]-bgSd[0])**2+(fgN[1]-bgSd[1])**2+(fgN[2]-bgSd[2])**2) < 0.2:
            fgS = parseC(self.get_style().fg[gtk.STATE_SELECTED])
        
        # Draw dying pieces (Found in self.deadlist)
        for piece, x, y in self.deadlist:
            context.set_source_rgba(fgN[0],fgN[1],fgN[2],piece.opacity)
            self.__drawPiece(context, piece, x, y)
        
        # Draw pieces reincarnating (With opacity < 1)
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
                if not piece or piece.opacity == 1:
                    continue
                if piece.x:
                    x, y = piece.x, piece.y
                context.set_source_rgba(fgN[0],fgN[1],fgN[2],piece.opacity)
                self.__drawPiece(context, piece, x, y)
        
        # Draw standing pieces (Only those who intersect drawn area)
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
                if not piece or piece.x != None or piece.opacity < 1:
                    continue
                if not intersects(rect(self.cord2RectRelative(x,y)), r):
                    continue
                
                if Cord(x,y) == self.selected:
                    context.set_source_rgb(*fgS)
                elif Cord(x,y) == self.active:
                    context.set_source_rgb(*fgA)
                elif Cord(x,y) == self.hover:
                    context.set_source_rgb(*fgP)
                else: context.set_source_rgb(*fgN)
                
                self.__drawPiece(context, piece, x, y)
        
        context.set_source_rgb(*fgP)
        
        # Draw moving or dragged pieces (Those with piece.x and piece.y != None)
        for y, row in enumerate(pieces.data):
            for x, piece in enumerate(row):
                if not piece or piece.x == None or piece.opacity < 1:
                    continue
                self.__drawPiece(context, piece, piece.x, piece.y)
    
    ###############################
    #         drawSpecial         #
    ###############################
    
    def drawSpecial (self, context, redrawn):
        used = []
        for cord, state in ((self.active, gtk.STATE_ACTIVE),
                            (self.selected, gtk.STATE_SELECTED),
                            (self.hover, gtk.STATE_PRELIGHT)):
            if not cord: continue
            if cord in used: continue
            # Ensure that same cord, if having multiple "tasks", doesn't get
            # painted more than once
            used.append(cord)
            
            bounding = self.cord2RectRelative(cord)
            if not intersects(rect(bounding), redrawn): continue
            
            xc, yc, square, s = self.square
            x, y = self.cord2Point(cord)
            context.rectangle(x, y, s, s)
            if self.isLight(cord):
                style = self.get_style().bg
            else: style = self.get_style().dark
            context.set_source_color(style[state])
            context.fill()
    
    ###############################
    #        drawLastMove         #
    ###############################
    
    def drawLastMove (self, context, redrawn):
        if not self.lastMove: return
        ply = self.shown-1
        if ply < self.model.lowply: return
        capture = self.model.getBoardAtPly(ply)[self.lastMove.cord1]
        
        wh = 0.27 # Width of marker
        p0 = 0.155 # Padding on last cord
        p1 = 0.085 # Padding on current cord
        sw = 0.02 # Stroke width
        
        xc, yc, square, s = self.square
        
        context.save()
        context.set_line_width(sw*s)
        
        d0 = {-1:1-p0,1:p0}
        d1 = {-1:1-p1,1:p1}
        ms = ((1,1),(-1,1),(-1,-1),(1,-1))
        
        light_yellow = (.929, .831, 0, 0.8)
        dark_yellow  = (.769, .627, 0, 0.5)
        light_orange = (.961, .475, 0, 0.8)
        dark_orange  = (.808, .361, 0, 0.5)
        
        
        rel = self.cord2RectRelative(self.lastMove.cord0)
        if intersects(rect(rel), redrawn):
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
            
            context.set_source_rgba(*light_yellow)
            context.fill_preserve()
            context.set_source_rgba(*dark_yellow)
            context.stroke()
            
        rel = self.cord2RectRelative(self.lastMove.cord1)
        if intersects(rect(rel), redrawn):
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
            
            if capture:
                context.set_source_rgba(*light_orange)
                context.fill_preserve()
                context.set_source_rgba(*dark_orange)
                context.stroke()
            else:
                context.set_source_rgba(*light_yellow)
                context.fill_preserve()
                context.set_source_rgba(*dark_yellow)
                context.stroke()
    
    ###############################
    #         drawArrows          #
    ###############################
    
    def __drawArrow (self, context, cords, aw, ahw, ahh, asw, fillc, strkc):
        context.save()
        
        lvx = cords[1].x-cords[0].x
        lvy = cords[0].y-cords[1].y
        l = float((lvx**2+lvy**2)**.5)
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
    
    def drawArrows (self, context):
        # TODO: Only redraw when intersecting with the redrawn area
        
        aw = 0.3 # Arrow width
        ahw = 0.72 # Arrow head width
        ahh = 0.64 # Arrow head height
        asw = 0.08 # Arrow stroke width
        
        if self.bluearrow:
            self.__drawArrow(context, self.bluearrow, aw, ahw, ahh, asw,
                             (.447,.624,.812,0.9), (.204,.396,.643,1))
        
        if self.shown != self.model.ply:
            return
        
        if self.greenarrow:
            self.__drawArrow(context, self.greenarrow, aw, ahw, ahh, asw,
                             (.54,.886,.2,0.9), (.306,.604,.024,1))
        
        if self.redarrow:
            self.__drawArrow(context, self.redarrow, aw, ahw, ahh, asw,
                             (.937,.16,.16,0.9), (.643,0,0,1))
    
    ###############################
    #        drawEnpassant        #
    ###############################
    
    def drawEnpassant (self, context, redrawn):
        if not self.showEnpassant: return
        enpassant = self.model.boards[-1].enpassant
        if not enpassant: return
        
        context.set_source_rgb(0, 0, 0)
        xc, yc, square, s = self.square
        x, y = self.cord2Point(enpassant)
        if not intersects(rect((x, y, s, s)), redrawn): return
        
        x, y = self.cord2Point(enpassant)
        cr = context
        cr.set_font_size(s/2.)
        fascent, fdescent, fheight, fxadvance, fyadvance = cr.font_extents()
        chars = "en"
        xbearing, ybearing, width, height, xadvance, yadvance = \
                cr.text_extents(chars)
        cr.move_to(x + s / 2. - xbearing - width / 2.-1,
                   s / 2. + y - fdescent + fheight / 2.)
        cr.show_text(chars)
    
    ###############################
    #          drawCross          #
    ###############################
    
    def drawCross (self, context, redrawn):
        xc, yc, square, s = self.square
        
        context.move_to(xc, yc)
        context.rel_line_to(square, square)
        context.move_to(xc+square, yc)
        context.rel_line_to(-square, square)
        
        context.set_line_cap(cairo.LINE_CAP_SQUARE)
        context.set_source_rgba(0,0,0,0.65)
        context.set_line_width(s)
        context.stroke_preserve()
        
        context.set_source_rgba(1,0,0,0.8)
        context.set_line_width(s/2.)
        context.stroke()
    
    ############################################################################
    #                                Attributes                                #
    ############################################################################
    
    ###############################
    #          Cord vars          #
    ###############################

    def _set_selected (self, cord):
        self._active = None
        if self._selected == cord: return
        if self._selected:
            r = rect(self.cord2RectRelative(self._selected))
            if cord: r = r.union(rect(self.cord2RectRelative(cord)))
        elif cord: r = rect(self.cord2RectRelative(cord))
        self._selected = cord
        self.redraw_canvas(r)
    def _get_selected (self):
        return self._selected
    selected = property(_get_selected, _set_selected)
    
    def _set_hover (self, cord):
        if self._hover == cord: return
        if self._hover:
            r = rect(self.cord2RectRelative(self._hover))
            if cord: r = r.union(rect(self.cord2RectRelative(cord)))
        elif cord: r = rect(self.cord2RectRelative(cord))
        self._hover = cord
        self.redraw_canvas(r)
    def _get_hover (self):
        return self._hover
    hover = property(_get_hover, _set_hover)
    
    def _set_active (self, cord):
        if self._active == cord: return
        if self._active:
            r = rect(self.cord2RectRelative(self._active))
            if cord: r = r.union(rect(self.cord2RectRelative(cord)))
        elif cord: r = rect(self.cord2RectRelative(cord))
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
        r = rect(self.cord2RectRelative(paintCords[0]))
        for cord in paintCords[1:]:
            r = r.union(rect(self.cord2RectRelative(cord)))
        self._redarrow = cords
        self.redraw_canvas(r)
    def _get_redarrow (self):
        return self._redarrow
    redarrow = property(_get_redarrow, _set_redarrow)
    
    def _set_greenarrow (self, cords):
        if cords == self._greenarrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._greenarrow: paintCords += self._greenarrow
        r = rect(self.cord2RectRelative(paintCords[0]))
        for cord in paintCords[1:]:
            r = r.union(rect(self.cord2RectRelative(cord)))
        self._greenarrow = cords
        self.redraw_canvas(r)
    def _get_greenarrow (self):
        return self._greenarrow
    greenarrow = property(_get_greenarrow, _set_greenarrow)
    
    def _set_bluearrow (self, cords):
        if cords == self._bluearrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._bluearrow: paintCords += self._bluearrow
        r = rect(self.cord2RectRelative(paintCords[0]))
        for cord in paintCords[1:]:
            r = r.union(rect(self.cord2RectRelative(cord)))
        self._bluearrow = cords
        self.redraw_canvas(r)
    def _get_bluearrow (self):
        return self._bluearrow
    bluearrow = property(_get_bluearrow, _set_bluearrow)
    
    ################################
    #          Other vars          #
    ################################
    
    def _set_rotation (self, radians):
        if not conf.get("fullAnimation", True):
            glock.acquire()
            try:
                self._rotation = radians
                self.nextRotation = radians
                self.matrix = cairo.Matrix.init_rotate(radians)
                self.redraw_canvas()
            finally:
                glock.release()
        else:
            if hasattr(self, "nextRotation") and \
                    self.nextRotation != self.rotation:
                return
            self.nextRotation = radians
            oldr = self.rotation
            start = time()
            def callback ():
                glock.acquire()
                try:
                    amount = (time()-start)/ANIMATION_TIME
                    if amount > 1:
                        amount = 1
                        next = False
                    else: next = True
                    self._rotation = new = oldr + amount*(radians-oldr)
                    self.matrix = cairo.Matrix.init_rotate(new)
                    self.redraw_canvas()
                finally:
                    glock.release()
                return next
            repeat(callback)
    
    def _get_rotation (self):
        return self._rotation
    rotation = property(_get_rotation, _set_rotation)
    
    def _set_showCords (self, showCords):
        if not showCords:
            self.padding = 0
        else: self.padding = self.pad
        self._showCords = showCords
        self.redraw_canvas()
    def _get_showCords (self):
        return self._showCords
    showCords = property(_get_showCords, _set_showCords)
    
    def _set_showEnpassant (self, showEnpassant):
        if self._showEnpassant == showEnpassant: return
        if self.model:
            enpascord = self.model.boards[-1].enpassant
            if enpascord:
                r = rect(self.cord2RectRelative(enpascord))
                self.redraw_canvas(r)
        self._showEnpassant = showEnpassant
    def _get_showEnpassant (self):
        return self._showEnpassant
    showEnpassant = property(_get_showEnpassant, _set_showEnpassant)
    
    ###########################
    #          Other          #
    ###########################
    
    def cord2Rect (self, cord, y=None):
        if y == None:
            x, y = cord.x, cord.y
        else: x = cord
        xc, yc, square, s = self.square
        r = (xc+x*s, yc+(7-y)*s, s)
        return r
    
    def cord2Point (self, cord, y=None):
        r = self.cord2Rect(cord, y)
        return r[:2]
    
    def cord2RectRelative (self, cord, y=None):
        """ Like cord2Rect, but gives you bounding rect in case board is beeing
            Rotated """
        if type(cord) == tuple:
            cx, cy, s = cord
        else:
            cx, cy, s = self.cord2Rect(cord, y)
        x0, y0 = self.matrix.transform_point(cx, cy)
        x1, y1 = self.matrix.transform_point(cx+s, cy)
        x2, y2 = self.matrix.transform_point(cx, cy+s)
        x3, y3 = self.matrix.transform_point(cx+s, cy+s)
        x = min(x0, x1, x2, x3)
        y = min(y0, y1, y2, y3)
        s = max(y0, y1, y2, y3) - y
        return (x, y, s)
    
    def isLight (self, cord):
        x, y = cord.cords
        return x % 2 + y % 2 == 1
    
    def runWhenReady (self, func, *args):
        """ As some pieces of pychess are quite eager to set the attributes of
        BoardView, we can't always be sure, that BoardView has been painted once
        before, and therefore self.sqaure has been set.
        This might be doable in a smarter way... """
        def do2():
            if not self.square:
                sleep(0.01)
                return True
            func(*args)
        repeat(do2)
    
    def showFirst (self):
        self.shown = self.model.lowply
    
    def showPrevious (self):
        if self.shown > self.model.lowply:
            self.shown -= 1
    
    def showNext (self):
        if self.shown < self.model.ply:
            self.shown += 1
            
    def showLast (self):
        self.shown = self.model.ply
