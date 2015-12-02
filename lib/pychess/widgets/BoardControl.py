# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from __future__ import print_function

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

import threading

from pychess.System.prefix import addDataPrefix
from pychess.System.Log import log
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move, parseAny, toAN
from pychess.Utils.const import *
from pychess.Utils.logic import validate
from pychess.Utils.lutils import lmove
from pychess.Utils.lutils import lmovegen

from . import preferencesDialog
from .PromotionDialog import PromotionDialog
from .BoardView import BoardView, rect
from .BoardView import join


class BoardControl (Gtk.EventBox):
    """ Creates a BoardView for GameModel to control move selection,
        action menu selection and emits signals to let Human player
        make moves and emit offers.
        SetuPositionDialog uses setup_position=True to disable most validation.
    """
    
    __gsignals__ = {
        'piece_moved' : (GObject.SignalFlags.RUN_FIRST, None, (object, int)),
        'action' : (GObject.SignalFlags.RUN_FIRST, None, (str, object))
    }
    
    def __init__(self, gamemodel, actionMenuItems, setup_position=False):
        GObject.GObject.__init__(self)
        self.setup_position = setup_position
        self.view = BoardView(gamemodel, setup_position=setup_position)
        self.add(self.view)
        self.variant = gamemodel.variant
        self.promotionDialog = PromotionDialog(self.variant.variant)

        self.RANKS = gamemodel.boards[0].RANKS
        self.FILES = gamemodel.boards[0].FILES
        
        self.actionMenuItems = actionMenuItems
        self.connections = {}
        for key, menuitem in self.actionMenuItems.items():
            if menuitem == None: print(key)
            self.connections[menuitem] = menuitem.connect("activate", self.actionActivate, key)
        
        self.view.connect("shown_changed", self.shown_changed)
        gamemodel.connect("moves_undoing", self.moves_undone)
        gamemodel.connect("game_ended", self.game_ended)
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK|Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)
        
        self.selected_last = None
        self.stateLock = threading.Lock()
        self.normalState = NormalState(self)
        self.selectedState = SelectedState(self)
        self.activeState = ActiveState(self)
        self.lockedNormalState = LockedNormalState(self)
        self.lockedSelectedState = LockedSelectedState(self)
        self.lockedActiveState = LockedActiveState(self)
        self.currentState = self.normalState
        
        self.lockedPly = self.view.shown
        self.possibleBoards = {
            self.lockedPly : self._genPossibleBoards(self.lockedPly) }
        
        self.allowPremove = False
        def onGameStart (gamemodel):
            if not self.setup_position:
                for player in gamemodel.players:
                    if player.__type__ == LOCAL:
                        self.allowPremove = True
        gamemodel.connect("game_started", onGameStart)
        self.keybuffer = ""
        
    def _del (self):
        for menu, conid in self.connections.items():
            menu.disconnect(conid)
        self.connections = {}

    def getPromotion(self):
        color = self.view.model.boards[-1].color
        variant = self.view.model.boards[-1].variant
        promotion = None
        promotion = self.promotionDialog.runAndHide(color, variant)
        return promotion
        
    def emit_move_signal (self, cord0, cord1, promotion=None):
        # Game end can change cord0 to None while dragging a piece
        if cord0 is None:
            return
        color = self.view.model.boards[-1].color
        board = self.view.model.getBoardAtPly(self.view.shown, self.view.shownVariationIdx)
        # Ask player for which piece to promote into. If this move does not
        # include a promotion, QUEEN will be sent as a dummy value, but not used
        if promotion is None and board[cord0].sign == PAWN and cord1.cord in board.PROMOTION_ZONE[color]:
            if self.variant.variant == SITTUYINCHESS:
                # no promotion allowed if we have queen
                if board.board.boards[color][QUEEN]:
                    promotion = None
                else:
                    # promotion is always optional
                    promotion = self.getPromotion()
                    if promotion is None and cord0 == cord1:
                        # if don't want in place promotion
                        return
            elif len(self.variant.PROMOTIONS) == 1:
                promotion = lmove.PROMOTE_PIECE(self.variant.PROMOTIONS[0])
            else:
                promotion = self.getPromotion()
                if promotion is None:
                    # Put back pawn moved be d'n'd
                    self.view.runAnimation(redrawMisc = False)
                    return
        if cord0.x < 0 or cord0.x > self.FILES-1:
            move = Move(lmovegen.newMove(board[cord0].piece, cord1.cord, DROP))
        else:
            move = Move(cord0, cord1, board, promotion)
        
        if (self.view.model.curplayer.__type__ == LOCAL or self.view.model.examined) and \
            self.view.shownIsMainLine() and \
            self.view.model.boards[-1] == board and \
            self.view.model.status == RUNNING:
            if self.setup_position:
                self.emit("piece_moved", (cord0, cord1), board[cord0].color)
            else:
                self.emit("piece_moved", move, color)
                if self.view.model.examined:
                    self.view.model.connection.bm.sendMove(toAN (board, move))
        else:
            if board.board.next is None and not self.view.shownIsMainLine():
                self.view.model.add_move2variation(board, move, self.view.shownVariationIdx)
                self.view.shown += 1
            else:
                new_vari = self.view.model.add_variation(board, (move,))
                self.view.setShownBoard(new_vari[-1])
    
    def actionActivate (self, widget, key):
        """ Put actions from a menu or similar """
        if key == "call_flag":
            self.emit("action", FLAG_CALL, None)
        elif key == "abort":
            self.emit("action", ABORT_OFFER, None)
        elif key == "adjourn":
            self.emit("action", ADJOURN_OFFER, None)
        elif key == "draw":
            self.emit("action", DRAW_OFFER, None)
        elif key == "resign":
            self.emit("action", RESIGNATION, None)
        elif key == "ask_to_move":
            self.emit("action", HURRY_ACTION, None)
        elif key == "undo1":
            curplayer = self.view.model.curplayer
            waitingplayer = self.view.model.waitingplayer
            if curplayer.__type__ == LOCAL \
                and (waitingplayer.__type__ == ARTIFICIAL or \
                     self.view.model.isPlayingICSGame()) \
                and self.view.model.ply - self.view.model.lowply > 1:
                self.emit("action", TAKEBACK_OFFER, self.view.model.ply-2)
            else:
                self.emit("action", TAKEBACK_OFFER, self.view.model.ply-1)
        elif key == "pause1":
            self.emit("action", PAUSE_OFFER, None)
        elif key == "resume1":
            self.emit("action", RESUME_OFFER, None)
    
    def shown_changed (self, view, shown):
        def do_shown_changed():
            self.lockedPly = self.view.shown
            self.possibleBoards[self.lockedPly] = self._genPossibleBoards(self.lockedPly)
            if self.view.shown-2 in self.possibleBoards:
                del self.possibleBoards[self.view.shown-2]
        GLib.idle_add(do_shown_changed)
        
    def moves_undone (self, gamemodel, moves):
        self.stateLock.acquire()
        try:
            self.view.selected = None
            self.view.active = None
            self.view.hover = None
            self.view.draggedPiece = None
            self.view.setPremove(None, None, None, None)
            self.currentState = self.lockedNormalState
        finally:
            self.stateLock.release()
    
    def game_ended (self, gamemodel, reason):
        self.stateLock.acquire()
        try:
            self.selected_last = None
            self.view.selected = None
            self.view.active = None
            self.view.hover = None
            self.view.draggedPiece = None
            self.view.setPremove(None, None, None, None)
            self.currentState = self.normalState
        finally:
            self.stateLock.release()

        self.view.startAnimation()

    def getBoard (self):
        return self.view.model.getBoardAtPly(self.view.shown, self.view.shownVariationIdx)

    def isLastPlayed(self, board):
        return board == self.view.model.boards[-1]
    
    def setLocked (self, locked):
        do_animation = False
        
        self.stateLock.acquire()
        try:
            if locked and self.isLastPlayed(self.getBoard()) and \
                    self.view.model.status == RUNNING:
                if self.view.model.status != RUNNING:
                    self.view.selected = None
                    self.view.active = None
                    self.view.hover = None
                    self.view.draggedPiece = None
                    do_animation = True

                if self.currentState == self.selectedState:
                    self.currentState = self.lockedSelectedState
                elif self.currentState == self.activeState:
                    self.currentState = self.lockedActiveState
                else:
                    self.currentState = self.lockedNormalState
            else:
                if self.currentState == self.lockedSelectedState:
                    self.currentState = self.selectedState
                elif self.currentState == self.lockedActiveState:
                    self.currentState = self.activeState
                else:
                    self.currentState = self.normalState
        finally:
            self.stateLock.release()
        
        if do_animation:
            self.view.startAnimation()
    
    def setStateSelected (self):
        self.stateLock.acquire()
        try:
            if self.currentState in (self.lockedNormalState, self.lockedSelectedState,
                                     self.lockedActiveState):
                self.currentState = self.lockedSelectedState
            else:
                self.view.setPremove(None, None, None, None)
                self.currentState = self.selectedState
        finally:
            self.stateLock.release()
    
    def setStateActive (self):
        self.stateLock.acquire()
        try:
            if self.currentState in (self.lockedNormalState, self.lockedSelectedState,
                                     self.lockedActiveState):
                self.currentState = self.lockedActiveState
            else:
                self.view.setPremove(None, None, None, None)
                self.currentState = self.activeState
        finally:
            self.stateLock.release()
    
    def setStateNormal (self):
        self.stateLock.acquire()
        try:
            if self.currentState in (self.lockedNormalState, self.lockedSelectedState,
                                     self.lockedActiveState):
                self.currentState = self.lockedNormalState
            else:
                self.view.setPremove(None, None, None, None)
                self.currentState = self.normalState
        finally:
            self.stateLock.release()
    
    def button_press (self, widget, event):
        return self.currentState.press(event.x, event.y, event.button)
    
    def button_release (self, widget, event):
        return self.currentState.release(event.x, event.y)
    
    def motion_notify (self, widget, event):
        return self.currentState.motion(event.x, event.y)
    
    def leave_notify (self, widget, event):
        return self.currentState.leave(event.x, event.y)

    def key_pressed (self, keyname):
        if keyname in "PNBRQKMFSOox12345678abcdefgh":
            self.keybuffer += keyname
        elif keyname == "minus":
            self.keybuffer += "-"
        elif keyname == "at":
            self.keybuffer += "@"
        elif keyname == "equal":
            self.keybuffer += "="
        elif keyname == "Return":
            color = self.view.model.boards[-1].color
            board = self.view.model.getBoardAtPly(self.view.shown, self.view.shownVariationIdx)
            try:
                move = parseAny(board, self.keybuffer)
            except:
                self.keybuffer = ""
                return
            if validate(board, move):
                if self.view.shownIsMainLine() and self.view.model.boards[-1] == board:
                    self.emit("piece_moved", move, color)
                else:
                    if board.board.next is None and not self.view.shownIsMainLine():
                        self.view.model.add_move2variation(board, move, self.view.shownVariationIdx)
                        self.view.shown += 1
                    else:
                        new_vari = self.view.model.add_variation(board, (move,))
                        self.view.setShownBoard(new_vari[-1])
            self.keybuffer = ""
        elif keyname == "BackSpace":
            self.keybuffer = self.keybuffer[:-1] if self.keybuffer else ""

    def _genPossibleBoards(self, ply):
        possibleBoards = []
        if self.setup_position:
            return possibleBoards
        if len(self.view.model.players) == 2 and self.view.model.isEngine2EngineGame():
            return possibleBoards
        curboard = self.view.model.getBoardAtPly(ply, self.view.shownVariationIdx)
        for lmove in lmovegen.genAllMoves(curboard.board.clone()):
            move = Move(lmove)
            board = curboard.move(move)
            possibleBoards.append(board)
        return possibleBoards

