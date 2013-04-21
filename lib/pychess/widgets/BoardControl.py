# -*- coding: UTF-8 -*-

import gtk, gtk.gdk
from gobject import *
import threading

from pychess.System.prefix import addDataPrefix
from pychess.System.Log import log
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move, parseAny
from pychess.Utils.const import *
from pychess.Utils.logic import validate
from pychess.Utils.lutils import lmovegen
from pychess.Variants.crazyhouse import CrazyhouseChess

from PromotionDialog import PromotionDialog
from BoardView import BoardView, rect, HOLDING_SHIFT
from BoardView import join


class BoardControl (gtk.EventBox):
    
    __gsignals__ = {
        'piece_moved' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object, int)),
        'action' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str, object))
    }
    
    def __init__(self, gamemodel, actionMenuItems):
        gtk.EventBox.__init__(self)
        self.promotionDialog = PromotionDialog()
        self.view = BoardView(gamemodel)
        self.add(self.view)
        self.variant = gamemodel.variant

        self.RANKS = gamemodel.boards[0].RANKS
        self.FILES = gamemodel.boards[0].FILES
        
        self.actionMenuItems = actionMenuItems
        self.connections = {}
        for key, menuitem in self.actionMenuItems.iteritems():
            if menuitem == None: print key
            self.connections[menuitem] = menuitem.connect("activate", self.actionActivate, key)
        
        self.view.connect("shown_changed", self.shown_changed)
        gamemodel.connect("moves_undoing", self.moves_undone)
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK|gtk.gdk.POINTER_MOTION_MASK)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)
        
        self.selected_last = None
        self.stateLock = threading.Lock()
        self.normalState = NormalState(self)
        self.selectedState = SelectedState(self)
        self.activeState = ActiveState(self)
        self.lockedState = LockedState(self)
        self.lockedSelectedState = LockedSelectedState(self)
        self.lockedActiveState = LockedActiveState(self)
        self.currentState = self.lockedState
        
        self.lockedPly = self.view.shown
        self.possibleBoards = {
            self.lockedPly : self._genPossibleBoards(self.lockedPly) }
        
        self.allowPremove = False
        def onGameStart (gamemodel):
            for player in gamemodel.players:
                if player.__type__ == LOCAL:
                    self.allowPremove = True
        gamemodel.connect("game_started", onGameStart)
        self.keybuffer = ""
        
    def __del__ (self):
        for menu, conid in self.connections.iteritems():
            menu.disconnect(conid)
        self.connections = {}
        
    def emit_move_signal (self, cord0, cord1):
        color = self.view.model.boards[-1].color
        board = self.view.model.getBoardAtPly(self.view.shown, self.view.shownVariationIdx)
        # Ask player for which piece to promote into. If this move does not
        # include a promotion, QUEEN will be sent as a dummy value, but not used
        promotion = QUEEN
        if board[cord0].sign == PAWN and cord1.y in (0, self.RANKS-1):
            res = self.promotionDialog.runAndHide(color)
            if res != gtk.RESPONSE_DELETE_EVENT:
                promotion = res
            else:
                # Put back pawn moved be d'n'd
                self.view.runAnimation(redrawMisc = False)
                return
        
        if cord0.x < 0 or cord0.x > self.FILES-1:
            move = Move(lmovegen.newMove(board[cord0].piece, cord1.cord, DROP))
        else:
            move = Move(cord0, cord1, self.view.model.boards[-1], promotion)
        self.emit("piece_moved", move, color)
    
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
            curColor = self.view.model.variations[0][-1].color
            curPlayer = self.view.model.players[curColor]
            if curPlayer.__type__ == LOCAL and self.view.model.ply > 1:
                self.emit("action", TAKEBACK_OFFER, self.view.model.ply-2)
            else:
                self.emit("action", TAKEBACK_OFFER, self.view.model.ply-1)
        elif key == "pause1":
            self.emit("action", PAUSE_OFFER, None)
        elif key == "resume1":
            self.emit("action", RESUME_OFFER, None)
    
    def shown_changed (self, view, shown):
        self.lockedPly = self.view.shown
        self.possibleBoards[self.lockedPly] = self._genPossibleBoards(self.lockedPly)
        if self.view.shown-2 in self.possibleBoards:
            del self.possibleBoards[self.view.shown-2]
    
    def moves_undone (self, gamemodel, moves):
        self.stateLock.acquire()
        try:
            self.view.selected = None
            self.view.active = None
            self.view.hover = None
            self.view.draggedPiece = None
            self.view.startAnimation()
            self.currentState = self.lockedState
        finally:
            self.stateLock.release()
    
    def setLocked (self, locked):
        self.stateLock.acquire()
        try:
            if locked:
                if self.view.model.status != RUNNING:
                    self.view.selected = None
                    self.view.active = None
                    self.view.hover = None
                    self.view.draggedPiece = None
                    self.view.startAnimation()
                self.currentState = self.lockedState
            else:
                if self.currentState == self.lockedSelectedState:
                    self.currentState = self.selectedState
                elif self.currentState == self.lockedActiveState:
                    self.currentState = self.activeState
                else:
                    self.currentState = self.normalState
        finally:
            self.stateLock.release()
    
    def setStateSelected (self):
        self.stateLock.acquire()
        try:
            if self.currentState in (self.lockedState, self.lockedSelectedState,
                                     self.lockedActiveState):
                self.currentState = self.lockedSelectedState
            else:
                self.currentState = self.selectedState
        finally:
            self.stateLock.release()
    
    def setStateActive (self):
        self.stateLock.acquire()
        try:
            if self.currentState in (self.lockedState, self.lockedSelectedState,
                                     self.lockedActiveState):
                self.currentState = self.lockedActiveState
            else:
                self.currentState = self.activeState
        finally:
            self.stateLock.release()
    
    def setStateNormal (self):
        self.stateLock.acquire()
        try:
            if self.currentState in (self.lockedState, self.lockedSelectedState,
                                     self.lockedActiveState):
                self.currentState = self.lockedState
            else:
                self.currentState = self.normalState
        finally:
            self.stateLock.release()
    
    def button_press (self, widget, event):
        return self.currentState.press(event.x, event.y)
    
    def button_release (self, widget, event):
        return self.currentState.release(event.x, event.y)
    
    def motion_notify (self, widget, event):
        return self.currentState.motion(event.x, event.y)
    
    def leave_notify (self, widget, event):
        return self.currentState.leave(event.x, event.y)

    def key_pressed (self, keyname):
        if keyname in "PNBRQKOox-12345678abcdefgh":
            self.keybuffer += keyname
        elif keyname == "at":
            self.keybuffer += "@"
        elif keyname == "Return":
            color = self.view.model.boards[-1].color
            board = self.view.model.getBoardAtPly(self.view.shown, self.view.shownVariationIdx)
            try:
                move = parseAny(board, self.keybuffer)
            except:
                self.keybuffer = ""
                return
            if validate(board, move):
                if self.view.shownIsMainLine() and board.board.next is None:
                    self.emit("piece_moved", move, color)
                else:
                    if board.board.next is None:
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
        return possibleBoards
        curboard = self.view.model.getBoardAtPly(ply, self.view.shownVariationIdx)
        for lmove in lmovegen.genAllMoves(curboard.board):
            move = Move(lmove)
            board = curboard.move(move)
            possibleBoards.append(board)        
        return possibleBoards

