# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from math import floor, ceil, pi
from time import time
from threading import RLock # , Lock , currentThread

import cairo
from gi.repository import Gtk, Gdk, GLib, GObject, Pango, PangoCairo
#from gi.repository import Gdk
#from gi.repository import GLib
#from gi.repository import GObject
#from gi.repository import Pango
#from gi.repository import PangoCairo
#
from pychess.System import conf
from pychess.System.idle_add import idle_add
from pychess.gfx import Pieces
from pychess.Utils.Cord import Cord
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import ASEAN_VARIANTS, DROP_VARIANTS, WAITING_TO_START, REMOTE, \
                                LOCAL, DRAW, WHITEWON, BLACKWON, ABORTED, KILLED, DROP, \
                                KING_CASTLE, QUEEN_CASTLE, WILDCASTLESHUFFLECHESS, \
                                WILDCASTLECHESS, PAWN, KNIGHT, SITTUYINCHESS, BLACK
from pychess.Variants.blindfold import BlindfoldBoard, HiddenPawnsBoard, \
                                       HiddenPiecesBoard, AllWhiteBoard
from . import preferencesDialog

#from pychess.System.Log import log


def intersects(r_zero, r_one):
    """ Takes two square and determines if they have an Intersection
        Returns a boolean
    """
    w_zero = r_zero.width + r_zero.x
    h_zero = r_zero.height + r_zero.y
    w_one = r_one.width + r_one.x
    h_one = r_one.height + r_one.y
    return  (w_one < r_one.x or w_one > r_zero.x) and \
            (h_one < r_one.y or h_one > r_zero.y) and \
            (w_zero < r_zero.x or w_zero > r_one.x) and \
            (h_zero < r_zero.y or h_zero > r_one.y)

def contains(r_zero, r_one):
    w_zero = r_zero.width + r_zero.x
    h_zero = r_zero.height + r_zero.y
    w_one = r_one.width + r_one.x
    h_one = r_one.height + r_one.y
    return r_zero.x <= r_one.x and w_zero >= w_one and \
           r_zero.y <= r_one.y and h_zero >= h_one

def union(r_zero, r_one):
    x_min = min(r_zero.x, r_one.x)
    y_min = min(r_zero.y, r_one.y)
    w_max = max(r_zero.x+r_zero.width, r_one.x+r_one.width) - x_min
    h_max = max(r_zero.y+r_zero.height, r_one.y+r_one.height) - y_min
    rct = Gdk.Rectangle()
    rct.x, rct.y, rct.width, rct.height = (x_min, y_min, w_max, h_max)
    return rct

def join(r_zero, r_one):
    """ Take (x, y, w, [h]) squares """

    if not r_zero: return r_one
    if not r_one: return r_zero
    if not r_zero and not r_one: return None

    if len(r_zero) == 3:
        r_zero = (r_zero[0], r_zero[1], r_zero[2], r_zero[2])
    if len(r_one) == 3:
        r_one = (r_one[0], r_one[1], r_one[2], r_one[2])

    x_one = min(r_zero[0], r_one[0])
    x_two = max(r_zero[0]+r_zero[2], r_one[0]+r_one[2])
    y_one = min(r_zero[1], r_one[1])
    y_two = max(r_zero[1]+r_zero[3], r_one[1]+r_one[3])

    return (x_one, y_one, x_two - x_one, y_two - y_one)

def rect(r):
    x, y = [int(floor(v)) for v in r[:2]]
    w = int(ceil(r[2]))
    if len(r) == 4:
        h = int(ceil(r[3]))
    else: h = w
    rct = Gdk.Rectangle()
    rct.x, rct.y, rct.width, rct.height = (x, y, w, h)
    return rct

def matrixAround(rotatedMatrix, anchorX, anchorY):
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