class BoardState:
    '''
    There are 6 total BoardStates:
    NormalState, ActiveState, SelectedState
    LockedNormalState, LockedActiveState, LockedSelectedState

    The board state is Locked while it is the opponents turn.
    The board state is not Locked during your turn.
    (Locked states are not used when BoardControl setup_position is True.)

    Normal/Locked State - No pieces or cords are selected
    Active State - A piece is currently being dragged by the mouse
    Selected State - A cord is currently selected
    '''
    def __init__ (self, board):
        self.parent = board
        self.view = board.view
        self.lastMotionCord = None

        self.RANKS = self.view.model.boards[0].RANKS
        self.FILES = self.view.model.boards[0].FILES
    
    def getBoard (self):
        return self.view.model.getBoardAtPly(self.view.shown, self.view.shownVariationIdx)
    
    def validate (self, cord0, cord1):
        if cord0 is None or cord1 is None:
            return False
        # prevent accidental NULL_MOVE creation
        if cord0 == cord1:
            return False
        if self.getBoard()[cord0] == None:
            return False

        if self.parent.setup_position:
            to_piece = self.getBoard()[cord1]
            # prevent moving pieces inside holding
            if (cord0.x < 0 or cord0.x > self.FILES-1) and \
                (cord1.x < 0 or cord1.x > self.FILES-1):
                return False
            # prevent moving kings off board
            elif self.getBoard()[cord0].piece == KING and \
                (cord1.x < 0 or cord1.x > self.FILES-1):
                return False
            # prevent taking enemy king
            elif to_piece is not None and to_piece.piece == KING:
                return False
            else:
                return True
        
        if cord1.x < 0 or cord1.x > self.FILES-1:
            return False
        if cord0.x < 0 or cord0.x > self.FILES-1:
            # drop
            return validate(self.getBoard(), Move(lmovegen.newMove(self.getBoard()[cord0].piece, cord1.cord, DROP)))
        else:
            return validate(self.getBoard(), Move(cord0, cord1, self.getBoard()))
    
    def transPoint (self, x, y):
        xc, yc, square, s = self.view.square
        x, y = self.view.invmatrix.transform_point(x,y)
        y -= yc; x -= xc
        
        y /= float(s)
        x /= float(s)
        return x, self.RANKS-y
    
    def point2Cord (self, x, y):
        point = self.transPoint(x, y)
        p0, p1 = point[0], point[1]
        if self.parent.variant.variant in DROP_VARIANTS:
            if not -3 <= int(p0) <= self.FILES+2 or not 0 <= int(p1) <= self.RANKS-1:
                return None
        else:
            if not 0 <= int(p0) <= self.FILES-1 or not 0 <= int(p1) <= self.RANKS-1:
                return None
        return Cord(int(p0) if p0>= 0 else int(p0)-1, int(p1))
    
    def isSelectable (self, cord):
        # Simple isSelectable method, disabling selecting cords out of bound etc
        if not cord:
            return False
        if self.parent.setup_position:
            return True
        if self.parent.variant.variant in DROP_VARIANTS:
            if (not -3 <= cord.x <= self.FILES+2) or (not 0 <= cord.y <= self.RANKS-1):
                return False
        else:
            if (not 0 <= cord.x <= self.FILES-1) or (not 0 <= cord.y <= self.RANKS-1):
                return False
        return True
    
    def press (self, x, y, button):
        pass
    
    def release (self, x, y):
        pass
    
    def motion (self, x, y):
        cord = self.point2Cord(x, y)
        if self.lastMotionCord == cord:
            return
        self.lastMotionCord = cord
        if cord and self.isSelectable(cord):
            if not self.view.model.isPlayingICSGame():
                self.view.hover = cord
        else: self.view.hover = None
    
    def leave (self, x, y):
        a = self.parent.get_allocation()
        if not (0 <= x < a.width and 0 <= y < a.height):
            self.view.hover = None

