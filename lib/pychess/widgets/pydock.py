from pychess.System.prefix import addDataPrefix
from math import ceil as float_ceil
ceil = lambda f: int(float_ceil(f))
import cairo
import gobject
import gtk
import re
import rsvg
import gobject

POSITION_CENTER, POSITION_TOP, POSITION_RIGHT, POSITION_BOTTOM, \
    POSITION_LEFT = range(5)

GROUP_ID_ACTIVE = 42
GROUP_ID_INACTIVE = -1

#===============================================================================
# Composite Interfaces
#===============================================================================

#---- TODO: Hiding of the pane handles can be done by putting a lock funciton in
#-------- Composite, and possible also Leaf, which changes HPaned with HBox etc.

class DockComponent:
    def dock (self, widget, position, title):
        abstract
    
    def _get_top_parrent (self):
        parent = self.get_parent()
        while not isinstance(parent, TopDock):
            parent = parent.get_parent()
        return parent

class DockComposite (DockComponent):
    def change (self, old, new):
        abstract
    def removeComponent (self, widget):
        abstract

class DockLeaf (DockComponent):
    def undock (self, widget):
        abstract

class TopDock (DockComposite):
    pass

#===============================================================================
# Composite Implementation
#===============================================================================

class PanedDockComposite (gtk.Paned, DockComposite):
    def __init__ (self, position):
        self.position = position
    
    def _initChildren (self, old, new):
        if self.position == POSITION_TOP or self.position == POSITION_LEFT:
            self.add1(new)
            self.add2(old)
        elif self.position == POSITION_BOTTOM or self.position == POSITION_RIGHT:
            self.add1(old)
            self.add2(new)
    
    def add1 (self, widget):
        self.emit("add", widget)
        gtk.Paned.add1(self, widget)
    
    def add2 (self, widget):
        self.emit("add", widget)
        gtk.Paned.add2(self, widget)
    
    def dock (self, widget, position, title):
        assert position != POSITION_CENTER, "POSITION_CENTER only works for leaves"
        leaf = PyDockLeaf(widget, title)
        new = PyDockComposite(position)
        self.get_parent().change(self, new)
        new._initChildren(self, leaf)
        new.show_all()
        return leaf
    
    def change (self, old, new):
        if old == self.get_child1():
            self.remove(old)
            self.add1(new)
        else:
            self.remove(old)
            self.add2(new)
    
    def removeComponent (self, widget):
        if widget == self.get_child1():
            new = self.get_child2()
        else:
            new = self.get_child1()
        self.remove(new)
        self.get_parent().change(self, new)

class HDockComposite (gtk.HPaned, PanedDockComposite):
    def __init__ (self, position):
        gtk.HPaned.__init__(self)
        PanedDockComposite.__init__(self, position)

class VDockComposite (gtk.VPaned, PanedDockComposite):
    def __init__ (self, position):
        gtk.VPaned.__init__(self)
        PanedDockComposite.__init__(self, position)

def PyDockComposite (position):
    if position == POSITION_TOP or position == POSITION_BOTTOM:
        return VDockComposite(position)
    elif position == POSITION_LEFT or position == POSITION_RIGHT:
        return HDockComposite(position)

#===============================================================================
# Drag Abstracts
#===============================================================================

