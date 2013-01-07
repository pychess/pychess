import gtk

class ImageMenu(gtk.EventBox):
    def __init__ (self, image, child):
        gtk.EventBox.__init__(self)
        self.add(image)
        
        self.subwindow = gtk.Window()
        self.subwindow.set_decorated(False)
        self.subwindow.set_resizable(False)
        self.subwindow.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.subwindow.add(child)
        self.subwindow.connect_after("expose-event", self.__sub_onExpose)
        self.subwindow.connect("button_press_event", self.__sub_onPress)
        self.subwindow.connect("motion_notify_event", self.__sub_onMotion)
        self.subwindow.connect("leave_notify_event", self.__sub_onMotion)
        self.subwindow.connect("delete-event", self.__sub_onDelete)
        self.subwindow.connect("focus-out-event", self.__sub_onFocusOut)
        child.show_all()
        
        self.setOpen(False)
        self.connect("button_press_event", self.__onPress)
    
    def setOpen (self, isopen):
        self.isopen = isopen
        
        if isopen:
            topwindow = self.get_parent()
            while not isinstance(topwindow, gtk.Window):
                topwindow = topwindow.get_parent()
            x, y = topwindow.window.get_position()
            x += self.get_allocation().x + self.get_allocation().width
            y += self.get_allocation().y
            self.subwindow.move(x, y)
        
        self.subwindow.props.visible = isopen
        self.set_state(self.isopen and gtk.STATE_SELECTED or gtk.STATE_NORMAL)
    
    def __onPress (self, self_, event):
        if event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
            self.setOpen(not self.isopen)
    
    
    def __sub_setGrabbed (self, grabbed):
        if grabbed and not gtk.gdk.pointer_is_grabbed():
            gtk.gdk.pointer_grab(self.subwindow.window, event_mask =
                                 gtk.gdk.LEAVE_NOTIFY_MASK|
                                 gtk.gdk.POINTER_MOTION_MASK|
                                 gtk.gdk.BUTTON_PRESS_MASK)
            gtk.gdk.keyboard_grab(self.subwindow.window)
        elif gtk.gdk.pointer_is_grabbed():
            gtk.gdk.pointer_ungrab() 
            gtk.gdk.keyboard_ungrab()
    
    def __sub_onMotion (self, subwindow, event):
        a = subwindow.get_allocation()
        self.__sub_setGrabbed(not (0 <= event.x < a.width and 0 <= event.y < a.height))
    
    def __sub_onPress (self, subwindow, event):
        a = subwindow.get_allocation()
        if not (0 <= event.x < a.width and 0 <= event.y < a.height):
            gtk.gdk.pointer_ungrab(event.time)
            self.setOpen(False)
    
    def __sub_onExpose (self, subwindow, event):
        a = subwindow.get_allocation()
        context = subwindow.window.cairo_create()
        context.set_line_width(2)
        context.rectangle (a.x, a.y, a.width, a.height)
        context.set_source_color(self.get_style().dark[gtk.STATE_NORMAL])
        context.stroke()
        self.__sub_setGrabbed(self.isopen)
    
    def __sub_onDelete (self, subwindow, event):
        self.setOpen(False)
        return True
    
    def __sub_onFocusOut (self, subwindow, event):
        self.setOpen(False)

def switchWithImage (image, dialog):
    parent = image.get_parent()
    parent.remove(image)
    imageMenu = ImageMenu(image, dialog)
    parent.add(imageMenu)
    imageMenu.show()

if __name__ == "__main__":
    win = gtk.Window()
    vbox = gtk.VBox()
    vbox.add(gtk.Label("Her er der en kat"))
    image = gtk.image_new_from_icon_name("gtk-properties", gtk.ICON_SIZE_BUTTON)
    vbox.add(image)
    vbox.add(gtk.Label("Her er der ikke en kat"))
    win.add(vbox)
    
    table = gtk.Table(2, 2)
    table.attach(gtk.Label("Minutes:"), 0, 1, 0, 1)
    spin1 = gtk.SpinButton(gtk.Adjustment(0,0,100,1))
    table.attach(spin1, 1, 2, 0, 1)
    table.attach(gtk.Label("Gain:"), 0, 1, 1, 2)
    spin2 = gtk.SpinButton(gtk.Adjustment(0,0,100,1))
    table.attach(spin2, 1, 2, 1, 2)
    table.set_border_width(6)
    
    switchWithImage(image, table)
    def onValueChanged (spin):
        print spin.get_value()
    spin1.connect("value-changed", onValueChanged)
    spin2.connect("value-changed", onValueChanged)
    
    win.show_all()
    win.connect("delete-event", gtk.main_quit)
    gtk.main()