class LockedBoardState (BoardState):
    '''
    Parent of LockedNormalState, LockedActiveState, LockedSelectedState

    The board is in one of the three Locked states during the opponent's turn.
    '''
    def __init__ (self, board):
        BoardState.__init__(self, board)
    
    def isAPotentiallyLegalNextMove (self, cord0, cord1):
        """ Determines whether the given move is at all legally possible
            as the next move after the player who's turn it is makes their move
            Note: This doesn't always return the correct value, such as when 
            BoardControl.setLocked() has been called and we've begun a drag,
            but view.shown and BoardControl.lockedPly haven't been updated yet """
        if cord0 == None or cord1 == None:
            return False
        if not self.parent.lockedPly in self.parent.possibleBoards:
            return False
        for board in self.parent.possibleBoards[self.parent.lockedPly]:
            if not board[cord0]:
                return False
            if validate(board, Move(cord0, cord1, board)):
                return True
        return False


class NormalState (BoardState):
    '''
    It is the human player's turn and no pieces or cords are selected.
    '''
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        if self.parent.setup_position:
            return True
        try:
            board = self.getBoard()
            if board[cord] == None:
                return False # We don't want empty cords
            elif board[cord].color != board.color:
                return False # We shouldn't be able to select an opponent piece
        except IndexError:
            return False
        return True
    
    def press (self, x, y, button):
        self.parent.grab_focus()
        cord = self.point2Cord(x,y)
        if self.isSelectable(cord):
            self.view.draggedPiece = self.getBoard()[cord]
            self.view.active = cord
            self.parent.setStateActive()

