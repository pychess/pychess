# -*- coding: UTF-8 -*-


from math import floor, ceil, pi
from time import time
from io import StringIO

import cairo
from gi.repository import GLib, Gtk, Gdk, GObject, Pango, PangoCairo

from pychess.Savers import pgn
from pychess.System.prefix import addDataPrefix
from pychess.System import conf
from pychess.gfx import Pieces
from pychess.Savers.pgn import comment_arrows_re, comment_circles_re
from pychess.Utils.Cord import Cord
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import ASEAN_VARIANTS, DROP_VARIANTS, WAITING_TO_START, REMOTE, \
    LOCAL, DRAW, WHITEWON, BLACKWON, ABORTED, KILLED, DROP, \
    KING_CASTLE, QUEEN_CASTLE, WILDCASTLESHUFFLECHESS, \
    WILDCASTLECHESS, PAWN, KNIGHT, SITTUYINCHESS, BLACK
from pychess.Variants.blindfold import BlindfoldBoard, HiddenPawnsBoard, \
    HiddenPiecesBoard, AllWhiteBoard
from . import preferencesDialog
from pychess.perspectives import perspective_manager


def intersects(r_zero, r_one):
    """ Takes two square and determines if they have an Intersection
        Returns a boolean
    """
    w_zero = r_zero.width + r_zero.x
    h_zero = r_zero.height + r_zero.y
    w_one = r_one.width + r_one.x
    h_one = r_one.height + r_one.y
    return (w_one < r_one.x or w_one > r_zero.x) and \
        (h_one < r_one.y or h_one > r_zero.y) and \
        (w_zero < r_zero.x or w_zero > r_one.x) and \
        (h_zero < r_zero.y or h_zero > r_one.y)


def contains(r_zero, r_one):
    """ Takes two squares and determines if square one is contained
        within square zero
        Returns a boolean
    """
    w_zero = r_zero.width + r_zero.x
    h_zero = r_zero.height + r_zero.y
    w_one = r_one.width + r_one.x
    h_one = r_one.height + r_one.y
    return r_zero.x <= r_one.x and w_zero >= w_one and \
        r_zero.y <= r_one.y and h_zero >= h_one


def union(r_zero, r_one):
    """ Takes 2 rectangles and returns a rectangle that represents
        the union of the two areas
        Returns a Gdk.Rectangle
    """
    x_min = min(r_zero.x, r_one.x)
    y_min = min(r_zero.y, r_one.y)
    w_max = max(r_zero.x + r_zero.width, r_one.x + r_one.width) - x_min
    h_max = max(r_zero.y + r_zero.height, r_one.y + r_one.height) - y_min
    rct = Gdk.Rectangle()
    rct.x, rct.y, rct.width, rct.height = (x_min, y_min, w_max, h_max)
    return rct


def join(r_zero, r_one):
    """ Take(x, y, w, [h]) squares """

    if not r_zero:
        return r_one
    if not r_one:
        return r_zero
    if not r_zero and not r_one:
        return None

    if len(r_zero) == 3:
        r_zero = (r_zero[0], r_zero[1], r_zero[2], r_zero[2])
    if len(r_one) == 3:
        r_one = (r_one[0], r_one[1], r_one[2], r_one[2])

    x_one = min(r_zero[0], r_one[0])
    x_two = max(r_zero[0] + r_zero[2], r_one[0] + r_one[2])
    y_one = min(r_zero[1], r_one[1])
    y_two = max(r_zero[1] + r_zero[3], r_one[1] + r_one[3])

    return (x_one, y_one, x_two - x_one, y_two - y_one)


def rect(rectangle):
    """
        Takes a list of 3 variables x,y,height and generates a rectangle
        rectangle(list) : contains screen locations
        returns a Gdk.Rectangle
    """
    x_size, y_size = [int(floor(v)) for v in rectangle[:2]]
    width = int(ceil(rectangle[2]))
    if len(rectangle) == 4:
        height = int(ceil(rectangle[3]))
    else:
        height = width
    rct = Gdk.Rectangle()
    rct.x, rct.y, rct.width, rct.height = (x_size, y_size, width, height)
    return rct


def matrixAround(rotated_matrix, anchor_x, anchor_y):
    """
    Description : Rotates a matrix through the hypotenuse so that the original
    matrix becomes the inverse matrix and the inverse matrix becomes matrix
    Returns a tuple representing the matrix and its inverse

    """
    corner = rotated_matrix[0]
    side = rotated_matrix[1]
    anchor_yside = anchor_y * side
    anchor_xside = anchor_x * side
    anchor_ycorner = anchor_y * (1 - corner)
    anchor_xcorner = anchor_x * (1 - corner)
    matrix = cairo.Matrix(corner, side, -side, corner,
                          anchor_xcorner + anchor_yside,
                          anchor_ycorner - anchor_xside)
    invmatrix = cairo.Matrix(corner, -side, side, corner,
                             anchor_xcorner - anchor_yside,
                             anchor_ycorner + anchor_xside)
    return matrix, invmatrix


ANIMATION_TIME = 0.5

# If this is true, the board is scaled so that everything fits inside the window
# even if the board is rotated 45 degrees
SCALE_ROTATED_BOARD = False

CORD_PADDING = 1.5