class ButtonDragHandler:
    def __init__ (self):
        if not isinstance(self, gtk.Notebook):
            self.connect("add", self.on_add)
            for child in self.get_children():
                self.on_add(self, child)
        else:
            self.set_group_id(GROUP_ID_ACTIVE)
        
        self.connect("drag-leave", self.on_drag_leave)
        self.connect("drag-end", self.on_drag_end)
        self.connect("drag-begin", self.on_drag_begin)
        self.connect("drag-motion", self.on_drag_motion)
        self.connect("drag-drop", self.on_drag_drop)
        
        self.connect_after("expose-event", self.onExpose)
        self.connect_after("style-set", self.onStyleSet)
        
        self.showStar = True
        self.showButtonsAlways = False
        
        self.dragPos = None
        self.highLight = None
        
        self.starSurface = None
        self.buttonSurfaces = None
        self.buttonPaddingX = 0.2 # Amount of button width
        self.buttonPaddingY = 0.4 # Amount of button height
    
    def setShowStar (self, showStar):
        self.showStar = showStar
    
    def setShowButtonsAlways (self, showButtonsAlways):
        self.showButtonsAlways = showButtonsAlways
    
    def getButtonPositions (self):
        """ Yields the four or five (POSITION_X, rectangle) tuples. The
            rectangle positions are compatible with drawing and mouse input. """
        abstract
    
    def parsePosition (self, x, y):
        """ Returns a POSITION or None """
        for position, rectangle in self.getButtonPositions():
            if rectangle.x <= x < rectangle.x + rectangle.width and \
                    rectangle.y <= y < rectangle.y + rectangle.height:
                return position
    
    def on_add (self, self_, widget, *stuff):
        targets = [("GTK_NOTEBOOK_TAB", gtk.TARGET_SAME_APP, 0xbadbeef)]
        widget.drag_dest_set(gtk.DEST_DEFAULT_DROP|gtk.DEST_DEFAULT_MOTION,
                             targets, gtk.gdk.ACTION_MOVE)
        widget.drag_dest_set_track_motion(True)
        
        widget.connect("drag-end", self.on_drag_end)
        
        def moveAndChain (widget, context, x, y, timestamp, function):
            r = widget.get_allocation()
            s = self.get_allocation()
            function(widget, context, x-s.x+r.x, y-s.y+r.y, timestamp)
        widget.connect("drag-drop", moveAndChain, self.on_drag_drop)
        widget.connect("drag-motion", moveAndChain, self.on_drag_motion)
        
        if isinstance(widget, gtk.Notebook):
            widget.connect("drag-end", self.on_drag_end)
        else:
            widget.connect("add", self.on_add)
            for child in widget.get_children():
                self.on_add(widget, child)
    
    def on_drag_leave (self, self_, context, timestamp):
        if not self.showButtonsAlways:
            assert not isinstance(self, gtk.Alignment)
            self.dragPos = None
            self.highLight = None
            self.queue_draw()
    
    def on_drag_end (self, widget, context):
        if not hasattr(context, "isEnded") and self.showButtonsAlways:
            self.dragPos = None
            self.highLight = None
            self.queue_draw()
            context.isEnded = True
    
    def on_drag_begin (self, self_, context):
        if self.showButtonsAlways:
            self.dragPos = (10000,10000)
            self.highLight = None
            self.queue_draw()
    
    def on_drag_motion (self, receiver, context, x, y, timestamp):
        if self.dragPos == (x,y):
            return
        parsed = self.parsePosition(x,y)
        
        if not self.dragPos or self.highLight != parsed:
            self.dragPos = (x,y)
            self.highLight = parsed
            self.queue_draw()
        self.dragPos = (x,y)
        
        if self.highLight == None:
            if isinstance(receiver, gtk.Notebook):
                receiver.set_group_id(GROUP_ID_INACTIVE)
            else:
                context.drag_status (gtk.gdk.ACTION_DEFAULT, timestamp)
        else:
            if isinstance(receiver, gtk.Notebook):
                receiver.set_group_id(GROUP_ID_ACTIVE)
                context.get_source_widget().set_group_id(GROUP_ID_ACTIVE)
            else:
                context.drag_status (gtk.gdk.ACTION_MOVE, timestamp)
            return True
    
    def on_drag_drop (self, receiver, context, x, y, timestamp):
        if hasattr(context, "isFinished"):
            context.finish(True, True, timestamp)
            return True
        
        position = self.parsePosition(x,y)
        sender = context.get_source_widget()
        
        # If the drop wasn't at a button
        if position == None:
            return
        
        if isinstance(receiver, gtk.Notebook):
            if sender == receiver:
                if position == POSITION_CENTER:
                    return
                if len(sender.get_children()) == 1:
                    return
            elif len(sender.get_children()) >= 1 and position == POSITION_CENTER:
                # We rely on the automatic tab moving
                return
            else:
                # We need to undo the automatic tab moving
                child = receiver.get_nth_page(receiver.get_current_page())
                title = receiver.get_tab_label(child) 
                receiver.remove_page(receiver.get_current_page())
                sender.append_page(child, title)
        
        if not "child" in locals():
            child = sender.get_nth_page(sender.get_current_page())
        
        title = sender.undock(child)
        self.dock(child, position, title)
        
        context.finish(True, True, timestamp)
        context.isFinished = True
        
        return True
    
    def onStyleSet (self, self_, oldstyle):
        self.starSurface = None
        self.buttonSurfaces = None
    
    def ensureSurfaces (self):
        if self.buttonSurfaces and self.lastAlloc == self.get_allocation:
            return
        
        def colorToHex (color, state):
             color = getattr(self.get_style(), color)[state]
             pixels = (color.red, color.green, color.blue)
             return "#"+"".join(hex(c/256)[2:].zfill(2) for c in pixels)
        
        def loadSvg (path):
            data = file(path).read()
            colorDic = {"#18b0ff": colorToHex("light", gtk.STATE_SELECTED),
                        "#575757": colorToHex("text_aa", gtk.STATE_PRELIGHT),
                        "#e3ddd4": colorToHex("bg", gtk.STATE_NORMAL),
                        "#d4cec5": colorToHex("bg", gtk.STATE_INSENSITIVE),
                        "#ffffff": colorToHex("base", gtk.STATE_NORMAL),
                        "#000000": colorToHex("fg", gtk.STATE_NORMAL)}
            repl = lambda m: m.group() in colorDic and colorDic[m.group()] or m.group()
            data = re.sub("|".join(colorDic.keys()), repl, data)
            f = file("/tmp/pychess_theamed.svg", "w")
            f.write(data)
            f.close()
            svg = rsvg.Handle("/tmp/pychess_theamed.svg")
            return svg
        
        def svgToSurface (svg, scale=1):
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         ceil(svg.props.width*scale),
                                         ceil(svg.props.height*scale))
            context = cairo.Context(surface)
            context.set_operator(cairo.OPERATOR_SOURCE)
            context.scale(scale, scale)
            svg.render_cairo(context)
            return surface
        
        self.lastAlloc = self.get_allocation()
        starSvg = loadSvg(addDataPrefix("glade/dock_star.svg"))
        scale = min(min(self.lastAlloc.width/float(starSvg.props.width),1),
                    min(self.lastAlloc.height/float(starSvg.props.height),1))
        self.starSurface = svgToSurface(starSvg, scale)
        
        create = lambda path, scale: svgToSurface(loadSvg(addDataPrefix(path)), scale)
        self.buttonSurfaces = {
            POSITION_CENTER: create("glade/dock_center.svg",scale),
            POSITION_TOP: create("glade/dock_top.svg",scale),
            POSITION_RIGHT: create("glade/dock_right.svg",scale),
            POSITION_BOTTOM: create("glade/dock_bottom.svg",scale),
            POSITION_LEFT: create("glade/dock_left.svg",scale)
        }
    
    def onExpose(self, area, event):
        context = self.window.cairo_create()
        r = self.get_allocation()
        if self.highLight != None:
            if self.highLight == POSITION_CENTER:
                context.rectangle(r)
            elif self.highLight == POSITION_TOP:
                context.rectangle(r.x, r.y,
                                  r.width, r.height*0.381966011)
            elif self.highLight == POSITION_RIGHT:
                context.rectangle(r.x + r.width*0.618033989, r.y,
                                  r.width*0.381966011, r.height)
            elif self.highLight == POSITION_BOTTOM:
                context.rectangle(r.x, r.y + r.height*0.618033989,
                                  r.width, r.height*0.381966011)
            elif self.highLight == POSITION_LEFT:
                context.rectangle(r.x, r.y,
                                  r.width*0.381966011, r.height)
            context.set_source_color(self.get_style().light[gtk.STATE_SELECTED])
            context.fill()
        
        if self.dragPos:
            self.ensureSurfaces()
            
            if self.showStar:
                star_w = self.starSurface.get_width()
                star_h = self.starSurface.get_height()
                context.set_source_surface(self.starSurface,
                                           r.x + r.width/2 - star_w/2,
                                           r.y + r.height/2 - star_h/2)
                context.paint()
            
            for position, rectangle in self.getButtonPositions():
                surface = self.buttonSurfaces[position]
                context.set_source_surface(surface,
                                           r.x + rectangle.x, r.y + rectangle.y)
                context.paint()