class ActiveState (BoardState):
    '''
    It is the human player's turn and a piece is being dragged by the mouse.
    '''
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        if self.parent.setup_position:
            return True
        return self.validate(self.view.active, cord)
    
    def release (self, x, y):
        cord = self.point2Cord(x,y)
        if cord != self.view.active and not self.validate(self.view.selected, cord):
            if not self.parent.setup_position:
                preferencesDialog.SoundTab.playAction("invalidMove")
        if not cord:
            self.view.active = None
            self.view.selected = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateNormal()
        
        # When in the mixed active/selected state
        elif self.view.selected:
            # Move when releasing on a good cord
            if self.validate(self.view.selected, cord):
                self.parent.setStateNormal()
                # It is important to emit_move_signal after setting state
                # as listeners of the function probably will lock the board
                self.view.draggedPiece = None
                self.parent.emit_move_signal(self.view.selected, cord)
                if self.parent.setup_position:
                    if not (self.view.selected.x < 0 or self.view.selected.x > self.FILES-1):
                        self.view.selected = None
                    else:
                        # enable stamping with selected holding pieces
                        self.parent.setStateSelected()
                else:
                    self.view.selected = None
                self.view.active = None
            elif cord == self.view.active == self.view.selected == self.parent.selected_last:
                # user clicked (press+release) same piece twice, so unselect it
                self.view.active = None
                self.view.selected = None
                self.view.draggedPiece = None
                self.view.startAnimation()
                self.parent.setStateNormal()
            else:  # leave last selected piece selected
                self.view.active = None
                self.view.draggedPiece = None
                self.view.startAnimation()
                self.parent.setStateSelected()
        
        # If dragged and released on a possible cord
        elif self.validate(self.view.active, cord):
            self.parent.setStateNormal()
            self.view.draggedPiece = None
            # removig piece from board
            if self.parent.setup_position and \
                (cord.x < 0 or cord.x > self.FILES-1):
                self.view.startAnimation()
            self.parent.emit_move_signal(self.view.active, cord)
            self.view.active = None
        
        # Select last piece user tried to move or that was selected
        elif self.view.active or self.view.selected:
            self.view.selected = self.view.active if self.view.active else self.view.selected
            self.view.active = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateSelected()
        
        # Send back, if dragging to a not possible cord
        else:
            self.view.active = None
            # Send the piece back to its original cord
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateNormal()
        
        self.parent.selected_last = self.view.selected
    
    def motion (self, x, y):
        BoardState.motion(self, x, y)
        fcord = self.view.active
        if not fcord:
            return
        piece = self.getBoard()[fcord]
        if not piece:
            return
        elif  piece.color != self.getBoard().color:
            if not self.parent.setup_position:
                return
            
        xc, yc, square, s = self.view.square
        co, si = self.view.matrix[0], self.view.matrix[1]
        point = self.transPoint(x-s*(co+si)/2., y+s*(co-si)/2.)
        if not point: return
        x, y = point
        
        if piece.x != x or piece.y != y:
            if piece.x:
                paintBox = self.view.cord2RectRelative(piece.x, piece.y)
            else: paintBox = self.view.cord2RectRelative(self.view.active)
            paintBox = join(paintBox, self.view.cord2RectRelative(x, y))
            piece.x = x
            piece.y = y
            self.view.redraw_canvas(rect(paintBox))