class BoardView(Gtk.DrawingArea):
    """ Description The BoardView instance is used to render the board to screen and supports
        event updates associated with the game
    """

    __gsignals__ = {  # Signals emitted by class
        'shownChanged': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    def __init__(self, gamemodel=None, preview=False, setup_position=False):
        GObject.GObject.__init__(self)

        if gamemodel is None:
            gamemodel = GameModel()
        self.model = gamemodel
        self.allwhite = self.model.variant == AllWhiteBoard
        self.asean = self.model.variant.variant in ASEAN_VARIANTS
        self.preview = preview
        self.setup_position = setup_position
        self.shown_variation_idx = 0  # the main variation is the first in gamemodel.variations list

        self.model_cids = [
            self.model.connect("game_started", self.gameStarted),
            self.model.connect("game_changed", self.gameChanged),
            self.model.connect("moves_undoing", self.movesUndoing),
            self.model.connect("variation_undoing", self.variationUndoing),
            self.model.connect("game_loading", self.gameLoading),
            self.model.connect("game_loaded", self.gameLoaded),
            self.model.connect("game_ended", self.gameEnded),
        ]

        self.board_style_name = None
        self.board_frame_name = None

        self.draw_cid = self.connect("draw", self.expose)
        self.realize_cid = self.connect_after("realize", self.onRealized)
        self.notify_cids = [
            conf.notify_add("drawGrid", self.onDrawGrid),
            conf.notify_add("showCords", self.onShowCords),
            conf.notify_add("showCaptured", self.onShowCaptured),
            conf.notify_add("faceToFace", self.onFaceToFace),
            conf.notify_add("noAnimation", self.onNoAnimation),
            conf.notify_add("autoRotate", self.onAutoRotate),
            conf.notify_add("pieceTheme", self.onPieceTheme),
            conf.notify_add("board_frame", self.onBoardFrame),
            conf.notify_add("board_style", self.onBoardStyle),
            conf.notify_add("lightcolour", self.onBoardColour),
            conf.notify_add("darkcolour", self.onBoardColour),
        ]
        self.RANKS = self.model.boards[0].RANKS
        self.FILES = self.model.boards[0].FILES
        self.FILES_FOR_HOLDING = 6

        self.animation_start = time()
        self.last_shown = None
        self.deadlist = []

        self.auto_update_shown = True

        self.real_set_shown = True
        # only false when self.shown set temporarily(change shown variation)
        # to avoid redraw_misc in animation

        self.padding = 0  # Set to self.pad when setcords is active
        self.square = 0, 0, self.FILES, 1  # An object global variable with the current
        # board size
        self.pad = 0.06  # Padding applied only when setcords is active

        self._selected = None
        self._hover = None
        self._active = None
        self._premove0 = None
        self._premove1 = None
        self._redarrow = None
        self._greenarrow = None
        self._bluearrow = None

        self._shown = self.model.ply

        self.no_frame = False
        self._show_cords = False
        self.show_cords = conf.get("showCords")

        self._draw_grid = False
        self.draw_grid = conf.get("drawGrid")

        self._show_captured = None
        if self.setup_position:
            self.set_size_request(int(40 * (self.FILES + self.FILES_FOR_HOLDING)), 40 * self.RANKS)
            self.redrawCanvas()

        self.noAnimation = conf.get("noAnimation")
        self.faceToFace = conf.get("faceToFace")
        self.autoRotate = conf.get("autoRotate")

        self.onBoardColour()
        self.onBoardStyle()
        self.onBoardFrame()

        self._show_enpassant = False

        self.lastMove = None

        self.matrix = cairo.Matrix()
        self.matrix_pi = cairo.Matrix.init_rotate(pi)
        self.invmatrix = cairo.Matrix().invert()
        self.cord_matrices_state = (0, 0)
        self._rotation = 0

        self.drawcount = 0
        self.drawtime = 0

        self.got_started = False
        self.animating = False

        self.dragged_piece = None  # a piece being dragged by the user
        self.premove_piece = None
        self.premove_promotion = None

        # right click circles and arrows
        self.arrows = set()
        self.circles = set()
        self.pre_arrow = None
        self.pre_circle = None

        # circles and arrows from .pgn comments
        self.saved_circles = set()
        self.saved_arrows = set()

    def _del(self):
        self.disconnect(self.draw_cid)
        self.disconnect(self.realize_cid)
        for cid in self.notify_cids:
            conf.notify_remove(cid)
        for cid in self.model_cids:
            self.model.disconnect(cid)

    def gameStarted(self, model):
        if model.lesson_game:
            self.shown = model.lowply

        if self.noAnimation:
            self.got_started = True
            self.redrawCanvas()
        else:
            if model.moves:
                self.lastMove = model.moves[-1]

            for row in self.model.boards[-1].data:
                for piece in row.values():  # row:
                    if piece:
                        piece.opacity = 0

            self.got_started = True
            self.startAnimation()

        self.emit("shownChanged", self.shown)

    def gameChanged(self, model, ply):
        # Play sounds
        if self.model.players and self.model.status != WAITING_TO_START:
            move = model.moves[-1]
            if move.is_capture(model.boards[-2]):
                sound = "aPlayerCaptures"
            else:
                sound = "aPlayerMoves"

            if model.boards[-1].board.isChecked():
                sound = "aPlayerChecks"

            if model.players[0].__type__ == REMOTE and \
                    model.players[1].__type__ == REMOTE:
                sound = "observedMoves"

            preferencesDialog.SoundTab.playAction(sound)

        # Auto updating self.shown can be disabled. Useful for loading games.
        # If we are not at the latest game we are probably browsing the history,
        # and we won't like auto updating.
        if self.auto_update_shown and self.shown + 1 >= ply and self.shownIsMainLine():
            self.shown = ply

            # Rotate board
            if self.autoRotate:
                if self.model.players and self.model.curplayer.__type__ == LOCAL:
                    self.rotation = self.model.boards[-1].color * pi

    def movesUndoing(self, model, moves):
        if self.shownIsMainLine():
            self.shown = model.ply - moves
        else:
            # Go back to the mainline to let animation system work
            board = model.getBoardAtPly(self.shown, self.shown_variation_idx)
            while board not in model.variations[0]:
                board = model.variations[self.shown_variation_idx][board.ply - model.lowply - 1]
            self.shown = board.ply
            self.shown_variation_idx = 0
            self.shown = model.ply - moves
        self.redrawCanvas()

    def variationUndoing(self, model):
        self.showPrev()

    def gameLoading(self, model, uri):
        self.auto_update_shown = False

    def gameLoaded(self, model, uri):
        self.auto_update_shown = True
        self._shown = model.ply

    def gameEnded(self, model, reason):
        self.redrawCanvas()

        if self.model.players:
            sound = ""

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
            if sound != "":
                preferencesDialog.SoundTab.playAction(sound)

    def onDrawGrid(self, *args):
        """ Checks the configuration / preferences to see if the board
            grid should be displayed.
        """
        self.draw_grid = conf.get("drawGrid")

    def onShowCords(self, *args):
        """ Checks the configuration / preferences to see if the board
            co-ordinates should be displayed.
        """
        self.show_cords = conf.get("showCords")

    def onShowCaptured(self, *args):
        """ Check the configuration / preferences to see if
            the captured pieces should be displayed
        """
        self._setShowCaptured(conf.get("showCaptured"), force_restore=True)

    def onNoAnimation(self, *args):
        """ Check the configuration / preferences to see if
            no animation needed at all
        """
        self.noAnimation = conf.get("noAnimation")

    def onFaceToFace(self, *args):
        """ If the preference for pieces to be displayed facing each other
            has been set then refresh the board
        """
        self.faceToFace = conf.get("faceToFace")
        self.redrawCanvas()

    def onAutoRotate(self, *args):
        self.autoRotate = conf.get("autoRotate")

    def onPieceTheme(self, *args):
        """ If the preference to display another chess set has been
            selected then refresh the board
        """
        self.redrawCanvas()

    def onBoardColour(self, *args):
        """ If the preference to display another set of board colours has been
            selected then refresh the board
        """
        self.light_colour = conf.get("lightcolour")
        self.dark_colour = conf.get("darkcolour")

    def onBoardStyle(self, *args):
        """ If the preference to display another set of board colours has been
            selected then refresh the board
        """
        board_style = conf.get("board_style")
        self.colors_only = board_style == 0
        if not self.colors_only:
            # create dark and light square surfaces
            board_style_name = preferencesDialog.board_items[board_style][1]
            if self.board_style_name is None or self.board_style_name != board_style_name:
                self.board_style_name = board_style_name
                dark_png = addDataPrefix("boards/%s_d.png" % board_style_name)
                light_png = addDataPrefix("boards/%s_l.png" % board_style_name)
                self.dark_surface = cairo.ImageSurface.create_from_png(dark_png)
                self.light_surface = cairo.ImageSurface.create_from_png(light_png)

        self.redrawCanvas()

    def onBoardFrame(self, *args):
        board_frame = conf.get("board_frame")
        self.no_frame = board_frame == 0
        if not self.no_frame:
            # create board frame surface
            board_frame_name = preferencesDialog.board_items[board_frame][1]
            if self.board_frame_name is None or self.board_frame_name != board_frame_name:
                self.board_frame_name = board_frame_name
                frame_png = addDataPrefix("boards/%s_d.png" % board_frame_name)
                self.frame_surface = cairo.ImageSurface.create_from_png(frame_png)

        if not self.show_cords and self.no_frame:
            self.padding = 0.
        else:
            self.padding = self.pad

        self.redrawCanvas()

    ###############################
    #          Animation          #
    ###############################

    def paintBoxAround(self, move):
        paint_box = self.cord2RectRelative(move.cord1)
        if move.flag != DROP:
            paint_box = join(paint_box, self.cord2RectRelative(move.cord0))
        if move.flag in (KING_CASTLE, QUEEN_CASTLE):
            board = self.model.boards[-1].board
            color = board.color
            wildcastle = Cord(board.ini_kings[color]).x == 3 and \
                board.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS)
            if move.flag == KING_CASTLE:
                side = 0 if wildcastle else 1
                paint_box = join(paint_box, self.cord2RectRelative(Cord(board.ini_rooks[color][side])))
                paint_box = join(paint_box, self.cord2RectRelative(Cord(board.fin_rooks[color][side])))
                paint_box = join(paint_box, self.cord2RectRelative(Cord(board.fin_kings[color][side])))
            else:
                side = 1 if wildcastle else 0
                paint_box = join(paint_box, self.cord2RectRelative(Cord(board.ini_rooks[color][side])))
                paint_box = join(paint_box, self.cord2RectRelative(Cord(board.fin_rooks[color][side])))
                paint_box = join(paint_box, self.cord2RectRelative(Cord(board.fin_kings[color][side])))
        return paint_box

    def setShownBoard(self, board):
        """ Set shown to the index of the given board in board list.
            If the board belongs to a different variationd,
            adjust the shown variation index too.
            If board is in the main line, reset the shown variation idx to 0(the main line).
        """
        if board in self.model.variations[self.shown_variation_idx]:
            # if the board to be shown is in the current shown variation, we are ok
            self.shown = self.model.variations[self.shown_variation_idx].index(board) + \
                self.model.lowply
        else:
            # else we have to go back first
            for vari in self.model.variations:
                if board in vari:
                    # Go back to the common board of variations to let animation system work
                    board_in_vari = board
                    while board_in_vari not in self.model.variations[self.shown_variation_idx]:
                        board_in_vari = vari[board_in_vari.ply - self.model.lowply - 1]
                    self.real_set_shown = False
                    self.shown = board_in_vari.ply
                    break
            # swich to the new variation
            self.shown_variation_idx = self.model.variations.index(vari)
            self.real_set_shown = True
            self.shown = self.model.variations[self.shown_variation_idx].index(board) + \
                self.model.lowply

    def shownIsMainLine(self):
        return self.shown_variation_idx == 0

    @property
    def has_unsaved_shapes(self):
        return self.saved_arrows != self.arrows or self.saved_circles != self.circles

    def _getShown(self):
        return self._shown

    def _setShown(self, shown, old_variation_idx=None):
        """ Adjust the index in current variation board list.
            old_variation_index is used when variation was added
            to the last played move and we want to step back.
        """
        assert shown >= 0
        if shown < self.model.lowply:
            shown = self.model.lowply

        # This would cause IndexErrors later
        if shown > self.model.variations[self.shown_variation_idx][-1].ply:
            return

        if old_variation_idx is None:
            old_variation_idx = self.shown_variation_idx

        self.redarrow = None
        self.greenarrow = None
        self.bluearrow = None

        # remove all circles and arrows
        need_redraw = False
        if self.saved_circles:
            self.saved_circles.clear()
            need_redraw = True
        if self.saved_arrows:
            self.saved_arrows.clear()
            need_redraw = True
        if self.arrows:
            self.arrows.clear()
            need_redraw = True
        if self.circles:
            self.circles.clear()
            need_redraw = True
        if self.pre_arrow is not None:
            self.pre_arrow = None
            need_redraw = True
        if self.pre_circle is not None:
            self.pre_circle = None
            need_redraw = True

        # search circles/arrows in move comments
        board = self.model.getBoardAtPly(shown, self.shown_variation_idx).board
        if board.children:
            for child in board.children:
                if isinstance(child, str):
                    if "[%csl" in child:
                        match = comment_circles_re.search(child)
                        circles = match.groups()[0].split(",")
                        for circle in circles:
                            self.saved_circles.add(Cord(circle[1:3], color=circle[0]))
                            self.circles.add(Cord(circle[1:3], color=circle[0]))
                        need_redraw = True

                    if "[%cal" in child:
                        match = comment_arrows_re.search(child)
                        arrows = match.groups()[0].split(",")
                        for arrow in arrows:
                            self.saved_arrows.add((Cord(arrow[1:3], color=arrow[0]), Cord(arrow[3:5])))
                            self.arrows.add((Cord(arrow[1:3], color=arrow[0]), Cord(arrow[3:5])))
                        need_redraw = True

        if need_redraw:
            self.redrawCanvas()

        # If there is only one board, we don't do any animation, but simply
        # redraw the entire board. Same if we are at first draw.
        if len(self.model.boards) == 1 or self.shown < self.model.lowply:
            self._shown = shown
            if shown > self.model.lowply:
                self.lastMove = self.model.getMoveAtPly(shown - 1, self.shown_variation_idx)
            self.emit("shownChanged", self.shown)
            self.redrawCanvas()
            return

        step = shown > self.shown and 1 or -1

        deadset = set()
        for i in range(self.shown, shown, step):
            board = self.model.getBoardAtPly(i, old_variation_idx)
            board1 = self.model.getBoardAtPly(i + step, self.shown_variation_idx)
            if step == 1:
                move = self.model.getMoveAtPly(i, self.shown_variation_idx)
                moved, new, dead = board.simulateMove(board1, move)
            else:
                move = self.model.getMoveAtPly(i - 1, old_variation_idx)
                moved, new, dead = board.simulateUnmove(board1, move)

            # We need to ensure, that the piece coordinate is saved in the
            # piece
            for piece, cord0 in moved:
                # Test if the piece already has a realcoord(has been dragged)
                if (piece is not None) and piece.x is None:
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
        for y_loc, row in enumerate(self.model.getBoardAtPly(self.shown, old_variation_idx).data):
            for x_loc, piece in row.items():
                if piece in deadset:
                    self.deadlist.append((piece, x_loc, y_loc))

        self._shown = shown
        if self.real_set_shown:
            board = self.model.getBoardAtPly(self.shown, self.shown_variation_idx)
            if board in self.model.variations[0]:
                self.shown_variation_idx = 0
            else:
                for vari in self.model.variations:
                    if board in vari:
                        # swich to the new variation
                        self.shown_variation_idx = self.model.variations.index(vari)
                        break
            self.emit("shownChanged", self.shown)

        self.animation_start = time()
        self.animating = True

        if self.lastMove:
            paint_box = self.paintBoxAround(self.lastMove)
            self.lastMove = None
            self.redrawCanvas(rect(paint_box))

        if self.shown > self.model.lowply:
            self.lastMove = self.model.getMoveAtPly(self.shown - 1, self.shown_variation_idx)
            paint_box = self.paintBoxAround(self.lastMove)
            self.redrawCanvas(rect(paint_box))
        else:
            self.lastMove = None

        self.runAnimation(redraw_misc=self.real_set_shown)
        if not self.noAnimation:
            while self.animating:
                self.runAnimation()

    shown = property(_getShown, _setShown)

    def runAnimation(self, redraw_misc=False):
        """
            The animationsystem in pychess is very loosely inspired by the one of
            chessmonk. The idea is, that every piece has a place in an array(the
            board.data one) for where to be drawn. If a piece is to be animated, it
            can set its x and y properties, to some cord(or part cord like 0.42 for
            42% right to file 0). Each time runAnimation is run, it will set those x
            and y properties a little closer to the location in the array. When it
            has reached its final location, x and y will be set to None. _setShown,
            which starts the animation, also sets a timestamp for the acceleration
            to work properply.
        """
        if self.model is None:
            return False

        if not self.animating:
            return False

        paint_box = None

        mod = min(1, (time() - self.animation_start) / ANIMATION_TIME)
        board = self.model.getBoardAtPly(self.shown, self.shown_variation_idx)

        for y_loc, row in enumerate(board.data):
            for x_loc, piece in row.items():
                if not piece:
                    continue
                if piece == self.dragged_piece:
                    continue
                if piece == self.premove_piece:
                    # if premove move is being made, the piece will already be
                    # sitting on the cord it needs to move to-
                    # do not animate and reset premove to None
                    if self.shown == self.premove_ply:
                        piece.x = None
                        piece.y = None
                        self.setPremove(None, None, None, None)
                        continue
                    # otherwise, animate premove piece moving to the premove cord
                    # rather than the cord it actually exists on
                    elif self.premove0 and self.premove1:
                        x_loc = self.premove1.x
                        y_loc = self.premove1.y

                if piece.x is not None:
                    if not self.noAnimation:
                        if piece.piece == KNIGHT:
                            newx = piece.x + (x_loc - piece.x) * mod**(1.5)
                            newy = piece.y + (y_loc - piece.y) * mod
                        else:
                            newx = piece.x + (x_loc - piece.x) * mod
                            newy = piece.y + (y_loc - piece.y) * mod
                    else:
                        newx, newy = x_loc, y_loc

                    paint_box = join(paint_box, self.cord2RectRelative(piece.x,
                                                                       piece.y))
                    paint_box = join(paint_box, self.cord2RectRelative(newx, newy))

                    if (newx <= x_loc <= piece.x or newx >= x_loc >= piece.x) and \
                       (newy <= y_loc <= piece.y or newy >= y_loc >= piece.y) or \
                       abs(newx - x_loc) < 0.005 and abs(newy - y_loc) < 0.005:
                        paint_box = join(paint_box, self.cord2RectRelative(x_loc, y_loc))
                        piece.x = None
                        piece.y = None
                    else:
                        piece.x = newx
                        piece.y = newy

                if piece.opacity < 1:
                    if piece.x is not None:
                        px_loc = piece.x
                        py_loc = piece.y
                    else:
                        px_loc = x_loc
                        py_loc = y_loc

                    if paint_box:
                        paint_box = join(paint_box, self.cord2RectRelative(px_loc, py_loc))
                    else:
                        paint_box = self.cord2RectRelative(px_loc, py_loc)

                    if not self.noAnimation:
                        new_op = piece.opacity + (1 - piece.opacity) * mod
                    else:
                        new_op = 1

                    if new_op >= 1 >= piece.opacity or abs(1 - new_op) < 0.005:
                        piece.opacity = 1
                    else:
                        piece.opacity = new_op

        ready = []
        for i, dead in enumerate(self.deadlist):
            piece, x_loc, y_loc = dead
            if not paint_box:
                paint_box = self.cord2RectRelative(x_loc, y_loc)
            else:
                paint_box = join(paint_box, self.cord2RectRelative(x_loc, y_loc))

            if not self.noAnimation:
                new_op = piece.opacity + (0 - piece.opacity) * mod
            else:
                new_op = 0

            if new_op <= 0 <= piece.opacity or abs(0 - new_op) < 0.005:
                ready.append(dead)
            else:
                piece.opacity = new_op

        for dead in ready:
            self.deadlist.remove(dead)

        if paint_box:
            self.redrawCanvas(rect(paint_box))

        if self.noAnimation:
            self.animating = False
            return False
        else:
            if not paint_box:
                self.animating = False
            return paint_box and True or False

    def startAnimation(self):
        self.animation_start = time()
        self.animating = True

        self.runAnimation(redraw_misc=True)
        if not self.noAnimation:
            while self.animating:
                self.runAnimation()

    #############################
    #          Drawing          #
    #############################

    def onRealized(self, widget):
        padding = (1 - self.padding)
        alloc = self.get_allocation()
        square = float(min(alloc.width, alloc.height)) * padding
        xc_loc = alloc.width / 2. - square / 2
        yc_loc = alloc.height / 2. - square / 2
        size = square / self.FILES
        self.square = (xc_loc, yc_loc, square, size)

    def expose(self, widget, ctx):
        context = widget.get_window().cairo_create()

        start = time()
        rectangle = Gdk.Rectangle()
        clip_ext = ctx.clip_extents()
        rectangle.x, rectangle.y = clip_ext[0], clip_ext[1]
        rectangle.width, rectangle.height = clip_ext[2] - clip_ext[0], clip_ext[3] - clip_ext[1]

        if False:
            import profile
            profile.runctx("self.draw(context, rectangle)", locals(), globals(), "/tmp/pychessprofile")
            from pstats import Stats
            stats = Stats("/tmp/pychessprofile")
            stats.sort_stats('cumulative')
            stats.print_stats()
        else:
            self.draw(context, rectangle)
            # self.drawcount += 1
            # self.drawtime += time() - start
            # if self.drawcount % 100 == 0:
            #    print( "Average FPS: %0.3f - %d / %d" % \
            #     (self.drawcount/self.drawtime, self.drawcount, self.drawtime))

        return False

    ############################################################################
    #                            drawing functions                             #
    ############################################################################

    ###############################
    #        redrawCanvas        #
    ###############################

    def redrawCanvas(self, rect=None):
        if self.get_window():
            if not rect:
                alloc = self.get_allocation()
                rect = Gdk.Rectangle()
                rect.x, rect.y, rect.width, rect.height = (0, 0, alloc.width, alloc.height)
            self.get_window().invalidate_rect(rect, True)
            self.get_window().process_updates(True)

    ###############################
    #            draw             #
    ###############################

    def draw(self, context, r):
        # context.set_antialias(cairo.ANTIALIAS_NONE)

        if self.shown < self.model.lowply:
            print("exiting cause to lowlpy", self.shown, self.model.lowply)
            return

        alloc = self.get_allocation()

        self.matrix, self.invmatrix = matrixAround(
            self.matrix, alloc.width / 2., alloc.height / 2.)
        cos_, sin_ = self.matrix[0], self.matrix[1]
        context.transform(self.matrix)

        square = float(min(alloc.width, alloc.height)) * (1 - self.padding)
        if SCALE_ROTATED_BOARD:
            square /= abs(cos_) + abs(sin_)
        xc_loc = alloc.width / 2. - square / 2
        yc_loc = alloc.height / 2. - square / 2
        side = square / self.FILES
        self.square = (xc_loc, yc_loc, square, side)

        self.drawBoard(context, r)

        if min(alloc.width, alloc.height) > 32:
            self.drawCords(context, r)

        if self.got_started:
            self.drawSpecial(context, r)
            self.drawEnpassant(context, r)
            self.drawCircles(context)
            self.drawArrows(context)
            self.drawPieces(context, r)
            if not self.setup_position:
                self.drawLastMove(context, r)

        if self.model.status == KILLED:
            pass
            # self.drawCross(context, r)

        # At this point we have real values of self.get_allocation()
        # and can adjust board paned divider if needed
        if self._show_captured is None:
            self.showCaptured = conf.get("showCaptured")

        # Unselect to mark redrawn areas - for debugging purposes
        # context.transform(self.invmatrix)
        # context.rectangle(r.x,r.y,r.width,r.height)
        # dc = self.drawcount*50
        # dc = dc % 1536
        # c = dc % 256 / 255.
        # if dc < 256:
        #    context.set_source_rgb(1, ,c,0)
        # elif dc < 512:
        #    context.set_source_rgb(1-c,1, 0)
        # elif dc < 768:
        #    context.set_source_rgb(0, 1,c)
        # elif dc < 1024:
        #    context.set_source_rgb(0, 1-c,1)
        # elif dc < 1280:
        #    context.set_source_rgb(c,0, 1)
        # elif dc < 1536:
        #    context.set_source_rgb(1, 0, 1-c)
        # context.stroke()

    ###############################
    #          drawCords          #
    ###############################

    def drawCords(self, context, rectangle):
        thickness = 0.01
        signsize = 0.02

        if (not self.show_cords) and (not self.setup_position):
            return

        xc_loc, yc_loc, square, side = self.square

        if rectangle is not None and contains(rect((xc_loc, yc_loc, square)), rectangle):
            return

        thick = thickness * square
        sign_size = signsize * square

        pangoScale = float(Pango.SCALE)
        if self.no_frame:
            context.set_source_rgb(0.0, 0.0, 0.0)
        else:
            context.set_source_rgb(1.0, 1.0, 1.0)

        def paint(inv):
            for num in range(self.RANKS):
                rank = inv and num + 1 or self.RANKS - num
                layout = self.create_pango_layout("%d" % rank)
                layout.set_font_description(
                    Pango.FontDescription("bold %d" % sign_size))
                width = layout.get_extents()[1].width / pangoScale
                height = layout.get_extents()[0].height / pangoScale

                # Draw left side
                context.move_to(xc_loc - thick - width, side * num + yc_loc + height / 2 + thick * 3)
                PangoCairo.show_layout(context, layout)

                file = inv and self.FILES - num or num + 1
                layout = self.create_pango_layout(chr(file + ord("A") - 1))
                layout.set_font_description(
                    Pango.FontDescription("bold %d" % sign_size))

                # Draw bottom
                context.move_to(xc_loc + side * num + side / 2 - width / 2, yc_loc + square)
                PangoCairo.show_layout(context, layout)

        matrix, invmatrix = matrixAround(self.matrix_pi, xc_loc + square / 2, yc_loc + square / 2)
        if self.rotation == 0:
            paint(False)
        else:
            context.transform(matrix)
            paint(True)
            context.transform(invmatrix)

        if self.faceToFace:
            if self.rotation == 0:
                context.transform(matrix)
                paint(True)
                context.transform(invmatrix)
            else:
                paint(False)

    def draw_image(self, context, image_surface, left, top, width, height):
        """ Draw a scaled image on a given context. """

        # calculate scale
        image_width = image_surface.get_width()
        image_height = image_surface.get_height()
        width_ratio = float(width) / float(image_width)
        height_ratio = float(height) / float(image_height)
        scale_xy = min(width_ratio, height_ratio)

        # scale image and add it
        context.save()
        context.translate(left, top)
        context.scale(scale_xy, scale_xy)
        context.set_source_surface(image_surface)

        context.paint()
        context.restore()

    def draw_frame(self, context, image_surface, left, top, width, height):
        """ Draw a repeated image pattern on a given context. """

        pat = cairo.SurfacePattern(image_surface)
        pat.set_extend(cairo.EXTEND_REPEAT)

        context.rectangle(left, top, width, height)
        context.set_source(pat)

        context.fill()

    ###############################
    #          drawBoard          #
    ###############################

    def drawBoard(self, context, r):
        xc_loc, yc_loc, square, side = self.square

        col = Gdk.RGBA()
        col.parse(self.light_colour)
        context.set_source_rgba(col.red, col.green, col.blue, col.alpha)

        if self.model.variant.variant in ASEAN_VARIANTS:
            # just fill the whole board with light color
            if self.colors_only:
                context.rectangle(xc_loc, yc_loc, side * self.FILES, side * self.RANKS)
            else:
                self.draw_image(context, self.light_surface, xc_loc, yc_loc, side * self.FILES, side * self.RANKS)
            if self.colors_only:
                context.fill()
        else:
            # light squares
            for x_loc in range(self.FILES):
                for y_loc in range(self.RANKS):
                    if x_loc % 2 + y_loc % 2 != 1:
                        if self.colors_only:
                            context.rectangle(xc_loc + x_loc * side, yc_loc + y_loc * side, side, side)
                        else:
                            self.draw_image(context, self.light_surface, xc_loc + x_loc * side, yc_loc + y_loc * side, side, side)
            if self.colors_only:
                context.fill()

        col = Gdk.RGBA()
        col.parse(self.dark_colour)
        context.set_source_rgba(col.red, col.green, col.blue, col.alpha)

        if self.model.variant.variant in ASEAN_VARIANTS:
            # diagonals
            if self.model.variant.variant == SITTUYINCHESS:
                context.move_to(xc_loc, yc_loc)
                context.rel_line_to(square, square)
                context.move_to(xc_loc + square, yc_loc)
                context.rel_line_to(-square, square)
                context.stroke()
        else:
            # dark squares
            for x_loc in range(self.FILES):
                for y_loc in range(self.RANKS):
                    if x_loc % 2 + y_loc % 2 == 1:
                        if self.colors_only:
                            context.rectangle((xc_loc + x_loc * side), (yc_loc + y_loc * side), side, side)
                        else:
                            self.draw_image(context, self.dark_surface, (xc_loc + x_loc * side), (yc_loc + y_loc * side), side, side)
            if self.colors_only:
                context.fill()

        if not self.no_frame:
            # board frame
            delta = side / 4
            # top
            self.draw_frame(context, self.frame_surface, xc_loc - delta, yc_loc - delta, self.FILES * side + delta * 2, delta)
            # bottom
            self.draw_frame(context, self.frame_surface, xc_loc - delta, yc_loc + self.RANKS * side, self.FILES * side + delta * 2, delta)
            # left
            self.draw_frame(context, self.frame_surface, xc_loc - delta, yc_loc, delta, self.FILES * side)
            # right
            self.draw_frame(context, self.frame_surface, xc_loc + self.FILES * side, yc_loc, delta, self.FILES * side)

        if self.draw_grid:
            # grid lines between squares
            context.set_source_rgb(0.0, 0.0, 0.0)
            context.set_line_width(0.5 if r is None else 1.0)

            for loc in range(self.FILES):
                context.move_to(xc_loc + side * loc, yc_loc)
                context.line_to(xc_loc + side * loc, yc_loc + self.FILES * side)
                context.move_to(xc_loc, yc_loc + side * loc)
                context.line_to(xc_loc + self.FILES * side, yc_loc + side * loc)

            context.rectangle(xc_loc, yc_loc, self.FILES * side, self.RANKS * side)
            context.stroke()

        context.set_source_rgba(col.red, col.green, col.blue, col.alpha)

    ###############################
    #         drawPieces          #
    ###############################

    def getCordMatrices(self, x_loc, y_loc, inv=False):
        square, side = self.square[2], self.square[3]
        rot_ = self.cord_matrices_state[1]
        if square != self.square or rot_ != self.rotation:
            self.cord_matrices = [None] * self.FILES * self.RANKS + [None] * self.FILES * 4
            self.cord_matrices_state = (self.square, self.rotation)
        c_loc = x_loc * self.FILES + y_loc
        if isinstance(c_loc, int) and self.cord_matrices[c_loc]:
            matrices = self.cord_matrices[c_loc]
        else:
            cx_loc, cy_loc = self.cord2Point(x_loc, y_loc)
            matrices = matrixAround(self.matrix, cx_loc + side / 2., cy_loc + side / 2.)
            matrices += (cx_loc, cy_loc)
            if isinstance(c_loc, int):
                self.cord_matrices[c_loc] = matrices
        return matrices

    def __drawPiece(self, context, piece, x_loc, y_loc):
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

        side = self.square[3]

        if not self.faceToFace:
            matrix, invmatrix, cx_loc, cy_loc = self.getCordMatrices(x_loc, y_loc)
        else:
            cx_loc, cy_loc = self.cord2Point(x_loc, y_loc)
            if piece.color == BLACK:
                matrix, invmatrix = matrixAround((-1, 0), cx_loc + side / 2., cy_loc + side / 2.)
            else:
                matrix = invmatrix = cairo.Matrix(1, 0, 0, 1, 0, 0)

        context.transform(invmatrix)
        Pieces.drawPiece(piece, context,
                         cx_loc + CORD_PADDING, cy_loc + CORD_PADDING,
                         side - CORD_PADDING * 2, allwhite=self.allwhite, asean=self.asean)
        context.transform(matrix)

    def drawPieces(self, context, rectangle):
        pieces = self.model.getBoardAtPly(self.shown, self.shown_variation_idx)

        style_ctxt = self.get_style_context()

        col = style_ctxt.lookup_color("p_fg_color")[1]
        fg_n = (col.red, col.green, col.blue)
        fg_s = fg_n

        col = style_ctxt.lookup_color("p_fg_active")[1]
        fg_a = (col.red, col.green, col.blue)

        col = style_ctxt.lookup_color("p_fg_prelight")[1]
        fg_p = (col.red, col.green, col.blue)

        fg_m = fg_n

        # As default we use normal foreground for selected cords, as it looks
        # less confusing. However for some themes, the normal foreground is so
        # similar to the selected background, that we have to use the selected
        # foreground.

        col = style_ctxt.lookup_color("p_bg_selected")[1]
        bg_sl = (col.red, col.green, col.blue)

        col = style_ctxt.lookup_color("p_dark_selected")[1]
        bg_sd = (col.red, col.green, col.blue)

        if min((fg_n[0] - bg_sl[0])**2 + (fg_n[1] - bg_sl[1])**2 + (fg_n[2] - bg_sl[2])**2,
               (fg_n[0] - bg_sd[0])**2 + (fg_n[1] - bg_sd[1])**2 + (fg_n[2] - bg_sd[2])**2) < 0.2:
            col = style_ctxt.lookup_color("p_fg_selected")[1]
            fg_s = (col.red, col.green, col.blue)

        # Draw dying pieces(Found in self.deadlist)
        for piece, x_loc, y_loc in self.deadlist:
            context.set_source_rgba(fg_n[0], fg_n[1], fg_n[2], piece.opacity)
            self.__drawPiece(context, piece, x_loc, y_loc)

        # Draw pieces reincarnating(With opacity < 1)
        for y_loc, row in enumerate(pieces.data):
            for x_loc, piece in row.items():
                if not piece or piece.opacity == 1:
                    continue
                if piece.x:
                    x_loc, y_loc = piece.x, piece.y
                context.set_source_rgba(fg_n[0], fg_n[1], fg_n[2], piece.opacity)
                self.__drawPiece(context, piece, x_loc, y_loc)

        # Draw standing pieces(Only those who intersect drawn area)
        for y_loc, row in enumerate(pieces.data):
            for x_loc, piece in row.items():
                if piece == self.premove_piece:
                    continue
                if not piece or piece.x is not None or piece.opacity < 1:
                    continue
                if rectangle is not None and not intersects(rect(self.cord2RectRelative(x_loc, y_loc)), rectangle):
                    continue
                if Cord(x_loc, y_loc) == self.selected:
                    context.set_source_rgb(*fg_s)
                elif Cord(x_loc, y_loc) == self.active:
                    context.set_source_rgb(*fg_a)
                elif Cord(x_loc, y_loc) == self.hover:
                    context.set_source_rgb(*fg_p)
                else:
                    context.set_source_rgb(*fg_n)

                self.__drawPiece(context, piece, x_loc, y_loc)

        # Draw moving or dragged pieces(Those with piece.x and piece.y != None)
        context.set_source_rgb(*fg_p)
        for y_loc, row in enumerate(pieces.data):
            for x_loc, piece in row.items():
                if not piece or piece.x is None or piece.opacity < 1:
                    continue
                self.__drawPiece(context, piece, piece.x, piece.y)

        # Draw standing premove piece
        context.set_source_rgb(*fg_m)
        if self.premove_piece and self.premove_piece.x is None and self.premove0 and self.premove1:
            self.__drawPiece(context, self.premove_piece, self.premove1.x, self.premove1.y)

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
            if not cord:
                continue
            if cord in used:
                continue
            # Ensure that same cord, if having multiple "tasks", doesn't get
            # painted more than once
            used.append(cord)

            bounding = self.cord2RectRelative(cord)
            if not intersects(rect(bounding), redrawn):
                continue

            board = self.model.getBoardAtPly(self.shown, self.shown_variation_idx)
            if board[cord] is None and (cord.x < 0 or cord.x > self.FILES - 1):
                continue

            side = self.square[3]
            x_loc, y_loc = self.cord2Point(cord)
            context.rectangle(x_loc, y_loc, side, side)
            if cord == self.premove0 or cord == self.premove1:
                if self.isLight(cord):
                    context.set_source_rgba(*light_blue)
                else:
                    context.set_source_rgba(*dark_blue)
            else:
                style_ctxt = self.get_style_context()
                if self.isLight(cord):
                    # bg
                    found, color = style_ctxt.lookup_color("p_bg" + state)
                else:
                    # dark
                    found, color = style_ctxt.lookup_color("p_dark" + state)
                if not found:
                    print("color not found in boardview.py:", "p_dark" + state)
                red, green, blue, alpha = color.red, color.green, color.blue, color.alpha
                context.set_source_rgba(red, green, blue, alpha)
            context.fill()

    def color2rgba(self, color):
        if color == "R":
            rgba = (.643, 0, 0, 0.8)
        elif color == "B":
            rgba = (.204, .396, .643, 0.8)
        elif color == "Y":
            rgba = (.961, .475, 0, 0.8)
        else:
            # light_green
            rgba = (0.337, 0.612, 0.117, 0.8)
        return rgba

    def drawCircles(self, context):
        radius = self.square[3] / 2.0
        context.set_line_width(4)

        for cord in self.circles:
            rgba = self.color2rgba(cord.color)
            context.set_source_rgb(*rgba[:3])
            x_loc, y_loc = self.cord2Point(cord)
            context.new_sub_path()
            context.arc(x_loc + radius, y_loc + radius, radius - 3, 0, 2 * pi)
            context.stroke()
        if self.pre_circle is not None:
            rgba = self.color2rgba(self.pre_circle.color)
            context.set_source_rgb(*rgba[:3])
            x_loc, y_loc = self.cord2Point(self.pre_circle)
            context.new_sub_path()
            context.arc(x_loc + radius, y_loc + radius, radius - 3, 0, 2 * pi)
            context.stroke()

        arw = 0.15  # Arrow width
        arhw = 0.6  # Arrow head width
        arhh = 0.6  # Arrow head height
        arsw = 0.0  # Arrow stroke width
        for arrow_cords in self.arrows:
            rgba = self.color2rgba(arrow_cords[0].color)
            self.__drawArrow(context, arrow_cords, arw, arhw, arhh, arsw, rgba, rgba)
        if self.pre_arrow is not None:
            rgba = self.color2rgba(self.pre_arrow[0].color)
            self.__drawArrow(context, self.pre_arrow, arw, arhw, arhh, arsw, rgba, rgba)

    ###############################
    #        drawLastMove         #
    ###############################

    def drawLastMove(self, context, redrawn):
        if not self.lastMove:
            return
        if self.shown <= self.model.lowply:
            return
        show_board = self.model.getBoardAtPly(self.shown, self.shown_variation_idx)
        last_board = self.model.getBoardAtPly(self.shown - 1, self.shown_variation_idx)
        capture = self.lastMove.is_capture(last_board)

        mark_width = 0.27  # Width of marker
        padding_last = 0.155  # Padding on last cord
        padding_curr = 0.085  # Padding on current cord
        stroke_width = 0.02  # Stroke width

        side = self.square[3]

        context.save()
        context.set_line_width(stroke_width * side)

        dic0 = {-1: 1 - padding_last, 1: padding_last}
        dic1 = {-1: 1 - padding_curr, 1: padding_curr}
        matrix_scaler = ((1, 1), (-1, 1), (-1, -1), (1, -1))

        light_yellow = (.929, .831, 0, 0.8)
        dark_yellow = (.769, .627, 0, 0.5)
        light_orange = (.961, .475, 0, 0.8)
        dark_orange = (.808, .361, 0, 0.5)
        light_green = (0.337, 0.612, 0.117, 0.8)
        dark_green = (0.237, 0.512, 0.17, 0.5)

        if self.lastMove.flag in (KING_CASTLE, QUEEN_CASTLE):
            ksq0 = last_board.board.kings[last_board.color]
            ksq1 = show_board.board.kings[last_board.color]
            wildcastle = Cord(last_board.board.ini_kings[last_board.color]).x == 3 and \
                last_board.variant in (WILDCASTLECHESS, WILDCASTLESHUFFLECHESS)
            if self.lastMove.flag == KING_CASTLE:
                side = 0 if wildcastle else 1
                rsq0 = show_board.board.ini_rooks[last_board.color][side]
                rsq1 = show_board.board.fin_rooks[last_board.color][side]
            else:
                side = 1 if wildcastle else 0
                rsq0 = show_board.board.ini_rooks[last_board.color][side]
                rsq1 = show_board.board.fin_rooks[last_board.color][side]
            cord_pairs = [[Cord(ksq0), Cord(ksq1)], [Cord(rsq0), Cord(rsq1)]]
        else:
            cord_pairs = [[self.lastMove.cord0, self.lastMove.cord1]]

        for [cord0, cord1] in cord_pairs:
            if cord0 is not None:
                rel = self.cord2RectRelative(cord0)
                if intersects(rect(rel), redrawn):
                    rectangle = self.cord2Rect(cord0)
                    for scaler in matrix_scaler:
                        context.move_to(
                            rectangle[0] + (dic0[scaler[0]] + mark_width * scaler[0]) * rectangle[2],
                            rectangle[1] + (dic0[scaler[1]] + mark_width * scaler[1]) * rectangle[2])
                        context.rel_line_to(
                            0, -mark_width * rectangle[2] * scaler[1])
                        context.rel_curve_to(0, mark_width * rectangle[2] * scaler[1] / 2.0,
                                             -mark_width * rectangle[2] * scaler[0] / 2.0,
                                             mark_width * rectangle[2] * scaler[1],
                                             -mark_width * rectangle[2] * scaler[0],
                                             mark_width * rectangle[2] * scaler[1])
                        context.close_path()

                    context.set_source_rgba(*light_yellow)
                    context.fill_preserve()
                    context.set_source_rgba(*dark_yellow)
                    context.stroke()

            rel = self.cord2RectRelative(cord1)
            if intersects(rect(rel), redrawn):
                rectangle = self.cord2Rect(cord1)

                for scaler in matrix_scaler:
                    context.move_to(
                        rectangle[0] + dic1[scaler[0]] * rectangle[2],
                        rectangle[1] + dic1[scaler[1]] * rectangle[2])
                    context.rel_line_to(
                        mark_width * rectangle[2] * scaler[0], 0)
                    context.rel_curve_to(
                        -mark_width * rectangle[2] * scaler[0] / 2.0, 0,
                        -mark_width * rectangle[2] * scaler[0], mark_width * rectangle[2] * scaler[1] / 2.0,
                        -mark_width * rectangle[2] * scaler[0], mark_width * rectangle[2] * scaler[1])
                    context.close_path()

                if capture:
                    context.set_source_rgba(*light_orange)
                    context.fill_preserve()
                    context.set_source_rgba(*dark_orange)
                    context.stroke()
                elif cord0 is None:  # DROP move
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

        lvx = cords[1].x - cords[0].x
        lvy = cords[0].y - cords[1].y
        hypotenuse = float((lvx**2 + lvy**2)**.5)
        vec_x = lvx / hypotenuse
        vec_y = lvy / hypotenuse
        v1x = -vec_y
        v1y = vec_x

        rectangle = self.cord2Rect(cords[0])

        px_loc = rectangle[0] + rectangle[2] / 2.0
        py_loc = rectangle[1] + rectangle[2] / 2.0
        ax_loc = v1x * rectangle[2] * aw / 2
        ay_loc = v1y * rectangle[2] * aw / 2
        context.move_to(px_loc + ax_loc, py_loc + ay_loc)

        p1x = px_loc + (lvx - vec_x * ahh) * rectangle[2]
        p1y = py_loc + (lvy - vec_y * ahh) * rectangle[2]
        context.line_to(p1x + ax_loc, p1y + ay_loc)

        lax = v1x * rectangle[2] * ahw / 2
        lay = v1y * rectangle[2] * ahw / 2
        context.line_to(p1x + lax, p1y + lay)

        context.line_to(px_loc + lvx * rectangle[2], py_loc + lvy * rectangle[2])
        context.line_to(p1x - lax, p1y - lay)
        context.line_to(p1x - ax_loc, p1y - ay_loc)
        context.line_to(px_loc - ax_loc, py_loc - ay_loc)
        context.close_path()

        context.set_source_rgba(*fillc)
        context.fill_preserve()
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        context.set_line_width(asw * rectangle[2])
        context.set_source_rgba(*strkc)
        context.stroke()

        context.restore()

    def drawArrows(self, context):
        arw = 0.3  # Arrow width
        arhw = 0.72  # Arrow head width
        arhh = 0.64  # Arrow head height
        arsw = 0.08  # Arrow stroke width

        if self.bluearrow:
            self.__drawArrow(context, self.bluearrow, arw, arhw, arhh, arsw,
                             (.447, .624, .812, 0.9), (.204, .396, .643, 1))

        if self.greenarrow:
            self.__drawArrow(context, self.greenarrow, arw, arhw, arhh, arsw,
                             (.54, .886, .2, 0.9), (.306, .604, .024, 1))

        if self.redarrow:
            self.__drawArrow(context, self.redarrow, arw, arhw, arhh, arsw,
                             (.937, .16, .16, 0.9), (.643, 0, 0, 1))

    ###############################
    #        drawEnpassant        #
    ###############################

    def drawEnpassant(self, context, redrawn):
        if not self.showEnpassant:
            return
        enpassant = self.model.boards[-1].enpassant
        if not enpassant:
            return

        context.set_source_rgb(0, 0, 0)
        side = self.square[3]
        x_loc, y_loc = self.cord2Point(enpassant)
        if not intersects(rect((x_loc, y_loc, side, side)), redrawn):
            return

        x_loc, y_loc = self.cord2Point(enpassant)
        crr = context
        crr.set_font_size(side / 2.)
        fdescent, fheight = crr.font_extents()[1], crr.font_extents()[2]
        chars = "en"
        xbearing, width = crr.text_extents(chars)[0], crr.text_extents(chars)[2]
        crr.move_to(x_loc + side / 2. - xbearing - width / 2.0 - 1,
                    side / 2. + y_loc - fdescent + fheight / 2.)
        crr.show_text(chars)

    ###############################
    #          drawCross          #
    ###############################

    def drawCross(self, context, redrawn):
        xc_loc, yc_loc, square, side = self.square

        context.move_to(xc_loc, yc_loc)
        context.rel_line_to(square, square)
        context.move_to(xc_loc + square, yc_loc)
        context.rel_line_to(-square, square)

        context.set_line_cap(cairo.LINE_CAP_SQUARE)
        context.set_source_rgba(0, 0, 0, 0.65)
        context.set_line_width(side)
        context.stroke_preserve()

        context.set_source_rgba(1, 0, 0, 0.8)
        context.set_line_width(side / 2.)
        context.stroke()

    ############################################################################
    #                                Attributes                                #
    ############################################################################

    ###############################
    #          Cord vars          #
    ###############################

    def _setSelected(self, cord):
        self._active = None
        if self._selected == cord:
            return
        if self._selected:
            rectangle = rect(self.cord2RectRelative(self._selected))
            if cord:
                rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        elif cord:
            rectangle = rect(self.cord2RectRelative(cord))
        self._selected = cord
        self.redrawCanvas(rectangle)

    def _getSelected(self):
        return self._selected
    selected = property(_getSelected, _setSelected)

    def _setHover(self, cord):
        if self._hover == cord:
            return
        if self._hover:
            rectangle = rect(self.cord2RectRelative(self._hover))
            # convert r from tuple to rect
            # tmpr = r
            # r = Gdk.Rectangle()
            # r.x, r.y, r.width, r.height = tmpr
            # if cord: r = r.union(rect(self.cord2RectRelative(cord)))
            if cord:
                rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        elif cord:
            rectangle = rect(self.cord2RectRelative(cord))
            # convert r from tuple to rect
            # tmpr = r
            # r = Gdk.Rectangle()
            # r.x, r.y, r.width, r.height = tmpr
        self._hover = cord
        self.redrawCanvas(rectangle)

    def _getHover(self):
        return self._hover
    hover = property(_getHover, _setHover)

    def _setActive(self, cord):
        if self._active == cord:
            return
        if self._active:
            rectangle = rect(self.cord2RectRelative(self._active))
            if cord:
                rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        elif cord:
            rectangle = rect(self.cord2RectRelative(cord))
        self._active = cord
        self.redrawCanvas(rectangle)

    def _getActive(self):
        return self._active
    active = property(_getActive, _setActive)

    def _setPremove0(self, cord):
        if self._premove0 == cord:
            return
        if self._premove0:
            rectangle = rect(self.cord2RectRelative(self._premove0))
            if cord:
                rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        elif cord:
            rectangle = rect(self.cord2RectRelative(cord))
        self._premove0 = cord
        self.redrawCanvas(rectangle)

    def _getPremove0(self):
        return self._premove0
    premove0 = property(_getPremove0, _setPremove0)

    def _setPremove1(self, cord):
        if self._premove1 == cord:
            return
        if self._premove1:
            rectangle = rect(self.cord2RectRelative(self._premove1))
            if cord:
                rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        elif cord:
            rectangle = rect(self.cord2RectRelative(cord))
        self._premove1 = cord
        self.redrawCanvas(rectangle)

    def _getPremove1(self):
        return self._premove1
    premove1 = property(_getPremove1, _setPremove1)

    ################################
    #          Arrow vars          #
    ################################

    def _setRedarrow(self, cords):
        if cords == self._redarrow:
            return
        paint_cords = []
        if cords:
            paint_cords += cords
        if self._redarrow:
            paint_cords += self._redarrow
        rectangle = rect(self.cord2RectRelative(paint_cords[0]))
        for cord in paint_cords[1:]:
            rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        self._redarrow = cords
        self.redrawCanvas(rectangle)

    def _getRedarrow(self):
        return self._redarrow
    redarrow = property(_getRedarrow, _setRedarrow)

    def _setGreenarrow(self, cords):
        if cords == self._greenarrow:
            return
        paint_cords = []
        if cords:
            paint_cords += cords
        if self._greenarrow:
            paint_cords += self._greenarrow
        rectangle = rect(self.cord2RectRelative(paint_cords[0]))
        for cord in paint_cords[1:]:
            rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        self._greenarrow = cords
        self.redrawCanvas(rectangle)

    def _getGreenarrow(self):
        return self._greenarrow
    greenarrow = property(_getGreenarrow, _setGreenarrow)

    def _setBluearrow(self, cords):
        if cords == self._bluearrow:
            return
        paint_cords = []
        if cords:
            paint_cords += cords
        if self._bluearrow:
            paint_cords += self._bluearrow
        rectangle = rect(self.cord2RectRelative(paint_cords[0]))
        for cord in paint_cords[1:]:
            rectangle = union(rectangle, rect(self.cord2RectRelative(cord)))
        self._bluearrow = cords
        self.redrawCanvas(rectangle)

    def _getBluearrow(self):
        return self._bluearrow
    bluearrow = property(_getBluearrow, _setBluearrow)

    ################################
    #          Other vars          #
    ################################

    def _setRotation(self, radians):
        if not conf.get("fullAnimation"):
            self._rotation = radians
            self.next_rotation = radians
            self.matrix = cairo.Matrix.init_rotate(radians)
            self.redrawCanvas()
        else:
            if hasattr(self, "next_rotation") and \
                    self.next_rotation != self.rotation:
                return
            self.next_rotation = radians
            oldr = self.rotation
            start = time()

            def rotate():
                amount = (time() - start) / ANIMATION_TIME
                if amount > 1:
                    amount = 1
                    next = False
                    self.animating = False
                else:
                    next = True
                self._rotation = new = oldr + amount * (radians - oldr)
                self.matrix = cairo.Matrix.init_rotate(new)
                self.redrawCanvas()
                return next

            self.animating = True
            GLib.idle_add(rotate)

    def _getRotation(self):
        return self._rotation
    rotation = property(_getRotation, _setRotation)

    def _setDrawGrid(self, draw_grid):
        self._draw_grid = draw_grid
        self.redrawCanvas()

    def _getDrawGrid(self):
        return self._draw_grid
    draw_grid = property(_getDrawGrid, _setDrawGrid)

    def _setShowCords(self, show_cords):
        if not show_cords and self.no_frame:
            self.padding = 0.
        else:
            self.padding = self.pad
        self._show_cords = show_cords
        self.redrawCanvas()

    def _getShowCords(self):
        return self._show_cords
    show_cords = property(_getShowCords, _setShowCords)

    def _setShowCaptured(self, show_captured, force_restore=False):
        self._show_captured = show_captured or self.model.variant.variant in DROP_VARIANTS

        alloc = self.get_allocation()
        size = alloc.height / self.RANKS

        persp = perspective_manager.get_perspective("games")
        if self._show_captured:
            needed_width = size * (self.FILES + self.FILES_FOR_HOLDING) + self.padding * 2
            if alloc.width < needed_width:
                persp.adjust_divider(needed_width - alloc.width)
        elif force_restore:
            needed_width = size * self.FILES + self.padding * 2
            if alloc.width > needed_width:
                persp.adjust_divider(needed_width - alloc.width)

        self.redrawCanvas()

    def _getShowCaptured(self):
        return False if self.preview else self._show_captured
    showCaptured = property(_getShowCaptured, _setShowCaptured)

    def _setShowEnpassant(self, show_enpassant):
        if self._show_enpassant == show_enpassant:
            return
        if self.model:
            enpascord = self.model.boards[-1].enpassant
            if enpascord:
                rectangle = rect(self.cord2RectRelative(enpascord))
                self.redrawCanvas(rectangle)
        self._show_enpassant = show_enpassant

    def _getShowEnpassant(self):
        return self._show_enpassant
    showEnpassant = property(_getShowEnpassant, _setShowEnpassant)

    ###########################
    #          Other          #
    ###########################

    def cord2Rect(self, cord, y_loc=None):
        if y_loc is None:
            x_loc, y_loc = cord.x, cord.y
        else:
            x_loc = cord
        xc_loc, yc_loc, side = self.square[0], self.square[1], self.square[3]
        return ((xc_loc + (x_loc * side)), (yc_loc + (self.RANKS - 1 - y_loc) * side), side)

    def cord2Point(self, cord, y_loc=None):
        point = self.cord2Rect(cord, y_loc)
        return point[:2]

    def cord2RectRelative(self, cord, y_loc=None):
        """ Like cord2Rect, but gives you bounding rect in case board is beeing
            Rotated """
        if isinstance(cord, tuple):
            cx_loc, cy_loc, square = cord
        else:
            cx_loc, cy_loc, square = self.cord2Rect(cord, y_loc)
        x_zero, y_zero = self.matrix.transform_point(cx_loc, cy_loc)
        x_one, y_one = self.matrix.transform_point(cx_loc + square, cy_loc)
        x_two, y_two = self.matrix.transform_point(cx_loc, cy_loc + square)
        x_three, y_three = self.matrix.transform_point(cx_loc + square, cy_loc + square)
        x_loc = min(x_zero, x_one, x_two, x_three)
        y_loc = min(y_zero, y_one, y_two, y_three)
        square = max(y_zero, y_one, y_two, y_three) - y_loc
        return (x_loc, y_loc, square)

    def isLight(self, cord):
        """ Description: Given a board co-ordinate it returns True
            if the square at that co-ordinate is light
            Return : Boolean
        """
        if self.model.variant.variant in ASEAN_VARIANTS:
            return False
        x_loc, y_loc = cord.cords
        return (x_loc % 2 + y_loc % 2) == 1

    def showFirst(self):
        if self.model.examined and self.model.noTD:
            self.model.goFirst()
        else:
            self.shown = self.model.lowply
            self.shown_variation_idx = 0

    def showPrev(self, step=1):
        # If prev board belongs to a higher level variation
        # we have to update shown_variation_idx
        old_variation_idx = None
        if not self.shownIsMainLine():
            board = self.model.getBoardAtPly(self.shown - step, self.shown_variation_idx)
            for vari in self.model.variations:
                if board in vari:
                    break
            # swich to the new variation
            old_variation_idx = self.shown_variation_idx
            self.shown_variation_idx = self.model.variations.index(vari)

        if self.model.examined and self.model.noTD:
            self.model.goPrev(step)
        else:
            if self.shown > self.model.lowply:
                if self.shown - step > self.model.lowply:
                    self._setShown(self.shown - step, old_variation_idx)
                else:
                    self._setShown(self.model.lowply, old_variation_idx)

    def showNext(self, step=1):
        if self.model.examined and self.model.noTD:
            self.model.goNext(step)
        else:
            maxply = self.model.variations[self.shown_variation_idx][-1].ply
            if self.shown < maxply:
                if self.shown + step < maxply:
                    self.shown += step
                else:
                    self.shown = maxply

    def showLast(self):
        if self.model.examined and self.model.noTD:
            self.model.goLast()
        else:
            maxply = self.model.variations[self.shown_variation_idx][-1].ply
            self.shown = maxply

    def backToMainLine(self):
        if self.model.examined and self.model.noTD:
            self.model.backToMainLine()
        else:
            while not self.shownIsMainLine():
                self.showPrev()

    def backToParentLine(self):
        if self.model.examined and self.model.noTD:
            self.model.backToMainLine()
        else:
            varline = self.shown_variation_idx
            while True:
                self.showPrev()
                if self.shownIsMainLine() or self.shown_variation_idx != varline:
                    break

    def setPremove(self, premove_piece, premove0, premove1, premove_ply, promotion=None):
        self.premove_piece = premove_piece
        self.premove0 = premove0
        self.premove1 = premove1
        self.premove_ply = premove_ply
        self.premove_promotion = promotion

    def copy_pgn(self):
        output = StringIO()
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(pgn.save(output, self.model), -1)

    def copy_fen(self):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        fen = self.model.getBoardAtPly(self.shown, self.shown_variation_idx).asFen()
        clipboard.set_text(fen, -1)
