# -*- coding: UTF-8 -*-

import gtk, gtk.gdk
from gobject import *

from pychess.System.prefix import addDataPrefix
from pychess.System.Log import log
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move
from pychess.Utils.const import *
from pychess.Utils.logic import validate

from BoardView import BoardView, rect
from BoardView import join

class BoardControl (gtk.EventBox):
    
    __gsignals__ = {
        'piece_moved' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object, int)),
        'action' : (SIGNAL_RUN_FIRST, TYPE_NONE, (int, object))
    }
    
    def __init__(self, gamemodel, actionMenuItems):
        gtk.EventBox.__init__(self)
        widgets = gtk.glade.XML(addDataPrefix("glade/promotion.glade"))
        self.promotionDialog = widgets.get_widget("promotionDialog")
        self.view = BoardView(gamemodel)
        self.add(self.view)
        
        self.actionMenuItems = actionMenuItems
        for key, menuitem in self.actionMenuItems.iteritems():
            if menuitem == None: print key
            menuitem.connect("activate", self.actionActivate, key)
        
        self.view.connect("shown_changed", self.shown_changed)
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK|gtk.gdk.POINTER_MOTION_MASK)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)
        
        self.normalState = NormalState(self)
        self.selectedState = SelectedState(self)
        self.activeState = ActiveState(self)
        self.lockedState = LockedState(self)
        self.currentState = self.lockedState
    
    def emit_move_signal (self, cord0, cord1):
        color = self.view.model.boards[-1].color
        promotion = QUEEN
        board = self.view.model.getBoardAtPly(self.view.shown)
        if board[cord0].sign == PAWN and cord1.y in (0,7):
            res = int(self.promotionDialog.run())
            self.promotionDialog.hide()
            if res == int(gtk.RESPONSE_DELETE_EVENT):
                # Put back pawn moved be d'n'd
                self.view.runAnimation(redrawMisc = False)
                return
            promotion = [QUEEN,ROOK,BISHOP,KNIGHT][res]
        
        move = Move(cord0, cord1, self.view.model.boards[-1], promotion)
        self.emit("piece_moved", move, color)
    
    def actionActivate (self, widget, key):
        """ Put actions from a menu or similar """
        if key == "call_flag":
            self.emit("action", FLAG_CALL, None)
        elif key == "draw":
            self.emit("action", DRAW_OFFER, None)
        elif key == "resign":
            self.emit("action", RESIGNATION, None)
        elif key == "ask_to_move":
            self.emit("action", HURRY_ACTION, None)
        elif key == "undo1":
            if self.view.model.curplayer.__type__ == LOCAL:
                self.emit("action", TAKEBACK_OFFER, self.view.model.ply-2)
            else: self.emit("action", TAKEBACK_OFFER, self.view.model.ply-1)
        elif key == "pause1":
            self.emit("action", PAUSE_OFFER, None)
        elif key == "resume1":
            self.emit("action", RESUME_OFFER, None)
    
    def shown_changed (self, view, shown):
        self.view.selected = None
        self.view.active = None
        self.view.hover = None
        if isinstance(self.currentState, ActiveState) or \
                isinstance(self.currentState, SelectedState):
            self.setState(self.normalState)
    
    def setLocked (self, locked):
        if locked:
            self.setState(self.lockedState)
        else: self.setState(self.normalState)
    
    def setState (self, state):
        self.currentState = state
    
    def button_press (self, widget, event):
        return self.currentState.press(event.x, event.y)
    
    def button_release (self, widget, event):
        return self.currentState.release(event.x, event.y)
    
    def motion_notify (self, widget, event):
        return self.currentState.motion(event.x, event.y)
    
    def leave_notify (self, widget, event):
        return self.currentState.leave(event.x, event.y)