class BoardState:
    def __init__ (self, board):
        self.parent = board
        self.view = board.view
        self.lastMotionCord = None

        self.RANKS = self.view.model.boards[0].RANKS
        self.FILES = self.view.model.boards[0].FILES
    
    def getBoard (self):
        return self.view.model.getBoardAtPly(self.view.shown, self.view.shownVariationIdx)
    
    def validate (self, cord0, cord1):
        assert cord0 != None and cord1 != None, "cord0: " + str(cord0) + ", cord1: " + str(cord1)
        if self.getBoard()[cord0] == None:
            return False
        if cord1.x < 0 or cord1.x > self.FILES-1:
            return False
        if cord0.x < 0 or cord0.x > self.FILES-1:
            # drop
            return validate(self.getBoard(), Move(lmovegen.newMove(self.getBoard()[cord0].piece, cord1.cord, DROP)))
        else:
            return validate(self.getBoard(), Move(cord0, cord1, self.getBoard()))
    
    def transPoint (self, x, y):
        if not self.view.square: return None
        xc, yc, square, s = self.view.square
        x, y = self.view.invmatrix.transform_point(x,y)
        y -= yc; x -= xc
        
        y /= float(s)
        # Holdings need some shift not to overlap cord letters when showCords is on
        if x < 0 or x > square:
            shift = -s*HOLDING_SHIFT if x < 0 else s*HOLDING_SHIFT
            x -= shift
        x /= float(s)
        return x if x>=0 else x-1, self.RANKS-y
    
    def point2Cord (self, x, y):
        if not self.view.square: return None
        point = self.transPoint(x, y)
        if self.parent.variant == CrazyhouseChess:
            if not -2 <= int(point[0]) <= self.FILES+1 or not 0 <= int(point[1]) <= self.RANKS-1:
                return None
        else:
            if not 0 <= int(point[0]) <= self.FILES-1 or not 0 <= int(point[1]) <= self.RANKS-1:
                return None
        return Cord(int(point[0]), int(point[1]))
    
    def isSelectable (self, cord):
        # Simple isSelectable method, disabling selecting cords out of bound etc
        if not cord:
            return False
        if self.parent.variant == CrazyhouseChess:
            if (not -2 <= cord.x <= self.FILES+1) or (not 0 <= cord.y <= self.RANKS-1):
                return False
        else:
            if (not 0 <= cord.x <= self.FILES-1) or (not 0 <= cord.y <= self.RANKS-1):
                return False
        if self.view.model.status != RUNNING:
            return False
        if self.view.shown != self.view.model.ply:
            return False
        return True
    
    def press (self, x, y):
        pass
    
    def release (self, x, y):
        pass
    
    def motion (self, x, y):
        cord = self.point2Cord(x, y)
        if self.lastMotionCord == cord:
            return
        self.lastMotionCord = cord
        if cord and self.isSelectable(cord):
            self.view.hover = cord
        else: self.view.hover = None
    
    def leave (self, x, y):
        a = self.parent.get_allocation()
        if not (0 <= x < a.width and 0 <= y < a.height):
            self.view.hover = None

