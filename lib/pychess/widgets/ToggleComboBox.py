from gi.repository import Gdk, Gtk, GObject

from pychess.System.Log import log
from pychess.Utils.IconLoader import load_icon


class ToggleComboBox(Gtk.ToggleButton):

    __gsignals__ = {'changed': (GObject.SignalFlags.RUN_FIRST, None,
                                (GObject.TYPE_INT, ))}

    def __init__(self, name):
        GObject.GObject.__init__(self)
        self.set_name(name)
        self.set_relief(Gtk.ReliefStyle.NONE)

        self.label = label = Gtk.Label()
        label.set_alignment(0, 0.5)
        self.hbox = hbox = Gtk.HBox()
        self.image = Gtk.Image()
        hbox.pack_start(self.image, False, False, 0)
        hbox.pack_start(label, True, True, 0)
        arrow = Gtk.Arrow(Gtk.ArrowType.DOWN, Gtk.ShadowType.OUT)
        hbox.pack_start(arrow, False, False, 0)
        self.add(hbox)
        self.show_all()

        self.connect("button_press_event", self.button_press)
        self.connect("key_press_event", self.key_press)
        self.connect("scroll_event", self.scroll_event)

        self.menu = menu = Gtk.Menu()
        menu.connect("deactivate", self.deactivate)
        menu.attach_to_widget(self, None)

        self.markup = "", ""

        self._active = -1
        self._items = []

    def deactivate(self, widget):
        return self.set_active(False)

    def _get_active(self):
        return self._active

    def _set_active(self, active):
        if not isinstance(active, int):
            raise TypeError
        if active == self._active:
            return
        if active >= len(self._items):
            log.warning(
                "Tried to set combobox to %d, but it has only got %d items" %
                (active, len(self._items)))
            return
        oldactive = self._active
        # take care the case when last used engine was uninstalled
        self._active = (active < len(self._items) and [active] or [1])[0]
        self.emit("changed", oldactive)
        text, icon = self._items[self._active]
        self.label.set_markup(self.markup[0] + text + self.markup[1])
        if icon is not None:
            self.hbox.set_spacing(6)
            self.image.set_from_pixbuf(icon)
        else:
            self.hbox.set_spacing(0)
            self.image.clear()

    active = property(_get_active, _set_active)

    def setMarkup(self, start, end):
        self.markup = (start, end)
        text = self._items[self.active][0]
        self.label.set_markup(self.markup[0] + text + self.markup[1])

    def getMarkup(self):
        return self.markup

    def addItem(self, text, stock=None):
        if stock is None:
            item = Gtk.MenuItem(text)
        else:
            item = Gtk.ImageMenuItem()
            item.set_name(text)
            label = Gtk.Label(label=text)
            label.props.xalign = 0
            if isinstance(stock, str):
                stock = load_icon(12, stock)
            image = Gtk.Image()
            image.set_from_pixbuf(stock)
            hbox = Gtk.HBox()
            hbox.set_spacing(6)
            hbox.pack_start(image, False, False, 0)
            hbox.add(label)
            item.add(hbox)
            hbox.show_all()

        item.connect("activate", self.menu_item_activate, len(self._items))
        self.menu.append(item)
        self._items += [(text, stock)]
        item.show()
        if self.active < 0:
            self.active = 0

    def update(self, data):
        last_active = self._items[self.active][0] if self.active >= 0 else None
        new_active = -1

        self._items = []
        for i in self.menu.get_children():
            self.menu.remove(i)

        for i, row in enumerate(data):
            self.addItem(row[1], row[0])
            if last_active == row[1]:
                new_active = i
        self.active = new_active

    def menuPos(self, menu, x, y, data):
        ignore, x_loc, y_loc = self.get_window().get_origin()
        x_loc += self.get_allocation().x
        y_loc += self.get_allocation().y + self.get_allocation().height
        return (x_loc, y_loc, False)

    def scroll_event(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            if self.active > 0:
                self.active -= 1
        else:
            if self.active < len(self._items) - 1:
                self.active += 1

    def button_press(self, widget, event):
        width = self.get_allocation().width
        self.menu.set_size_request(-1, -1)
        ownWidth = self.menu.size_request().width
        self.menu.set_size_request(max(width, ownWidth), -1)
        self.set_active(True)
        self.menu.popup(None, None, self.menuPos, 1, 1, event.time)

    keys = list(map(Gdk.keyval_from_name, ("space", "KP_Space", "Return",
                                           "KP_Enter")))

    def key_press(self, widget, event):
        if event.keyval not in self.keys:
            return
        self.set_active(True)
        self.menu.popup(None, None, self.menuPos, 1, 1, event.time)
        return True

    def menu_item_activate(self, widget, index):
        self.active = index
