# -*- coding: UTF-8 -*-

import pygtk
pygtk.require("2.0")
import gtk, gtk.gdk, re
from gobject import *
from pychess.Utils.Cord import Cord
from pychess.Utils.Move import Move
from math import floor, ceil
from BoardView import BoardView, rect
from pychess.System.Log import log
from pychess.Utils.const import *
from BoardView import join
from time import time
from pychess.Utils.logic import getDestinationCords

class BoardControl (gtk.EventBox):
    
    __gsignals__ = {
        'piece_moved' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'call_flag' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'draw' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'lock_changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }
    
    def __init__(self, gamemodel):
        gtk.EventBox.__init__(self)
        widgets = gtk.glade.XML(prefix("glade/promotion.glade"))
        self.promotionDialog = widgets.get_widget("promotionDialog")
        self.view = BoardView(gamemodel)
        self.add(self.view)
        
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK|gtk.gdk.POINTER_MOTION_MASK)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)
        
        self.fromcord = None # The cord to which the tocords list is relative
        self.tocords = [] # List of cords to which the selected piece can move
        
        self.pressed = False
        self.locked = True
    
    def emit_move_signal (self, cord0, cord1):
        promotion = QUEEN
        if self.view.model.boards[-1][cord0].sign == PAWN and cord1.y in (0,7):
            res = int(self.promotionDialog.run())
            self.promotionDialog.hide()
            if res == int(gtk.RESPONSE_DELETE_EVENT):
                # Put back pawn moved be d'n'd
                self.view.runAnimation(redrawMisc = False)
                return
            promotion = [QUEEN,ROOK,BISHOP,KNIGHT][res]
        
        move = Move(cord0, cord1, self.view.model.boards[-1], promotion)
        self.emit("piece_moved", move)
    
    #          Selection and stuff          #
    
    def isSelectable (self, cord):
        if self.locked: return False
        if self.view.model.status != RUNNING: return False
        if not cord: return False
        if cord.x < 0 or cord.x > 7 or cord.y < 0 or cord.y > 7: return False
        
        if self.view.shown != len(self.view.model.boards)-1:
            return False
        
        # Set the basiscord to the selected or active
        if self.view.active:
            basiscord = self.view.active
        else: basiscord = self.view.selected
        
        # If we are dealing with two cords (a piece select)
        if basiscord and basiscord != cord:
            
            # If some fast mouse trickery was used to make a cord active with no
            # piece, we can't continue
            if not self.view.model.boards[-1][basiscord]:
                return False
            
            # If the tocords list, is not relative to our basiscord, we have to
            # create a new list.
            if self.fromcord != basiscord:
                self.tocords = getDestinationCords(
                                          self.view.model.boards[-1], basiscord)
                self.fromcord = basiscord # Remember the basiscord of self.tocords
            
            # If cord is a legal move..
            if cord in self.tocords:
                return True
        
        # if no other cord is active/selected, we are probably trying to select
        # a piece to move. In that case we should not want empty cords
        if self.view.model.boards[-1][cord] == None:
            return False
        
        # We also don't won't to select friendly pieces while dragging
        if self.view.active and self.pressed:
            return False
        
        # We should not be able to select an opponent piece
        color = self.view.model.boards[-1].color
        if self.view.model.boards[-1][cord].color != color:
            return False
        
        return True
    
    def transPoint (self, x, y):
        if not self.view.square: return None
        xc, yc, square, s = self.view.square
        y -= yc; x -= xc
        y /= float(s)
        x /= float(s)
        if self.view.fromWhite:
            y = 8 - y
        else: x = 8 - x
        return x, y
    
    def point2Cord (self, x, y):
        if not self.view.square: return None
        point = self.transPoint(x, y)
        x = floor(point[0])
        if self.view.fromWhite:
            y = floor(point[1])
        else: y = floor(point[1])
        return Cord(int(x), int(y))
    
    def button_press (self, widget, event):
        self.pressed = True
        
        self.grab_focus()
        cord = self.point2Cord (event.x, event.y)
        
        if not self.isSelectable(cord):
            self.view.active = None
            self.view.selected = None
        else:
            self.view.active = cord
    
    def button_release (self, widget, event):
        self.pressed = False

        cord = self.point2Cord (event.x, event.y)
        if self.view.selected == cord or cord == None:
            self.view.selected = None
            self.view.startAnimation()
        elif cord == self.view.active:
            color = self.view.model.boards[-1].color
            if self.view.model.boards[-1][cord] != None and \
                    self.view.model.boards[-1][cord].color == color:
                self.view.selected = cord
                self.view.startAnimation()
            elif self.view.selected:
                if self.view.active and \
                        self.view.model.boards[-1][self.view.active] and \
                        self.view.model.boards[-1][cord].color == color:
                    self.emit_move_signal(self.view.active, cord)
                else: self.emit_move_signal(self.view.selected, cord)
                self.view._hover = cord
                self.view.selected = None
            else:
                self.view.selected = cord
        elif self.view.active != None:
            color = self.view.model.boards[-1].color
            if self.isSelectable(cord) and \
                    (not self.view.model.boards[-1][cord] or \
                    self.view.model.boards[-1][cord].color != color):
                cord0 = self.view.active
                self.view.active = None
                self.view.selected = None
                self.emit_move_signal(cord0, cord)
            else:
                self.view.active = None
                self.view.selected = None
                color = self.view.model.boards[-1].color
                if not self.isSelectable(cord) or \
                        self.view.model.boards[-1][cord] and \
                        self.view.model.boards[-1][cord].color == color:
                    self.view.startAnimation()
    
    def motion_notify (self, widget, event):
        cord = self.point2Cord (event.x, event.y)
        if cord == None: return
        
        if not self.isSelectable(cord):
            self.view.hover = None
        else: self.view.hover = cord
        
        if self.pressed and self.view.active:
            piece = self.view.model.boards[self.view.shown][self.view.active]
            if not piece: return
            if piece.color != self.view.model.boards[-1].color: return
            xc, yc, square, s = self.view.square
            
            if not self.view.square: return
            xc, yc, square, s = self.view.square
            if self.view.fromWhite:
                point = self.transPoint(event.x-s/2., event.y+s/2.)
            else: point = self.transPoint(event.x+s/2., event.y-s/2.)
            if not point: return
            x, y = point
            if piece.x != x or piece.y != y:
                if piece.x:
                    paintBox = self.view.fcord2Rect(piece.x, piece.y)
                else: paintBox = self.view.cord2Rect(self.view.active)
                paintBox = join(paintBox, self.view.fcord2Rect(x, y))
                piece.x = x
                piece.y = y
                self.view.redraw_canvas(rect(paintBox))
    
    def leave_notify (self, widget, event):
        a = self.get_allocation()
        if not (0 <= event.x < a.width and 0 <= event.y < a.height):
            self.view.hover = None
    
    def on_call_flag_activate (self, widget):
        if self.locked:
            log.warn("Using locked methodhandler (skipping). Menuitem should have been locked\n")
            return
        self.emit("call_flag")
        
    def on_draw_activate (self, widget):
        if self.locked:
            log.warn("Using locked methodhandler (skipping). Menuitem should have been locked\n")
            return
        self.emit("draw")
        
    def on_resign_activate (self, widget):
        if self.locked:
            log.warn("Using locked methodhandler (skipping). Menuitem should have been locked\n")
            return
        self.emit("resign")
    