class SelectedState (BoardState):
    '''
    It is the human player's turn and a cord is selected.
    '''
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        if self.parent.setup_position:
            return True
        try:
            board = self.getBoard()
            if board[cord] != None and board[cord].color == board.color:
                return True  # Select another piece
        except IndexError:
            return False
        return self.validate(self.view.selected, cord)
    
    def press (self, x, y, button):
        cord = self.point2Cord(x,y)
        # Unselecting by pressing the selected cord, or marking the cord to be 
        # moved to. We don't unset self.view.selected, so ActiveState can handle
        # things correctly
        if self.isSelectable(cord):
            if self.parent.setup_position:
                color_ok = True
            else:
                color_ok = self.getBoard()[cord] != None and \
                    self.getBoard()[cord].color == self.getBoard().color
            if self.view.selected and self.view.selected != cord and \
               color_ok and not self.validate(self.view.selected, cord):
                # corner case encountered:
                # user clicked (press+release) a piece, then clicked (no release yet)
                # a different piece and dragged it somewhere else. Since
                # ActiveState.release() will use self.view.selected as the source piece
                # rather than self.view.active, we need to update it here
                self.view.selected = cord   # re-select new cord
            
            self.view.draggedPiece = self.getBoard()[cord]
            self.view.active = cord
            self.parent.setStateActive()
        
        else:  # Unselecting by pressing an inactive cord
            self.view.selected = None
            self.parent.setStateNormal()
            if not self.parent.setup_position:
                preferencesDialog.SoundTab.playAction("invalidMove")
            
