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
from BoardView import BoardView
from Utils.Log import log

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
        self.connect("focus_out_event", self.focus_out)
        self.add_events(gtk.gdk.LEAVE_NOTIFY_MASK|gtk.gdk.POINTER_MOTION_MASK)
        self.connect("motion_notify_event", self.motion_notify)
        self.connect("leave_notify_event", self.leave_notify)
    
    def emit_move_signal (self, cord0, cord1):
        #TODO: Should this be moved static to Human class?
        promotion = "q"
        if len(self.view.history) > 0 and self.view.history[-1][cord0] != None and \
                self.view.history[-1][cord0].sign == "p" and cord1.y in [0,7]:
            res = int(self.promotionDialog.run())
            self.promotionDialog.hide()
            if res == int(gtk.RESPONSE_DELETE_EVENT):
                return
            promotion = ["q","r","b","n"][res]
            
        move = Move(self.view.history, (cord0, cord1), promotion)
        self.emit("piece_moved", move)
    
    #          Selection and stuff          #
    
    locked = True
    def isSelectable (self, cord):
        if self.locked: return False
        if not self.view.history.movelist[-1]: return False
        if not cord: return False

        if self.view.shown != len(self.view.history)-1:
            return False

        if self.view.selected in self.view.history.movelist[-1] and \
            cord in self.view.history.movelist[-1][self.view.selected]:
            return True
        if self.view.history[-1][cord] == None:
            return False

        color = self.view.history.curCol()
        if self.view.history[-1][cord].color != color:
            return False
        
        return True
    
    def point2Cord (self, x, y):
        if not self.view.square: return None
        xc, yc, square, s = self.view.square
        y -= yc; x -= xc
        if (x < 0 or x >= square or y < 0 or y >= square):
            return None
        x = floor(x/s); y = floor(y/s)
        if self.view.fromWhite: return Cord(x, 7-y)
        return Cord(7-x, y)

    def button_press (self, widget, event):
        self.grab_focus()
        cord = self.point2Cord (event.x, event.y)
        
        if not self.isSelectable(cord):
            self.view.active = None
        else: self.view.active = cord
    
    def button_release (self, widget, event):
        cord = self.point2Cord (event.x, event.y)
        if self.view.selected == cord or cord == None:
            self.view.selected = None
        elif cord == self.view.active:
            color = self.view.history.curCol()
            if self.view.history[-1][cord] != None and self.view.history[-1][cord].color == color:
                self.view.selected = cord
            elif self.view.selected:
                self.emit_move_signal(self.view.selected, cord)
                self.view._hover = cord
                self.view.selected = None
            else: self.view.selected = cord
        else:
            if self.view.active != None:
                self.view.selected = self.view.active
                if not self.isSelectable(cord):
                    self.view.selected = None
                else:
                    self.view.active = cord
                    self.button_release(widget, event)
    
    def motion_notify (self, widget, event):
        cord = self.point2Cord (event.x, event.y)
        if cord == None: return
        if not self.isSelectable(cord):
            self.view.hover = None
        else: self.view.hover = cord

    def leave_notify (self, widget, event):
        a = self.get_allocation()
        if not (0 <= event.x < a.width and 0 <= event.y < a.height):
            self.view.hover = None
    
    def focus_out (self, widget, event):
        pass
    #    self.view.selected = None
    #    self.view.active = None


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
    
