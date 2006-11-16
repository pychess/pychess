# -*- coding: UTF-8 -*-

import pygtk
pygtk.require("2.0")
import gtk, gtk.gdk, re
from gobject import *
from Utils.Cord import Cord
from Utils.Move import Move
from math import floor
from BoardView import BoardView
from System.Log import log
from Utils.const import *
from BoardView import join
from time import time

class BoardControl (gtk.EventBox):

    __gsignals__ = {
        'piece_moved' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_PYOBJECT,)),
        'call_flag' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'draw' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'resign' : (SIGNAL_RUN_FIRST, TYPE_NONE, ())
    }
    
    def __init__(self):
        gtk.EventBox.__init__(self)
        widgets = gtk.glade.XML("glade/promotion.glade")
        self.promotionDialog = widgets.get_widget("promotionDialog")
        self.view = BoardView()
        self.add(self.view)
        
        self.connect("button_press_event", self.button_press)
        self.connect("button_release_event", self.button_release)
        self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK|gtk.gdk.POINTER_MOTION_MASK)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)
        
        self.pressed = False
        self.locked = True
    
    def emit_move_signal (self, cord0, cord1):
        promotion = QUEEN
        if self.view.history[-1][cord0].sign == PAWN and cord1.y in (0,7):
            res = int(self.promotionDialog.run())
            self.promotionDialog.hide()
            if res == int(gtk.RESPONSE_DELETE_EVENT):
                return
            promotion = [QUEEN,ROOK,BISHOP,KNIGHT][res]
            
        move = Move(cord0, cord1, promotion)
        self.emit("piece_moved", move)
    
    #          Selection and stuff          #
    
    def isSelectable (self, cord):
        if self.locked: return False
        if not self.view.history[-1].movelist: return False
        if not cord: return False

        if self.view.shown != len(self.view.history)-1:
            return False
        
        if self.view.active:
            basiscord = self.view.active
        else: basiscord = self.view.selected
        
        if basiscord in self.view.history[-1].movelist and \
            cord in self.view.history[-1].movelist[basiscord]:
            return True
        if self.view.history[-1][cord] == None:
            return False

        color = self.view.history.curCol()
        if self.view.history[-1][cord].color != color:
            return False
        
        return True
    
    def transPoint (self, x, y):
        if not self.view.square: return None
        xc, yc, square, s = self.view.square
        y -= yc; x -= xc
        if (x < 0 or x >= square or y < 0 or y >= square):
            return None
        y /= float(s)
        x /= float(s)
        if self.view.fromWhite:
            y = 8 - y
        return x, y
    
    def point2Cord (self, x, y):
        if not self.view.square: return None
        point = self.transPoint(x, y)
        if not point: return
        x, y = map(floor, point)
        if (x < 0 or x >= 8 or y < 0 or y >= 8):
            return
        return Cord(x, y)

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
            color = self.view.history.curCol()
            if self.view.history[-1][cord] != None and \
                    self.view.history[-1][cord].color == color:
                self.view.selected = cord
                self.view.startAnimation()
            elif self.view.selected:
                if self.view.active and self.view.history[-1][self.view.active] and \
                        self.view.history[-1][cord].color == color:
                    self.emit_move_signal(self.view.active, cord)
                else: self.emit_move_signal(self.view.selected, cord)
                self.view._hover = cord
                self.view.selected = None
            else:
                self.view.selected = cord
        elif self.view.active != None:
            color = self.view.history.curCol()
            if self.isSelectable(cord) and (not self.view.history[-1][cord] or \
                    self.view.history[-1][cord].color != color):
                cord0 = self.view.active
                self.view.active = None
                self.view.selected = None
                self.emit_move_signal(cord0, cord)
            else:
                self.view.active = None
                self.view.selected = None
                color = self.view.history.curCol()
                if not self.isSelectable(cord) or self.view.history[-1][cord] and \
                        self.view.history[-1][cord].color == color:
                    self.view.startAnimation()
                    
    def motion_notify (self, widget, event):
        cord = self.point2Cord (event.x, event.y)
        if cord == None: return
        
        if not self.isSelectable(cord):
            self.view.hover = None
        else: self.view.hover = cord
        
        if self.pressed and self.view.active:
            piece = self.view.history[self.view.shown][self.view.active]
            if not piece: return
            xc, yc, square, s = self.view.square
            
            if not self.view.square: return
            xc, yc, square, s = self.view.square
            point = self.transPoint(event.x-s/2., event.y+s/2.)
            if not point: return
            x, y = point
            if piece.x != x or piece.y != y:
                if piece.x:
                    paintBox = self.view.fcord2Rect(piece.x, piece.y)
                else: paintBox = self.view.cord2Rect(self.view.active)
                paintBox = join(paintBox, self.view.fcord2Rect(x, y))
                piece.x = x
                piece.y = y
                self.view.redraw_canvas(paintBox)

    def leave_notify (self, widget, event):
        a = self.get_allocation()
        if not (0 <= event.x < a.width and 0 <= event.y < a.height):
            self.view.hover = None
    
    def on_call_flag_activate (self, widget):
        if self.locked:
            #TODO: Should BoardControl own the action menu?
            log.warn("Using locked methodhandler (skipping). Menuitem should have been locked")
            return
        self.emit("call_flag")
        
    def on_draw_activate (self, widget):
        if self.locked:
            log.warn("Using locked methodhandler (skipping). Menuitem should have been locked")
            return
        self.emit("draw")
        
    def on_resign_activate (self, widget):
        if self.locked:
            log.warn("Using locked methodhandler (skipping). Menuitem should have been locked")
            return
        self.emit("resign")
    