class LockedNormalState (LockedBoardState):
    '''
    It is the opponent's turn and no piece or cord is selected.
    '''
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        if not self.parent.allowPremove:
            return False # Don't allow premove if neither player is human
        try:
            board = self.getBoard()
            if board[cord] == None:
                return False # We don't want empty cords
            elif board[cord].color == board.color:
                return False # We shouldn't be able to select an opponent piece
        except IndexError:
            return False
        return True
    
    def press (self, x, y, button):
        self.parent.grab_focus()
        cord = self.point2Cord(x,y)
        if self.isSelectable(cord):
            self.view.draggedPiece = self.getBoard()[cord]
            self.view.active = cord
            self.parent.setStateActive()

        # reset premove if mouse right-clicks or clicks one of the premove cords
        if button == 3: #right-click
            self.view.setPremove(None, None, None, None)
            self.view.startAnimation()
        elif cord == self.view.premove0 or cord == self.view.premove1:
            self.view.setPremove(None, None, None, None)
            self.view.startAnimation()

class LockedActiveState (LockedBoardState):
    '''
    It is the opponent's turn and a piece is being dragged by the mouse.
    '''
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        return self.isAPotentiallyLegalNextMove(self.view.active, cord)

    def release (self, x, y):
        cord = self.point2Cord(x,y)
        if cord == self.view.active == self.view.selected == self.parent.selected_last:
            # User clicked (press+release) same piece twice, so unselect it
            self.view.active = None
            self.view.selected = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateNormal()
        elif self.parent.allowPremove and self.view.selected and self.isAPotentiallyLegalNextMove(self.view.selected, cord):
            # In mixed locked selected/active state and user selects a valid premove cord
            board = self.getBoard()
            if board[self.view.selected].sign == PAWN and cord.cord in board.PROMOTION_ZONE[1-board.color]:
                promotion = self.parent.getPromotion()
            else:
                promotion = None
            self.view.setPremove(board[self.view.selected], self.view.selected, cord, self.view.shown+2, promotion)
            self.view.selected = None
            self.view.active = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateNormal()
        elif self.parent.allowPremove and self.isAPotentiallyLegalNextMove(self.view.active, cord):
            # User drags a piece to a valid premove square
            board = self.getBoard()
            if board[self.view.active].sign == PAWN and cord.cord in board.PROMOTION_ZONE[1-board.color]:
                promotion = self.parent.getPromotion()
            else:
                promotion = None
            self.view.setPremove(self.getBoard()[self.view.active], self.view.active, cord, self.view.shown+2, promotion)
            self.view.selected = None
            self.view.active = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateNormal()
        elif self.view.active or self.view.selected:
            # Select last piece user tried to move or that was selected
            self.view.selected = self.view.active if self.view.active else self.view.selected
            self.view.active = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateSelected()
        else:
            self.view.active = None
            self.view.selected = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.parent.setStateNormal()

        self.parent.selected_last = self.view.selected
    
    def motion (self, x, y):
        BoardState.motion(self, x, y)
        fcord = self.view.active
        if not fcord:
            return
        piece = self.getBoard()[fcord]
        if not piece or piece.color == self.getBoard().color:
            return
        
        xc, yc, square, s = self.view.square
        co, si = self.view.matrix[0], self.view.matrix[1]
        point = self.transPoint(x-s*(co+si)/2., y+s*(co-si)/2.)
        if not point: return
        x, y = point

        if piece.x != x or piece.y != y:
            if piece.x:
                paintBox = self.view.cord2RectRelative(piece.x, piece.y)
            else: paintBox = self.view.cord2RectRelative(self.view.active)
            paintBox = join(paintBox, self.view.cord2RectRelative(x, y))
            piece.x = x
            piece.y = y
            self.view.redraw_canvas(rect(paintBox))