class BoardView(Gtk.DrawingArea):

    __gsignals__ = {
        'shown_changed' : (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    def __init__(self, gamemodel=None, preview=False, setup_position=False):
        GObject.GObject.__init__(self)

        if gamemodel == None:
            gamemodel = GameModel()
        self.model = gamemodel
        self.allwhite = self.model.variant == AllWhiteBoard
        self.asean = self.model.variant.variant in ASEAN_VARIANTS
        self.preview = preview
        self.setup_position = setup_position
        self.shownVariationIdx = 0 # the main variation is the first in gamemodel.variations list

        self.model.connect("game_started", self.game_started)
        self.model.connect("game_started", self.game_started_after)
        self.model.connect("game_changed", self.game_changed)
        self.model.connect("moves_undoing", self.moves_undoing)
        self.model.connect("game_loading", self.game_loading)
        self.model.connect("game_loaded", self.game_loaded)
        self.model.connect("game_ended", self.game_ended)

        self.connect("draw", self.expose)
        self.connect_after("realize", self.on_realized)
        conf.notify_add("showCords", self.on_show_cords)
        conf.notify_add("showCaptured", self.on_show_captured)
        conf.notify_add("faceToFace", self.on_face_to_face)
        conf.notify_add("pieceTheme", self.on_set_piece_theme)
        conf.notify_add("lightcolour", self.on_board_colour_theme)
        conf.notify_add("darkcolour", self.on_board_colour_theme)

        self.RANKS = self.model.boards[0].RANKS
        self.FILES = self.model.boards[0].FILES

        self.animationID = -1
        self._doStop = False
        self.animationStart = time()
        self.lastShown = None
        self.deadlist = []

        self.autoUpdateShown = True

        self.realSetShown = True
        # only false when self.shown set temporarily (change shown variation)
        # to avoid redrawMisc in animation

        self.padding = 0 # Set to self.pad when setcords is active
        self.square = 0, 0, self.FILES, 1 # An object global variable with the current
                                 # board size
        self.pad = 0.13 # Padding applied only when setcords is active

        self._selected = None
        self._hover = None
        self._active = None
        self._premove0 = None
        self._premove1 = None
        self._redarrow = None
        self._greenarrow = None
        self._bluearrow = None

        self._shown = self.model.ply
        self._showCords = False
        self.showCords = conf.get("showCords", False)
        self._showCaptured = False
        if self.preview:
            self.showCaptured = False
        else:
            self.showCaptured = conf.get("showCaptured", False) or \
                                self.model.variant.variant in DROP_VARIANTS
        self._showEnpassant = False
        self.lastMove = None
        self.matrix = cairo.Matrix()
        self.matrixPi = cairo.Matrix.init_rotate(pi)
        self.invmatrix = cairo.Matrix().invert()
        self.cordMatricesState = (0, 0)
        self._rotation = 0

        self.drawcount = 0
        self.drawtime = 0

        self.gotStarted = False
        self.animationLock = RLock()
        self.animating = False

        self.draggedPiece = None  # a piece being dragged by the user
        self.premovePiece = None
        self.premovePromotion = None

    @idle_add
    def game_started_after(self, model):
        # reenable shrinking the board
        self.set_size_request(-1, -1)
        self.emit("shown_changed", self.shown)

    def game_started(self, model):
        if conf.get("noAnimation", False):
            self.gotStarted = True
            self.redraw_canvas()
        else:
            if model.moves:
                self.lastMove = model.moves[-1]
            with self.animationLock:
                for row in self.model.boards[-1].data:
                    for piece in row.values(): #row:
                        if piece:
                            piece.opacity = 0
            self.gotStarted = True
            self.startAnimation()

    def game_changed(self, model, ply):
        # Play sounds
        if self.model.players and self.model.status != WAITING_TO_START:
            move = model.moves[-1]
            if move.is_capture(model.boards[-2]):
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
        if self.autoUpdateShown and self.shown+1 >= ply and self.shownIsMainLine():
            self.shown = ply

            # Rotate board
            if conf.get("autoRotate", True):
                if self.model.players and self.model.curplayer.__type__ == LOCAL:
                    self.rotation = self.model.boards[-1].color * pi

    def moves_undoing(self, model, moves):
        if self.shownIsMainLine():
            self.shown = model.ply-moves
        else:
            # Go back to the mainline to let animation system work
            board = model.getBoardAtPly(self.shown, self.shownVariationIdx)
            while board not in model.variations[0]:
                board = model.variations[self.shownVariationIdx][board.ply-model.lowply-1]
            self.shown = board.ply
            self.shownVariationIdx = 0
            self.shown = model.ply-moves
        self.redraw_canvas()

    def game_loading(self, model, uri):
        self.autoUpdateShown = False

    def game_loaded(self, model, uri):
        self.autoUpdateShown = True
        self._shown = model.ply

    def game_ended(self, model, reason):
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

    def on_show_cords(self, *args):
        self.showCords = conf.get("showCords", False)

    def on_show_captured(self, *args):
        self.showCaptured = conf.get("showCaptured", False)

    def on_face_to_face(self, *args):
        self.redraw_canvas()

    def on_set_piece_theme(self, *args):
        self.redraw_canvas()

    def on_board_colour_theme(self, *args):
        self.redraw_canvas()


    ###############################
    #          Animation          #
    ###############################

    def paintBoxAround(self, move):
        paintBox = self.cord2RectRelative(move.cord1)
        if move.flag != DROP:
            paintBox = join(paintBox, self.cord2RectRelative(move.cord0))
        if move.flag in (KING_CASTLE, QUEEN_CASTLE):
            board = self.model.boards[-1].board
            color = board.color
            wildcastle = Cord(board.ini_kings[color]).x == 3 and board.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS)
            if move.flag == KING_CASTLE:
                side = 0 if wildcastle else 1
                paintBox = join(paintBox, self.cord2RectRelative(Cord(board.ini_rooks[color][side])))
                paintBox = join(paintBox, self.cord2RectRelative(Cord(board.fin_rooks[color][side])))
                paintBox = join(paintBox, self.cord2RectRelative(Cord(board.fin_kings[color][side])))
            else:
                side = 1 if wildcastle else 0
                paintBox = join(paintBox, self.cord2RectRelative(Cord(board.ini_rooks[color][side])))
                paintBox = join(paintBox, self.cord2RectRelative(Cord(board.fin_rooks[color][side])))
                paintBox = join(paintBox, self.cord2RectRelative(Cord(board.fin_kings[color][side])))
        return paintBox

    def setShownBoard(self, board):
        """Set shown to the index of the given board in board list.
        If the board belongs to a different variationd,
        adjust the shown variation index too.
        If board is in the main line, reset the shown variation idx to 0 (the main line).
        """

        if board in self.model.variations[self.shownVariationIdx]:
            # if the board to be shown is in the current shown variation, we are ok
            self.shown = self.model.variations[self.shownVariationIdx].index(board) + self.model.lowply
            if board in self.model.variations[0]:
                self.shownVariationIdx = 0
        else:
            # else we have to go back first
            for vari in self.model.variations:
                if board in vari:
                    # Go back to the common board of variations to let animation system work
                    board_in_vari = board
                    while board_in_vari not in self.model.variations[self.shownVariationIdx]:
                        board_in_vari = vari[board_in_vari.ply-self.model.lowply-1]
                    self.realSetShown = False
                    self.shown = board_in_vari.ply
                    break
            # swich to the new variation
            self.shownVariationIdx = self.model.variations.index(vari)
            self.realSetShown = True
            self.shown = self.model.variations[self.shownVariationIdx].index(board) + self.model.lowply

    def shownIsMainLine(self):
        return self.shownVariationIdx == 0

    def _get_shown(self):
        return self._shown

    def _set_shown(self, shown):
        """Adjust the index in current variation board list."""

        # We don't do anything if we are already showing the right ply
        if shown == self._shown:
            return

        # This would cause IndexErrors later
        if not self.model.lowply <= shown <= self.model.variations[self.shownVariationIdx][-1].ply:
            return

        # If there is only one board, we don't do any animation, but simply
        # redraw the entire board. Same if we are at first draw.
        if len(self.model.boards) == 1 or self.shown < self.model.lowply:
            self._shown = shown
            if shown > self.model.lowply:
                self.lastMove = self.model.getMoveAtPly(shown-1, self.shownVariationIdx)
            self.emit("shown_changed", self.shown)
            self.redraw_canvas()
            return


        step = shown > self.shown and 1 or -1

        with self.animationLock:
            deadset = set()
            for i in range(self.shown, shown, step):
                board = self.model.getBoardAtPly(i, self.shownVariationIdx)
                board1 = self.model.getBoardAtPly(i + step, self.shownVariationIdx)
                if step == 1:
                    move = self.model.getMoveAtPly(i, self.shownVariationIdx)
                    moved, new, dead = board.simulateMove(board1, move)
                else:
                    move = self.model.getMoveAtPly(i-1, self.shownVariationIdx)
                    moved, new, dead = board.simulateUnmove(board1, move)

                # We need to ensure, that the piece coordinate is saved in the
                # piece
                for piece, cord0 in moved:
                    # Test if the piece already has a realcoord (has been dragged)
                    if (piece is not None) and piece.x == None:
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

        self.deadlist = []
        for y, row in enumerate(self.model.getBoardAtPly(self.shown, self.shownVariationIdx).data):
            for x, piece in row.items():
                if piece in deadset:
                    self.deadlist.append((piece,x,y))

        self._shown = shown
        if self.realSetShown:
            self.emit("shown_changed", self.shown)

        if self.animationID != -1:
            self._doStop = True

        self.animationStart = time()
        self.animating = True

        if self.lastMove:
            paintBox = self.paintBoxAround(self.lastMove)
            self.lastMove = None
            self.redraw_canvas(rect(paintBox))
        if self.shown > self.model.lowply:
            self.lastMove = self.model.getMoveAtPly(self.shown-1, self.shownVariationIdx)
        else:
            self.lastMove = None

        @idle_add
        def do_set_shown():
            self.runAnimation(redrawMisc=self.realSetShown)
            if not conf.get("noAnimation", False):
                while self.animating:
                    self.animationID = self.runAnimation()

        do_set_shown()

    shown = property(_get_shown, _set_shown)

    def runAnimation(self, redrawMisc=False):
        """
        The animationsystem in pychess is very loosely inspired by the one of
        chessmonk. The idea is, that every piece has a place in an array (the
        board.data one) for where to be drawn. If a piece is to be animated, it
        can set its x and y properties, to some cord (or part cord like 0.42 for
        42% right to file 0). Each time runAnimation is run, it will set those x
        and y properties a little closer to the location in the array. When it
        has reached its final location, x and y will be set to None. _set_shown,
        which starts the animation, also sets a timestamp for the acceleration
        to work properply.
        """

        if self._doStop:
            self._doStop = False
            self.animationID = -1
            return False

        with self.animationLock:
            paintBox = None

            mod = min(1, (time()-self.animationStart)/ANIMATION_TIME)
            board = self.model.getBoardAtPly(self.shown, self.shownVariationIdx)

            for y, row in enumerate(board.data):
                for x, piece in row.items():
                    if not piece: continue
                    if piece == self.draggedPiece: continue
                    if piece == self.premovePiece:
                        # if premove move is being made, the piece will already be sitting on the cord it needs to move to-
                        # do not animate and reset premove to None
                        if self.shown == self.premovePly:
                            piece.x = None
                            piece.y = None
                            self.setPremove(None, None, None, None)
                            continue
                        # otherwise, animate premove piece moving to the premove cord rather than the cord it actually exists on
                        elif self.premove0 and self.premove1:
                            x = self.premove1.x
                            y = self.premove1.y

                    if piece.x != None:
                        if not conf.get("noAnimation", False):
                            if piece.piece == KNIGHT:
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
                            paintBox = join(paintBox, self.cord2RectRelative(x, y))
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

            ready = []
            for i, dead in enumerate(self.deadlist):
                piece, x, y = dead
                if not paintBox:
                    paintBox = self.cord2RectRelative(x, y)
                else: paintBox = join(paintBox, self.cord2RectRelative(x, y))

                if not conf.get("noAnimation", False):
                    newOp = piece.opacity + (0-piece.opacity)*mod
                else:
                    newOp = 0

                if newOp <= 0 <= piece.opacity or abs(0-newOp) < 0.005:
                    ready.append(dead)
                else: piece.opacity = newOp

            for dead in ready:
                self.deadlist.remove(dead)

        if paintBox:
            self.redraw_canvas(rect(paintBox))

        if conf.get("noAnimation", False):
            self.animating = False
            return False
        else:
            if not paintBox:
                self.animating = False
            return paintBox and True or False

    def startAnimation(self):
        @idle_add
        def do_start_animation():
            self.runAnimation(redrawMisc=True)
            if not conf.get("noAnimation", False):
                while self.animating:
                    self.animationID = self.runAnimation()

        self.animationStart = time()
        self.animating = True
        do_start_animation()

    #############################
    #          Drawing          #
    #############################

    def on_realized(self, widget):
        p = (1-self.padding)
        alloc = self.get_allocation()
        square = float(min(alloc.width, alloc.height))*p
        xc = alloc.width/2. - square/2
        yc = alloc.height/2. - square/2
        s = square/self.FILES
        self.square = (xc, yc, square, s)

    def expose(self, widget, ctx):
        context = widget.get_window().cairo_create()

        start = time()
        a = Gdk.Rectangle()
        ce = ctx.clip_extents()
        a.x, a.y, a.width, a.height = ce[0], ce[1], ce[2]-ce[0], ce[3]-ce[1]

        if False:
            import profile
            profile.runctx("self.draw(context, a)", locals(), globals(), "/tmp/pychessprofile")
            from pstats import Stats
            s = Stats("/tmp/pychessprofile")
            s.sort_stats('cumulative')
            s.print_stats()
        else:
            with self.animationLock:
                self.draw(context, a)
            #self.drawcount += 1
            #self.drawtime += time() - start
            #if self.drawcount % 100 == 0:
            #    print( "Average FPS: %0.3f - %d / %d" % \
            #     (self.drawcount/self.drawtime, self.drawcount, self.drawtime))

        return False

    ############################################################################
    #                            drawing functions                             #
    ############################################################################

    ###############################
    #        redraw_canvas        #
    ###############################

    def redraw_canvas(self, r=None):
        @idle_add
        def redraw(r):
            if self.get_window():
                if not r:
                    alloc = self.get_allocation()
                    r = Gdk.Rectangle()
                    r.x, r.y, r.width, r.height = (0, 0, alloc.width, alloc.height)
#                    self.queue_draw_area(r.x, r.y, r.width, r.height)
                self.get_window().invalidate_rect(r, True)
                self.get_window().process_updates(True)
        redraw(r)

    ###############################
    #            draw             #
    ###############################

    def draw(self, context, r):
        #context.set_antialias (cairo.ANTIALIAS_NONE)

        if self.shown < self.model.lowply:
            print("exiting cause to lowlpy", self.shown, self.model.lowply)
            return

        alloc = self.get_allocation()

        self.matrix, self.invmatrix = matrixAround(
                self.matrix, alloc.width/2., alloc.height/2.)
        cos_, sin_ = self.matrix[0], self.matrix[1]
        context.transform(self.matrix)

        if self.showCaptured:
            holding_size = (alloc.width/(self.FILES+6))*6
        else:
            holding_size = 0
        square = float(min(alloc.width - holding_size, alloc.height))*(1-self.padding)
        if SCALE_ROTATED_BOARD:
            square /= abs(cos_)+abs(sin_)
        xc = alloc.width/2. - square/2
        yc = alloc.height/2. - square/2
        s = square/self.FILES
        self.square = (xc, yc, square, s)

        self.drawBoard (context, r)

        if min(alloc.width, alloc.height) > 32:
            self.drawCords (context, r)

        if self.gotStarted:
            self.drawSpecial (context, r)
            self.drawEnpassant (context, r)
            self.drawArrows (context)
            with self.animationLock:
                self.drawPieces (context, r)
            if not self.setup_position:
                self.drawLastMove (context, r)

        if self.model.status == KILLED:
            pass
            #self.drawCross (context, r)

        # Unselect to mark redrawn areas - for debugging purposes
        #context.transform(self.invmatrix)
        #context.rectangle(r.x,r.y,r.width,r.height)
        #dc = self.drawcount*50
        #dc = dc % 1536
        #c = dc % 256 / 255.
        #if dc < 256:
        #    context.set_source_rgb(1, ,c,0)
        #elif dc < 512:
        #    context.set_source_rgb(1-c,1, 0)
        #elif dc < 768:
        #    context.set_source_rgb(0, 1,c)
        #elif dc < 1024:
        #    context.set_source_rgb(0, 1-c,1)
        #elif dc < 1280:
        #    context.set_source_rgb(c,0, 1)
        #elif dc < 1536:
        #    context.set_source_rgb(1, 0,1-c)
        #context.stroke()

    ###############################
    #          drawCords          #
    ###############################

    def drawCords(self, context, r):
        thickness = 0.01
        signsize = 0.04

        if (not self.showCords) and (not self.setup_position):
            return

        xc, yc, square, s = self.square

        if contains(rect((xc, yc, square)), r): return

        t = thickness*square
        ss = signsize*square

        context.rectangle(xc-t*1.5,yc-t*1.5,square+t*3,square+t*3)

        sc = self.get_style_context()
        bool1, dcolor = sc.lookup_color("p_dark_color")
        dcolor = Gdk.RGBA()
        dcolor.parse(conf.get("darkcolour", "#000000000000"))
        context.set_source_rgba(dcolor.red, dcolor.green, dcolor.blue, dcolor.alpha)

        context.set_line_width(t)
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        context.stroke()

        pangoScale = float(Pango.SCALE)

        def paint (inv):
            for n in range(self.RANKS):
                rank = inv and n+1 or self.RANKS-n
                layout = self.create_pango_layout("%d" % rank)
                layout.set_font_description(
                        Pango.FontDescription("bold %d" % ss))
                w = layout.get_extents()[1].width/pangoScale
                h = layout.get_extents()[0].height/pangoScale

                # Draw left side
                context.move_to(xc-t*2.5-w, s*n+yc+h/2+t)
                PangoCairo.show_layout(context, layout)

                # Draw right side
                #context.move_to(xc+square+t*2.5, s*n+yc+h/2+t)
                #context.show_layout(layout)

                file = inv and self.FILES-n or n+1
                layout = self.create_pango_layout(chr(file+ord("A")-1))
                layout.set_font_description(
                        Pango.FontDescription("bold %d" % ss))

                w = layout.get_pixel_size()[0]
                h = layout.get_pixel_size()[1]
                y = layout.get_extents()[1].y/pangoScale

                # Draw top
                #context.move_to(xc+s*n+s/2.-w/2., yc-h-t*1.5)
                #context.show_layout(layout)

                # Draw bottom
                context.move_to(xc+s*n+s/2.-w/2., yc+square+t*1.5+abs(y))
                PangoCairo.show_layout(context, layout)

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
        sc = self.get_style_context()
        col = Gdk.RGBA()
        col.parse(conf.get("lightcolour", "#ffffffffffff"))
        context.set_source_rgba(col.red, col.green, col.blue, col.alpha)

        if self.model.variant.variant in ASEAN_VARIANTS:
            # just fill the whole board with light color
            context.rectangle(xc, yc, s*self.FILES, s*self.RANKS)
            context.fill()
        else:
            # light squares
            for x in range(self.FILES):
                for y in range(self.RANKS):
                    if x % 2 + y % 2 != 1:
                        context.rectangle(xc+x*s, yc+y*s, s, s)
            context.fill()

        found, col = sc.lookup_color("p_dark_color")
        col = Gdk.RGBA()
        col.parse(conf.get("darkcolour", "#000000000000"))
        context.set_source_rgba(col.red, col.green, col.blue, col.alpha)

        if self.model.variant.variant in ASEAN_VARIANTS:
            # just unfilled rectangles
            for x in range(self.FILES):
                for y in range(self.RANKS):
                    context.rectangle(xc+x*s, yc+y*s , s, s)
            # diagonals
            if self.model.variant.variant == SITTUYINCHESS:
                context.move_to(xc, yc)
                context.rel_line_to(square, square)
                context.move_to(xc+square, yc)
                context.rel_line_to(-square, square)
                context.stroke()
        else:
            # dark squares
            for x in range(self.FILES):
                for y in range(self.RANKS):
                    if x % 2 + y % 2 == 1:
                        context.rectangle(xc+x*s, yc+y*s, s, s)
            context.fill()

        context.rectangle(xc, yc, self.FILES*s, self.RANKS*s)
        context.stroke()

    ###############################
    #         drawPieces          #
    ###############################

    def getCordMatrices(self, x, y, inv=False):
        xc, yc, square, s = self.square
        square_, rot_ = self.cordMatricesState
        if square != self.square or rot_ != self.rotation:
            self.cordMatrices = [None] * self.FILES*self.RANKS + [None] * self.FILES*4
            self.cordMatricesState =(self.square, self.rotation)
        c = x * self.FILES + y
        if isinstance(c, int) and self.cordMatrices[c]:
            matrices = self.cordMatrices[c]
        else:
            cx, cy = self.cord2Point(x,y)
            matrices = matrixAround(self.matrix, cx+s/2., cy+s/2.)
            matrices += (cx, cy)
            if isinstance(c, int):
                self.cordMatrices[c] = matrices
        return matrices

    def __drawPiece(self, context, piece, x, y):
        # Maybe a premove was reset from another thread
        if piece is None:
            print("Trying to draw a None piece")
            return
        if self.model.variant == BlindfoldBoard:
            return
        elif self.model.variant == HiddenPawnsBoard:
            if piece.piece == PAWN:
                return
        elif self.model.variant == HiddenPiecesBoard:
            if piece.piece != PAWN:
                return

        if piece.captured and not self.showCaptured:
            return

        xc, yc, square, s = self.square

        if not conf.get("faceToFace", False):
            matrix, invmatrix, cx, cy = self.getCordMatrices(x, y)
        else:
            cx, cy = self.cord2Point(x,y)
            if piece.color == BLACK:
                matrix, invmatrix = matrixAround((-1, 0), cx+s/2., cy+s/2.)
            else:
                matrix = invmatrix = cairo.Matrix(1, 0,0, 1,0, 0)

        context.transform(invmatrix)
        Pieces.drawPiece(  piece, context,
                    cx+CORD_PADDING, cy+CORD_PADDING,
                    s-CORD_PADDING*2, allwhite = self.allwhite, asean=self.asean)
        context.transform(matrix)

    def drawPieces(self, context, r):
        pieces = self.model.getBoardAtPly(self.shown, self.shownVariationIdx)
        xc, yc, square, s = self.square

        sc = self.get_style_context()

        found, col = sc.lookup_color("p_fg_color")
        fgN = (col.red, col.green, col.blue)
        fgS = fgN

        found, col = sc.lookup_color("p_fg_active")
        fgA = (col.red, col.green, col.blue)

        found, col = sc.lookup_color("p_fg_prelight")
        fgP = (col.red, col.green, col.blue)

        fgM = fgN

        # As default we use normal foreground for selected cords, as it looks
        # less confusing. However for some themes, the normal foreground is so
        # similar to the selected background, that we have to use the selected
        # foreground.

        found, col = sc.lookup_color("p_bg_selected")
        bgSl = (col.red, col.green, col.blue)

        found, col = sc.lookup_color("p_dark_selected")
        bgSd = (col.red, col.green, col.blue)

        if min((fgN[0]-bgSl[0])**2+(fgN[1]-bgSl[1])**2+(fgN[2]-bgSl[2])**2,
               (fgN[0]-bgSd[0])**2+(fgN[1]-bgSd[1])**2+(fgN[2]-bgSd[2])**2) < 0.2:
            found, col = sc.lookup_color("p_fg_selected")
            fgS = (col.red, col.green, col.blue)

        # Draw dying pieces (Found in self.deadlist)
        for piece, x, y in self.deadlist:
            context.set_source_rgba(fgN[0],fgN[1],fgN[2],piece.opacity)
            self.__drawPiece(context, piece, x, y)

        # Draw pieces reincarnating (With opacity < 1)
        for y, row in enumerate(pieces.data):
            for x, piece in row.items():
                if not piece or piece.opacity == 1:
                    continue
                if piece.x:
                    x, y = piece.x, piece.y
                context.set_source_rgba(fgN[0],fgN[1],fgN[2],piece.opacity)
                self.__drawPiece(context, piece, x, y)

        # Draw standing pieces (Only those who intersect drawn area)
        for y, row in enumerate(pieces.data):
            for x, piece in row.items():
                if piece == self.premovePiece:
                    continue
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

        # Draw moving or dragged pieces (Those with piece.x and piece.y != None)
        context.set_source_rgb(*fgP)
        for y, row in enumerate(pieces.data):
            for x, piece in row.items():
                if not piece or piece.x == None or piece.opacity < 1:
                    continue
                self.__drawPiece(context, piece, piece.x, piece.y)

        # Draw standing premove piece
        context.set_source_rgb(*fgM)
        if self.premovePiece and self.premovePiece.x == None and self.premove0 and self.premove1:
            self.__drawPiece(context, self.premovePiece, self.premove1.x, self.premove1.y)


    ###############################
    #         drawSpecial         #
    ###############################

    def drawSpecial(self, context, redrawn):

        light_blue = (0.550, 0.775, 0.950, 0.8)
        dark_blue = (0.475, 0.700, 0.950, 0.5)

        used = []
        for cord, state in ((self.active, "_active"),
                           (self.selected, "_selected"),
                           (self.premove0, "_selected"),
                           (self.premove1, "_selected"),
                           (self.hover, "_prelight")):
            if not cord: continue
            if cord in used: continue
            # Ensure that same cord, if having multiple "tasks", doesn't get
            # painted more than once
            used.append(cord)

            bounding = self.cord2RectRelative(cord)
            if not intersects(rect(bounding), redrawn): continue

            board = self.model.getBoardAtPly(self.shown, self.shownVariationIdx)
            if board[cord] is None and (cord.x < 0 or cord.x > self.FILES-1):
                continue

            xc, yc, square, s = self.square
            x, y = self.cord2Point(cord)
            context.rectangle(x, y, s, s)
            if cord == self.premove0 or cord == self.premove1:
                if self.isLight(cord):
                    context.set_source_rgba(*light_blue)
                else:
                    context.set_source_rgba(*dark_blue)
            else:
                sc = self.get_style_context()
                if self.isLight(cord):
                    # bg
                    found, color = sc.lookup_color("p_bg" + state)
                else:
                    # dark
                    found, color = sc.lookup_color("p_dark" + state)
                if not found:
                    print("color not found in boardview.py:","p_dark" + state)
                r, g, b, a = color.red, color.green, color.blue, color.alpha
                context.set_source_rgba(r, g, b, a)
            context.fill()

    ###############################
    #        drawLastMove         #
    ###############################

    def drawLastMove(self, context, redrawn):
        if not self.lastMove: return
        if self.shown <= self.model.lowply: return
        show_board = self.model.getBoardAtPly(self.shown, self.shownVariationIdx)
        last_board = self.model.getBoardAtPly(self.shown - 1, self.shownVariationIdx)
        capture = self.lastMove.is_capture(last_board)

        wh = 0.27 # Width of marker
        p0 = 0.155 # Padding on last cord
        p1 = 0.085 # Padding on current cord
        sw = 0.02 # Stroke width

        xc, yc, square, s = self.square

        context.save()
        context.set_line_width(sw*s)

        d0 = {-1:1-p0, 1:p0}
        d1 = {-1:1-p1, 1:p1}
        ms = ((1, 1), (-1, 1), (-1,-1), (1,-1))

        light_yellow = (.929, .831, 0, 0.8)
        dark_yellow  = (.769, .627, 0, 0.5)
        light_orange = (.961, .475, 0, 0.8)
        dark_orange  = (.808, .361, 0, 0.5)
        light_green  = (0.337, 0.612, 0.117, 0.8)
        dark_green   = (0.237, 0.512, 0.17, 0.5)

        if self.lastMove.flag in (KING_CASTLE, QUEEN_CASTLE):
            ksq0 = last_board.board.kings[last_board.color]
            ksq1 = show_board.board.kings[last_board.color]
            wildcastle = Cord(last_board.board.ini_kings[last_board.color]).x == 3 and last_board.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS)
            if self.lastMove.flag == KING_CASTLE:
                side = 0 if wildcastle else 1
                rsq0 = show_board.board.ini_rooks[last_board.color][side]
                rsq1 = show_board.board.fin_rooks[last_board.color][side]
            else:
                side = 1 if wildcastle else 0
                rsq0 = show_board.board.ini_rooks[last_board.color][side]
                rsq1 = show_board.board.fin_rooks[last_board.color][side]
            cord_pairs = [ [Cord(ksq0), Cord(ksq1)], [Cord(rsq0), Cord(rsq1)] ]
        else:
            cord_pairs = [ [self.lastMove.cord0, self.lastMove.cord1] ]

        for [cord0, cord1] in cord_pairs:
            if cord0 is not None:
                rel = self.cord2RectRelative(cord0)
                if intersects(rect(rel), redrawn):
                    r = self.cord2Rect(cord0)
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

            rel = self.cord2RectRelative(cord1)
            if intersects(rect(rel), redrawn):
                r = self.cord2Rect(cord1)

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
                elif cord0 is None: # DROP move
                    context.set_source_rgba(*light_green)
                    context.fill_preserve()
                    context.set_source_rgba(*dark_green)
                    context.stroke()
                else:
                    context.set_source_rgba(*light_yellow)
                    context.fill_preserve()
                    context.set_source_rgba(*dark_yellow)
                    context.stroke()

    ###############################
    #         drawArrows          #
    ###############################

    def __drawArrow(self, context, cords, aw, ahw, ahh, asw, fillc, strkc):
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
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        context.set_line_width(asw*r[2])
        context.set_source_rgba(*strkc)
        context.stroke()

        context.restore()

    def drawArrows(self, context):
        # TODO: Only redraw when intersecting with the redrawn area

        aw = 0.3 # Arrow width
        ahw = 0.72 # Arrow head width
        ahh = 0.64 # Arrow head height
        asw = 0.08 # Arrow stroke width

        if self.bluearrow:
            self.__drawArrow(context, self.bluearrow, aw, ahw, ahh, asw,
                             (.447,.624,.812, 0.9), (.204,.396,.643, 1))