class BoardState:
    def __init__ (self, board):
        self.parent = board
        self.view = board.view
    
    def getBoard (self):
        return self.view.model.getBoardAtPly(self.view.shown)
    
    def validate (self, cord0, cord1):
        return validate(self.getBoard(), Move(cord0, cord1, self.getBoard()))
    
    def transPoint (self, x, y):
        if not self.view.square: return None
        xc, yc, square, s = self.view.square
        x, y = self.view.invmatrix.transform_point(x,y)
        y -= yc; x -= xc
        y /= float(s)
        x /= float(s)
        return x, 8-y
    
    def point2Cord (self, x, y):
        if not self.view.square: return None
        point = self.transPoint(x, y)
        if not 0 <= int(point[0]) <= 7 or not 0 <= int(point[1]) <= 7:
            return None
        return Cord(int(point[0]), int(point[1]))
    
    def isSelectable (self, cord):
        # Simple isSelectable method, disabling selecting cords out of bound etc
        if not cord:
            return False
        if not 0 <= cord.x <= 7 or not 0 <= cord.y <= 7:
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
        if cord and self.isSelectable(cord):
            self.view.hover = cord
        else: self.view.hover = None
    
    def leave (self, x, y):
        a = self.parent.get_allocation()
        if not (0 <= x < a.width and 0 <= y < a.height):
            self.view.hover = None

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
            self.view.active = cord
            self.parent.setState(self.parent.activeState)

class LockedState (BoardState):
    def isSelectable (self, cord):
        return False

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
            self.view.startAnimation()
            self.parent.setState(self.parent.normalState)
        
        # When in the mixed active/selected state
        elif self.view.selected:
            # Unselect when releasing on an already selected cord
            if cord == self.view.active == self.view.selected:
                self.view.hover = cord
                self.view.selected = None
                self.view.active = None
                self.view.startAnimation()
                self.parent.setState(self.parent.normalState)
            
            # Move when releasing on a good cord
            elif cord == self.view.active:
                # Select it if it is friendly
                if self.getBoard()[cord] and \
                        self.getBoard()[cord].color == self.getBoard().color:
                    if self.getBoard().variant == FISCHERRANDOMCHESS:
                        # in frc we enable castling moves when the king
                        # moves on top of the involved rook
                        if self.validate(self.view.selected, cord):
                            self.parent.emit_move_signal(self.view.selected, cord)
                            self.view.selected = None
                            self.view.active = None
                            self.parent.setState(self.parent.normalState)
                        else:
                            self.view.selected = cord
                            self.view.active = None
                            self.view.startAnimation()
                            self.parent.setState(self.parent.selectedState)
                    else:
                        self.view.selected = cord
                        self.view.active = None
                        self.view.startAnimation()
                        self.parent.setState(self.parent.selectedState)
                # Move to it, if it isn't
                else:
                    self.parent.setState(self.parent.normalState)
                    # It is important to emit_move_signal after setting of stage
                    # as listeners of the function probably will lock the board
                    self.parent.emit_move_signal(self.view.selected, cord)
                    self.view.selected = None
                    self.view.active = None
            
            # Unselect when releasing on a nonactive cord
            else:
                self.view.selected = None
                self.view.active = None
                self.view.startAnimation()
                self.parent.setState(self.parent.normalState)
        
        # Selecting if releasing on the active cord
        elif cord == self.view.active:
            self.view.selected = cord
            self.view.active = None
            self.view.startAnimation()
            self.parent.setState(self.parent.selectedState)
        
        # If dragged and released on a possible cord
        elif cord == self.view.hover:
            self.parent.setState(self.parent.normalState)
            self.parent.emit_move_signal(self.view.active, cord)
            self.view.active = None
        
        # Send back, if dragging to a not possible cord
        else:
            self.view.active = None
            # Send the piece back to its original cord
            self.view.startAnimation()
            self.parent.setState(self.parent.normalState)
    
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
            self.view.active = cord
            self.parent.setState(self.parent.activeState)
        # Unselecting by pressing an inactive cord
        else:
            self.view.selected = None
            self.parent.setState(self.parent.normalState)