class LockedSelectedState (LockedBoardState):
    '''
    It is the opponent's turn and a cord is selected.
    '''
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        try:
            board = self.getBoard()
            if board[cord] != None and board[cord].color != board.color:
                return True # Select another piece
        except IndexError:
            return False
        return self.isAPotentiallyLegalNextMove(self.view.selected, cord)

    def motion (self, x, y):
        cord = self.point2Cord(x, y)
        if self.lastMotionCord == cord:
            self.view.hover = cord
            return
        self.lastMotionCord = cord
        if cord and self.isAPotentiallyLegalNextMove(self.view.selected, cord):
            if not self.view.model.isPlayingICSGame():
                self.view.hover = cord
        else: self.view.hover = None
    
    def press (self, x, y, button):
        cord = self.point2Cord(x,y)
        # Unselecting by pressing the selected cord, or marking the cord to be 
        # moved to. We don't unset self.view.selected, so ActiveState can handle
        # things correctly
        if self.isSelectable(cord):
            if self.view.selected and self.view.selected != cord and \
               self.getBoard()[cord] != None and \
               self.getBoard()[cord].color != self.getBoard().color and \
               not self.isAPotentiallyLegalNextMove(self.view.selected, cord):
                # corner-case encountered (see comment in SelectedState.press)
                self.view.selected = cord  # re-select new cord
            
            self.view.draggedPiece = self.getBoard()[cord]
            self.view.active = cord
            self.parent.setStateActive()
        
        else:  # Unselecting by pressing an inactive cord
            self.view.selected = None
            self.parent.setStateNormal()

        # reset premove if mouse right-clicks or clicks one of the premove cords
        if button == 3: #right-click
            self.view.setPremove(None, None, None, None)
            self.view.startAnimation()
        elif cord == self.view.premove0 or cord == self.view.premove1:
            self.view.setPremove(None, None, None, None)
            self.view.startAnimation()