#         if self.shown != self.model.ply or \
#            self.model.boards != self.model.variations[0]:
#             return

        if self.greenarrow:
            self.__drawArrow(context, self.greenarrow, aw, ahw, ahh, asw,
                             (.54,.886,.2, 0.9), (.306,.604,.024, 1))

        if self.redarrow:
            self.__drawArrow(context, self.redarrow, aw, ahw, ahh, asw,
                             (.937,.16,.16, 0.9), (.643, 0,0, 1))

    ###############################
    #        drawEnpassant        #
    ###############################

    def drawEnpassant(self, context, redrawn):
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

    def drawCross(self, context, redrawn):
        xc, yc, square, s = self.square

        context.move_to(xc, yc)
        context.rel_line_to(square, square)
        context.move_to(xc+square, yc)
        context.rel_line_to(-square, square)

        context.set_line_cap(cairo.LINE_CAP_SQUARE)
        context.set_source_rgba(0, 0,0, 0.65)
        context.set_line_width(s)
        context.stroke_preserve()

        context.set_source_rgba(1, 0,0, 0.8)
        context.set_line_width(s/2.)
        context.stroke()

    ############################################################################
    #                                Attributes                                #
    ############################################################################

    ###############################
    #          Cord vars          #
    ###############################

    def _set_selected(self, cord):
        self._active = None
        if self._selected == cord: return
        if self._selected:
            r = rect(self.cord2RectRelative(self._selected))
            if cord: r = union(r, rect(self.cord2RectRelative(cord)))
        elif cord: r = rect(self.cord2RectRelative(cord))
        self._selected = cord
        self.redraw_canvas(r)
    def _get_selected(self):
        return self._selected
    selected = property(_get_selected, _set_selected)

    def _set_hover(self, cord):
        if self._hover == cord: return
        if self._hover:
            r = rect(self.cord2RectRelative(self._hover))
            # convert r from tuple to rect
            #tmpr = r
            #r = Gdk.Rectangle()
            #r.x, r.y, r.width, r.height = tmpr
            #if cord: r = r.union(rect(self.cord2RectRelative(cord)))
            if cord: r = union(r, rect(self.cord2RectRelative(cord)))
        elif cord:
            r = rect(self.cord2RectRelative(cord))
            # convert r from tuple to rect
            #tmpr = r
            #r = Gdk.Rectangle()
            #r.x, r.y, r.width, r.height = tmpr
        self._hover = cord
        self.redraw_canvas(r)
    def _get_hover(self):
        return self._hover
    hover = property(_get_hover, _set_hover)

    def _set_active(self, cord):
        if self._active == cord: return
        if self._active:
            r = rect(self.cord2RectRelative(self._active))
            if cord: r = union(r, rect(self.cord2RectRelative(cord)))
        elif cord: r = rect(self.cord2RectRelative(cord))
        self._active = cord
        self.redraw_canvas(r)
    def _get_active(self):
        return self._active
    active = property(_get_active, _set_active)

    def _set_premove0(self, cord):
        if self._premove0 == cord: return
        if self._premove0:
            r = rect(self.cord2RectRelative(self._premove0))
            if cord: r = union(r, rect(self.cord2RectRelative(cord)))
        elif cord: r = rect(self.cord2RectRelative(cord))
        self._premove0 = cord
        self.redraw_canvas(r)
    def _get_premove0(self):
        return self._premove0
    premove0 = property(_get_premove0, _set_premove0)

    def _set_premove1(self, cord):
        if self._premove1 == cord: return
        if self._premove1:
            r = rect(self.cord2RectRelative(self._premove1))
            if cord: r = union(r, rect(self.cord2RectRelative(cord)))
        elif cord: r = rect(self.cord2RectRelative(cord))
        self._premove1 = cord
        self.redraw_canvas(r)
    def _get_premove1(self):
        return self._premove1
    premove1 = property(_get_premove1, _set_premove1)

    ################################
    #          Arrow vars          #
    ################################

    def _set_redarrow(self, cords):
        if cords == self._redarrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._redarrow: paintCords += self._redarrow
        r = rect(self.cord2RectRelative(paintCords[0]))
        for cord in paintCords[1:]:
            r = union(r, rect(self.cord2RectRelative(cord)))
        self._redarrow = cords
        self.redraw_canvas(r)
    def _get_redarrow(self):
        return self._redarrow
    redarrow = property(_get_redarrow, _set_redarrow)

    def _set_greenarrow(self, cords):
        if cords == self._greenarrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._greenarrow: paintCords += self._greenarrow
        r = rect(self.cord2RectRelative(paintCords[0]))
        for cord in paintCords[1:]:
            r = union(r, rect(self.cord2RectRelative(cord)))
        self._greenarrow = cords
        self.redraw_canvas(r)
    def _get_greenarrow(self):
        return self._greenarrow
    greenarrow = property(_get_greenarrow, _set_greenarrow)

    def _set_bluearrow(self, cords):
        if cords == self._bluearrow: return
        paintCords = []
        if cords: paintCords += cords
        if self._bluearrow: paintCords += self._bluearrow
        r = rect(self.cord2RectRelative(paintCords[0]))
        for cord in paintCords[1:]:
            r = union(r, rect(self.cord2RectRelative(cord)))
        self._bluearrow = cords
        self.redraw_canvas(r)
    def _get_bluearrow(self):
        return self._bluearrow
    bluearrow = property(_get_bluearrow, _set_bluearrow)

    ################################
    #          Other vars          #
    ################################

    def _set_rotation(self, radians):
        if not conf.get("fullAnimation", True):
            def rotate():
                self._rotation = radians
                self.nextRotation = radians
                self.matrix = cairo.Matrix.init_rotate(radians)
                self.redraw_canvas()
            GLib.idle_add(rotate)
        else:
            if hasattr(self, "nextRotation") and \
                    self.nextRotation != self.rotation:
                return
            self.nextRotation = radians
            oldr = self.rotation
            start = time()
            next = True

            def rotate():
                amount = (time()-start)/ANIMATION_TIME
                if amount > 1:
                    amount = 1
                    next = False
                else: next = True
                self._rotation = new = oldr + amount*(radians-oldr)
                self.matrix = cairo.Matrix.init_rotate(new)
                self.redraw_canvas()
                return next

            self.animating = True
            GLib.idle_add(rotate)

    def _get_rotation(self):
        return self._rotation
    rotation = property(_get_rotation, _set_rotation)

    def _set_showCords(self, showCords):
        if not showCords:
            self.padding = 0
        else: self.padding = self.pad
        self._showCords = showCords
        self.redraw_canvas()
    def _get_showCords(self):
        return self._showCords
    showCords = property(_get_showCords, _set_showCords)

    def _set_showCaptured(self, showCaptured):
        self._showCaptured = showCaptured or self.model.variant.variant in DROP_VARIANTS
        files_for_holding = 6 if self._showCaptured else 0
        self.set_size_request(int(30*(self.FILES + files_for_holding)), 30*self.RANKS)
        self.redraw_canvas()
    def _get_showCaptured(self):
        return False if self.preview else self._showCaptured
    showCaptured = property(_get_showCaptured, _set_showCaptured)

    def _set_showEnpassant(self, showEnpassant):
        if self._showEnpassant == showEnpassant: return
        if self.model:
            enpascord = self.model.boards[-1].enpassant
            if enpascord:
                r = rect(self.cord2RectRelative(enpascord))
                self.redraw_canvas(r)
        self._showEnpassant = showEnpassant
    def _get_showEnpassant(self):
        return self._showEnpassant
    showEnpassant = property(_get_showEnpassant, _set_showEnpassant)

    ###########################
    #          Other          #
    ###########################

    def cord2Rect(self, cord, y=None):
        if y == None:
            x, y = cord.x, cord.y
        else: x = cord
        xc, yc, square, s = self.square

        r = (xc+x*s, yc+(self.RANKS-1-y)*s, s)
        return r

    def cord2Point(self, cord, y=None):
        r = self.cord2Rect(cord, y)
        return r[:2]

    def cord2RectRelative(self, cord, y=None):
        """ Like cord2Rect, but gives you bounding rect in case board is beeing
            Rotated """
        if isinstance(cord, tuple):
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

    def isLight(self, cord):
        if self.model.variant.variant in ASEAN_VARIANTS:
            return False
        x, y = cord.cords
        return x % 2 + y % 2 == 1

    def showFirst(self):
        if self.model.examined and self.model.noTD:
            self.model.goFirst()
        else:
            self.shown = self.model.lowply
            self.shownVariationIdx = 0

    def showPrev(self, step=1):
        if self.model.examined and self.model.noTD:
            self.model.goPrev(step)
        else:
            if self.shown > self.model.lowply:
                if self.shown - step > self.model.lowply:
                    self.shown -= step
                else:
                    self.shown = self.model.lowply

                if self.model.getBoardAtPly(self.shown, self.shownVariationIdx) in self.model.variations[0]:
                    self.shownVariationIdx = 0

    def showNext(self, step=1):
        if self.model.examined and self.model.noTD:
            self.model.goNext(step)
        else:
            maxply = self.model.variations[self.shownVariationIdx][-1].ply
            if self.shown < maxply:
                if self.shown + step < maxply:
                    self.shown += step
                else:
                    self.shown = maxply

    def showLast(self):
        if self.model.examined and self.model.noTD:
            self.model.goLast()
        else:
            maxply = self.model.variations[self.shownVariationIdx][-1].ply
            self.shown = maxply

    def backToMainLine(self):
        if self.model.examined and self.model.noTD:
            self.model.backToMainLine()
        else:
            while not self.shownIsMainLine():
                self.showPrev()

    def setPremove(self, premovePiece, premove0, premove1, premovePly, promotion=None):
        self.premovePiece = premovePiece
        self.premove0 = premove0
        self.premove1 = premove1
        self.premovePly = premovePly
        self.premovePromotion = promotion