#===============================================================================
# Top and leaf logic implementation
#===============================================================================

class PyDock (gtk.Alignment, TopDock, ButtonDragHandler):
    def __init__ (self):
        gtk.Alignment.__init__(self, xscale=1, yscale=1)
        ButtonDragHandler.__init__(self)
        self.setShowStar(False)
        self.setShowButtonsAlways(True)
    
    def dock (self, widget, position, title):
        if not self.get_child():
            leaf = PyDockLeaf(widget, title)
            self.add(leaf)
            return leaf
        else:
            return self.get_child().dock(widget, position, title)
    
    def change (self, old, new):
        self.remove(old)
        self.add(new)
    
    def removeComponent (self, widget):
        self.remove(widget)
    
    def toXML (self):
        pass
    
    def fromXML (self):
        pass
    
    
    def getButtonPositions (self):
        """ Yields the five (POSITION_X, rectangle) tuples. The rectangle
            positions are compatible with drawing and mouse input. """
        self.ensureSurfaces()
        r = self.get_allocation()
        for position, dx, dy in ((POSITION_TOP, 0.5, 0),
                                 (POSITION_RIGHT, 1, 0.5),
                                 (POSITION_BOTTOM, 0.5, 1),
                                 (POSITION_LEFT, 0, 0.5)):
            surface = self.buttonSurfaces[position]
            yield (position,
                   gtk.gdk.Rectangle(int(r.x + (r.width-surface.get_width())*dx),
                                     int(r.y + (r.height-surface.get_height())*dy),
                                     surface.get_width(), surface.get_height()))

