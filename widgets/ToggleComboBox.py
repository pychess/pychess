import pygtk
pygtk.require("2.0")
import gtk
from gobject import *

class ToggleComboBox (gtk.ToggleButton):

    __gsignals__ = {'changed' : (SIGNAL_RUN_FIRST, TYPE_NONE, (TYPE_INT,))}

    def __init__ (self):
        gtk.ToggleButton.__init__(self)
        self.set_relief(gtk.RELIEF_NONE)
        
        self.label = label = gtk.Label()
        label.set_alignment(0, 0.5)
        hbox = gtk.HBox()
        hbox.pack_start(label)
        arrow = gtk.Arrow (gtk.ARROW_DOWN, gtk.SHADOW_NONE);
        hbox.pack_end(arrow, False, False)
        self.add(hbox)
        self.show_all()
        
        self.connect("button_press_event", self.button_press)
        self.connect("key_press_event", self.key_press)

        self.menu = menu = gtk.Menu()
        deactivate = lambda w: self.set_active(False)
        menu.connect("deactivate", deactivate)
        menu.attach_to_widget(self, None)
        
        self._active = -1
        self._items = []
        
    def _get_active(self):
        return self._active
    def _set_active(self, active):
        if active == self._active: return
        self.emit("changed", active)
        self._active = active
        self.label.set_text(self._items[active])
    active = property(_get_active, _set_active)
    
    def addItem (self, label):
        item = gtk.MenuItem(label)
        item.connect("activate", self.menu_item_activate, len(self._items))
        self.menu.append(item)
        self._items += [label]
        item.show()
        if self.active < 0: self.active = 0
    
    def menuPos (self, menu):
        x, y = self.window.get_origin()
        x += self.get_allocation().x
        y += self.get_allocation().y + self.get_allocation().height
        return (x,y,False)
    
    def button_press (self, widget, event):
        width = self.allocation.width
        self.menu.set_size_request(-1,-1)
        ownWidth = self.menu.size_request()[0]
        self.menu.set_size_request(max(width,ownWidth),-1)
        self.set_active(True)
        self.menu.popup(None,None, self.menuPos, 1, event.time)
    
    from gtk.gdk import keyval_from_name
    keys = map(keyval_from_name,("space", "KP_Space", "Return", "KP_Enter"))
    def key_press (self, widget, event):
        if not event.keyval in self.keys: return
        self.set_active(True)
        self.menu.popup(None,None, self.menuPos, 1, event.time)
        return True
    
    def menu_item_activate (self, widget, index):
        self.active = index