class LockedBoardState (BoardState):
    def __init__ (self, board):
        BoardState.__init__(self, board)
    
    def isAPotentiallyLegalNextMove (self, cord0, cord1):
        """ Determines whether the given move is at all legally possible
            as the next move after the player who's turn it is makes their move
            Note: This doesn't always return the correct value, such as when 
            BoardControl.setLocked() has been called and we've begun a drag,
            but view.shown and BoardControl.lockedPly haven't been updated yet """
        
        if cord0 == None or cord1 == None: return False
        if not self.parent.lockedPly in self.parent.possibleBoards:
            return False
        for board in self.parent.possibleBoards[self.parent.lockedPly]:
            if not board[cord0]:
                return False
            if validate(board, Move(cord0, cord1, board)):
                return True
        return False

class NormalState (BoardState):
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        # We don't want empty cords
        if self.getBoard()[cord] == None:
            return False
        # We should not be able to select an opponent piece
        if self.getBoard()[cord].color != self.getBoard().color:
            return False
        return True
    
    def press (self, x, y):
        self.parent.grab_focus()
        cord = self.point2Cord(x,y)
        if self.isSelectable(cord):
            self.view.draggedPiece = self.getBoard()[cord]
            self.view.active = cord
            self.parent.setStateActive()

class ActiveState (BoardState):
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        return self.validate(self.view.active, cord)
    
    def release (self, x, y):
        cord = self.point2Cord(x,y)
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
        if not self.getBoard()[self.view.active]:
            return
        
        BoardState.motion(self, x, y)
        fcord = self.view.active
        piece = self.getBoard()[fcord]
        
        if piece.color != self.getBoard().color:
            return
        
        if not self.view.square: return
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
            self.view.redraw_canvas(rect(paintBox), queue=True)

class SelectedState (BoardState):
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        # Select another piece
        if self.getBoard()[cord] != None and \
                self.getBoard()[cord].color == self.getBoard().color:
            return True
        return self.validate(self.view.selected, cord)
    
    def press (self, x, y):
        cord = self.point2Cord(x,y)
        # Unselecting by pressing the selected cord, or marking the cord to be 
        # moved to. We don't unset self.view.selected, so ActiveState can handle
        # things correctly
        if self.isSelectable(cord):
            if self.view.selected and self.view.selected != cord and \
               self.getBoard()[cord] != None and \
               self.getBoard()[cord].color == self.getBoard().color and \
               not self.validate(self.view.selected, cord):
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

class LockedState (LockedBoardState):
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        # Don't allow premove if neither player is human
        if not self.parent.allowPremove:
            return False
        # We don't want empty cords
        if self.getBoard()[cord] == None:
            return False
        # We should not be able to select an opponent piece
        if self.getBoard()[cord].color == self.getBoard().color:
            return False
        return True
    
    def press (self, x, y):
        self.parent.grab_focus()
        cord = self.point2Cord(x,y)
        if self.isSelectable(cord):
            self.view.draggedPiece = self.getBoard()[cord]
            self.view.active = cord
            self.parent.setStateActive()

class LockedActiveState (LockedBoardState):
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        return self.isAPotentiallyLegalNextMove(self.view.active, cord)

    def release (self, x, y):
        cord = self.point2Cord(x,y)
        if cord == self.view.active == self.view.selected == self.parent.selected_last:
            # user clicked (press+release) same piece twice, so unselect it
            self.view.active = None
            self.view.selected = None
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
        if not self.getBoard()[self.view.active]:
            return
        
        BoardState.motion(self, x, y)
        fcord = self.view.active
        piece = self.getBoard()[fcord]
        
        if piece.color == self.getBoard().color:
            return
        
        if not self.view.square: return
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
            self.view.redraw_canvas(rect(paintBox), queue=True)

class LockedSelectedState (LockedBoardState):
    def isSelectable (self, cord):
        if not BoardState.isSelectable(self, cord):
            return False
        # Select another piece
        if self.getBoard()[cord] != None and \
                self.getBoard()[cord].color != self.getBoard().color:
            return True
        return False
    
    def motion (self, x, y):
        cord = self.point2Cord(x, y)
        if self.lastMotionCord == cord:
            self.view.hover = cord
            return
        self.lastMotionCord = cord
        if cord and self.isAPotentiallyLegalNextMove(self.view.selected, cord):
            self.view.hover = cord
        else: self.view.hover = None
    
    def press (self, x, y):
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