class PyDockLeaf (gtk.Notebook, DockLeaf, ButtonDragHandler):
    def __init__ (self, widget, title):
        gtk.Notebook.__init__(self)
        ButtonDragHandler.__init__(self)
        self.setShowStar(True)
        self._add(widget, title)
    
    def _add (self, widget, title):
        self.append_page(widget, title)
        self.set_tab_label_packing(widget, True, True, gtk.PACK_START)
        self.set_tab_detachable(widget, True)
    
    def dock (self, widget, position, title):
        if position == POSITION_CENTER:
            self._add(widget, title)
            return self
        else:
            leaf = PyDockLeaf(widget, title)
            new = PyDockComposite(position)
            self.get_parent().change(self, new)
            new._initChildren(self, leaf)
            new.show_all()
            return leaf
    
    def undock (self, widget):
        assert widget in self.get_children()
        title = self.get_tab_label(widget)
        self.remove_page(self.page_num(widget))
        if self.get_n_pages() == 0:
            def cb ():
                self.get_parent().removeComponent(self)
            # We need to idle_add this, as the widget won't emit drag-ended, if
            # it is removed to early
            gobject.idle_add(cb)
        return title
    
    def getButtonPositions (self):
        """ Yields the five (POSITION_X, rectangle) tuples. The rectangle
            positions are compatible with drawing and mouse input. """
        self.ensureSurfaces()
        r = self.get_allocation()
        for position, dx, dy in ((POSITION_CENTER, 0, 0),
                                 (POSITION_TOP, 0, -1),
                                 (POSITION_RIGHT, 1, 0),
                                 (POSITION_BOTTOM, 0, 1),
                                 (POSITION_LEFT, -1, 0)):
            surface = self.buttonSurfaces[position]
            buttons_w = surface.get_width()
            buttons_h = surface.get_height()
            padx = self.buttonPaddingX*buttons_w
            pady = self.buttonPaddingY*buttons_h
            yield (position,
                   gtk.gdk.Rectangle(
                            int((r.width-buttons_w)/2. + (padx+buttons_w)*dx),
                            int((r.height-buttons_h)/2. + (pady+buttons_h)*dy),
                            buttons_w, buttons_h))

if __name__ == "__main__":
    w = gtk.Window()
    dock = PyDock()
    w.add(dock)
    
    dock.dock(gtk.Label("Nummer 1"), POSITION_CENTER, gtk.Label("Nummer 1"))
    leaf = dock.dock(gtk.Label("Nummer 2"), POSITION_RIGHT, gtk.Label("Nummer 2"))
    leaf = leaf.dock(gtk.Label("Nummer 3"), POSITION_TOP, gtk.Label("Nummer 3"))
    leaf.dock(gtk.Label("Nummer 4"), POSITION_CENTER, gtk.Label("Nummer 4"))
    leaf = leaf.dock(gtk.Label("Nummer 5"), POSITION_LEFT, gtk.Label("Nummer 5"))
    dock.get_child().dock(gtk.Label("Nummer 6"), POSITION_TOP, gtk.Label("Nummer 6"))
    
    w.connect("delete-event", gtk.main_quit)
    w.resize(500,500)
    w.show_all()
    gtk.main()
