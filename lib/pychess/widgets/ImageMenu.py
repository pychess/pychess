from __future__ import print_function
from gi.repository import Gtk, Gdk, GObject


class ImageMenu(Gtk.EventBox):
    def __init__(self, image, child):
        GObject.GObject.__init__(self)
        self.add(image)

        self.subwindow = Gtk.Window()
        self.subwindow.set_decorated(False)
        self.subwindow.set_resizable(False)
        self.subwindow.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.subwindow.add(child)
        self.subwindow.connect_after("draw", self.__sub_onExpose)
        self.subwindow.connect("button_press_event", self.__sub_onPress)
        # self.subwindow.connect("motion_notify_event", self.__sub_onMotion)
        # self.subwindow.connect("leave_notify_event", self.__sub_onMotion)
        # self.subwindow.connect("delete-event", self.__sub_onDelete)
        self.subwindow.connect("focus-out-event", self.__sub_onFocusOut)
        child.show_all()

        self.setOpen(False)
        self.connect("button_press_event", self.__onPress)

    def setOpen(self, isopen):
        self.isopen = isopen

        if isopen:
            topwindow = self.get_parent()
            while not isinstance(topwindow, Gtk.Window):
                topwindow = topwindow.get_parent()
            x_loc, y_loc = topwindow.get_window().get_position()
            x_loc += self.get_allocation().x + self.get_allocation().width
            y_loc += self.get_allocation().y
            self.subwindow.move(x_loc, y_loc)

        self.subwindow.props.visible = isopen
        self.set_state(self.isopen and Gtk.StateType.SELECTED or
                       Gtk.StateType.NORMAL)

    def __onPress(self, self_, event):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.setOpen(not self.isopen)

    def __sub_setGrabbed(self, grabbed):
        if grabbed and not Gdk.pointer_is_grabbed():
            Gdk.pointer_grab(self.subwindow.get_window(), True,
                             Gdk.EventMask.LEAVE_NOTIFY_MASK |
                             Gdk.EventMask.POINTER_MOTION_MASK |
                             Gdk.EventMask.BUTTON_PRESS_MASK, None, None,
                             Gdk.CURRENT_TIME)
            Gdk.keyboard_grab(self.subwindow.get_window(), True,
                              Gdk.CURRENT_TIME)
        elif Gdk.pointer_is_grabbed():
            Gdk.pointer_ungrab(Gdk.CURRENT_TIME)
            Gdk.keyboard_ungrab(Gdk.CURRENT_TIME)

    def __sub_onMotion(self, subwindow, event):
        allocation = subwindow.get_allocation()
        self.__sub_setGrabbed(not (0 <= event.x < allocation.width and 0 <= event.y <
                                   allocation.height))

    def __sub_onPress(self, subwindow, event):
        allocation = subwindow.get_allocation()
        if not (0 <= event.x < allocation.width and 0 <= event.y < allocation.height):
            Gdk.pointer_ungrab(event.time)
            self.setOpen(False)

    def __sub_onExpose(self, subwindow, ctx):
        allocation = subwindow.get_allocation()
        context = subwindow.get_window().cairo_create()
        context.set_line_width(2)
        context.rectangle(allocation.x, allocation.y,
                          allocation.width, allocation.height)
        style_ctxt = self.get_style_context()
        color = style_ctxt.lookup_color("p_dark_color")[1]
        red, green, blue, alpha = color.red, color.green, color.blue, color.alpha
        context.set_source_rgba(red, green, blue, alpha)
        context.stroke()
        # self.__sub_setGrabbed(self.isopen)

    def __sub_onDelete(self, subwindow, event):
        self.setOpen(False)
        return True

    def __sub_onFocusOut(self, subwindow, event):
        self.setOpen(False)


def switchWithImage(image, dialog):
    parent = image.get_parent()
    parent.remove(image)
    imageMenu = ImageMenu(image, dialog)
    parent.add(imageMenu)
    imageMenu.show()


if __name__ == "__main__":
    win = Gtk.Window()
    vbox = Gtk.VBox()
    vbox.add(Gtk.Label(label="Her er der en kat"))
    image = Gtk.Image.new_from_icon_name("gtk-properties", Gtk.IconSize.BUTTON)
    vbox.add(image)
    vbox.add(Gtk.Label(label="Her er der ikke en kat"))
    win.add(vbox)

    table = Gtk.Table(2, 2)
    table.attach(Gtk.Label(label="Minutes:"), 0, 1, 0, 1)
    spin1 = Gtk.SpinButton()
    spin1.set_adjustment(Gtk.Adjustment(0, 0, 100, 1))
    table.attach(spin1, 1, 2, 0, 1)
    table.attach(Gtk.Label(label="Gain:"), 0, 1, 1, 2)
    spin2 = Gtk.SpinButton()
    spin2.set_adjustment(Gtk.Adjustment(0, 0, 100, 1))
    table.attach(spin2, 1, 2, 1, 2)
    table.set_border_width(6)

    switchWithImage(image, table)

    def onValueChanged(spin):
        print(spin.get_value())

    spin1.connect("value-changed", onValueChanged)
    spin2.connect("value-changed", onValueChanged)

    win.show_all()
    win.connect("delete-event", Gtk.main_quit)
    Gtk.main()
