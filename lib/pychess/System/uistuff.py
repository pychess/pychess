import colorsys
import re
import sys
import webbrowser
import xml.etree.cElementTree as ET
# from io import BytesIO

from gi.repository import Gtk, Gdk, GObject, Pango
from gi.repository.GdkPixbuf import Pixbuf

from pychess.compat import PY3
from pychess.System import conf
from pychess.System.Log import log
from pychess.System.prefix import addDataPrefix
from pychess.widgets.ToggleComboBox import ToggleComboBox


def createCombo(combo, data=[], name=None):
    if name is not None:
        combo.set_name(name)
    lst_store = Gtk.ListStore(Pixbuf, str)
    for row in data:
        lst_store.append(row)
    combo.clear()

    combo.set_model(lst_store)
    crp = Gtk.CellRendererPixbuf()
    crp.set_property('xalign', 0)
    crp.set_property('xpad', 2)
    combo.pack_start(crp, False)
    combo.add_attribute(crp, 'pixbuf', 0)

    crt = Gtk.CellRendererText()
    crt.set_property('xalign', 0)
    crt.set_property('xpad', 4)
    combo.pack_start(crt, True)
    combo.add_attribute(crt, 'text', 1)
    # crt.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)


def updateCombo(combo, data):
    def get_active(combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return None
        return model[active][1]

    last_active = get_active(combo)
    lst_store = combo.get_model()
    lst_store.clear()
    new_active = 0
    for i, row in enumerate(data):
        lst_store.append(row)
        if last_active == row[1]:
            new_active = i
    combo.set_active(new_active)


def genColor(n, startpoint=0):
    assert n >= 1
    # This splits the 0 - 1 segment in the pizza way
    hue = (2 * n - 1) / (2.**(n - 1).bit_length()) - 1
    hue = (hue + startpoint) % 1
    # We set saturation based on the amount of green, scaled to the interval
    # [0.6..0.8]. This ensures a consistent lightness over all colors.
    rgb = colorsys.hsv_to_rgb(hue, 1, 1)
    rgb = colorsys.hsv_to_rgb(hue, 1, (1 - rgb[1]) * 0.2 + 0.6)
    # This algorithm ought to balance colors more precisely, but it overrates
    # the lightness of yellow, and nearly makes it black
    # yiq = colorsys.rgb_to_yiq(*rgb)
    # rgb = colorsys.yiq_to_rgb(.125, yiq[1], yiq[2])
    return rgb


def keepDown(scrolledWindow):
    def changed(vadjust):
        if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
            vadjust.set_value(vadjust.get_upper() - vadjust.get_page_size())
            vadjust.need_scroll = True

    scrolledWindow.get_vadjustment().connect("changed", changed)

    def value_changed(vadjust):
        vadjust.need_scroll = abs(vadjust.get_value() + vadjust.get_page_size() -
                                  vadjust.get_upper()) < vadjust.get_step_increment()

    scrolledWindow.get_vadjustment().connect("value-changed", value_changed)


# wrap analysis text column. thanks to
# http://www.islascruz.org/html/index.php?blog/show/Wrap-text-in-a-TreeView-column.html
def appendAutowrapColumn(treeview, name, **kvargs):
    cell = Gtk.CellRendererText()
    # cell.props.wrap_mode = Pango.WrapMode.WORD
    # TODO:
    # changed to ellipsize instead until "never ending grow" bug gets fixed
    # see https://github.com/pychess/pychess/issues/1054
    cell.props.ellipsize = Pango.EllipsizeMode.END
    column = Gtk.TreeViewColumn(name, cell, **kvargs)
    treeview.append_column(column)

    def callback(treeview, allocation, column, cell):
        otherColumns = [c for c in treeview.get_columns() if c != column]
        newWidth = allocation.width - sum(c.get_width() for c in otherColumns)

        hsep = GObject.Value()
        hsep.init(GObject.TYPE_INT)
        hsep.set_int(0)
        treeview.style_get_property("horizontal-separator", hsep)
        newWidth -= hsep.get_int() * (len(otherColumns) + 1) * 2
        if cell.props.wrap_width == newWidth or newWidth <= 0:
            return
        cell.props.wrap_width = newWidth
        store = treeview.get_model()
        store_iter = store.get_iter_first()
        while store_iter and store.iter_is_valid(store_iter):
            store.row_changed(store.get_path(store_iter), store_iter)
            store_iter = store.iter_next(store_iter)
        treeview.set_size_request(0, -1)
    # treeview.connect_after("size-allocate", callback, column, cell)

    scroll = treeview.get_parent()
    if isinstance(scroll, Gtk.ScrolledWindow):
        scroll.set_policy(Gtk.PolicyType.NEVER, scroll.get_policy()[1])

    return cell


METHODS = (
    # Gtk.SpinButton should be listed prior to Gtk.Entry, as it is a
    # subclass, but requires different handling
    (Gtk.SpinButton, ("get_value", "set_value", "value-changed")),
    (Gtk.Entry, ("get_text", "set_text", "changed")),
    (Gtk.Expander, ("get_expanded", "set_expanded", "notify::expanded")),
    (Gtk.ComboBox, ("get_active", "set_active", "changed")),
    # Gtk.ToggleComboBox should be listed prior to Gtk.ToggleButton, as it is a
    # subclass, but requires different handling
    (ToggleComboBox, ("_get_active", "_set_active", "changed")),
    (Gtk.IconView, ("_get_active", "_set_active", "selection-changed")),
    (Gtk.ToggleButton, ("get_active", "set_active", "toggled")),
    (Gtk.CheckMenuItem, ("get_active", "set_active", "toggled")),
    (Gtk.Range, ("get_value", "set_value", "value-changed")),
    (Gtk.TreeSortable, ("get_value", "set_value", "sort-column-changed")), )


def keep(widget, key, get_value_=None, set_value_=None, first_value=None):
    if widget is None:
        raise AttributeError("key '%s' isn't in widgets" % key)

    for class_, methods_ in METHODS:
        if isinstance(widget, class_):
            getter, setter, signal = methods_
            break
    else:
        raise AttributeError("I don't have any knowledge of type: '%s'" %
                             widget)

    if get_value_:
        def get_value():
            return get_value_(widget)
    else:
        get_value = getattr(widget, getter)

    if set_value_:
        def set_value(v):
            return set_value_(widget, v)
    else:
        set_value = getattr(widget, setter)

    def setFromConf():
        try:
            v = conf.getStrict(key)
        except TypeError:
            log.warning("uistuff.keep.setFromConf: Key '%s' from conf had the wrong type '%s', ignored" %
                        (key, type(conf.getStrict(key))))
            if first_value is not None:
                conf.set(key, first_value)
            else:
                conf.set(key, get_value())
        else:
            set_value(v)

    def callback(*args):
        if not conf.hasKey(key) or conf.getStrict(key) != get_value():
            conf.set(key, get_value())

    widget.connect(signal, callback)
    conf.notify_add(key, lambda *args: setFromConf())

    if conf.hasKey(key):
        setFromConf()
    elif first_value is not None:
        conf.set(key, first_value)


# loadDialogWidget() and saveDialogWidget() are similar to uistuff.keep() but are needed
# for saving widget values for Gtk.Dialog instances that are loaded with different
# sets of values/configurations and which also aren't instant save like in
# uistuff.keep(), but rather are saved later if and when the user clicks
# the dialog's OK button
def loadDialogWidget(widget,
                     widget_name,
                     config_number,
                     get_value_=None,
                     set_value_=None,
                     first_value=None):
    key = widget_name + "-" + str(config_number)

    if widget is None:
        raise AttributeError("key '%s' isn't in widgets" % widget_name)

    for class_, methods_ in METHODS:
        if isinstance(widget, class_):
            getter, setter, signal = methods_
            break
    else:
        if set_value_ is None:
            raise AttributeError("I don't have any knowledge of type: '%s'" %
                                 widget)

    if get_value_:
        def get_value():
            return get_value_(widget)
    else:
        get_value = getattr(widget, getter)

    if set_value_:
        def set_value(v):
            return set_value_(widget, v)
    else:
        set_value = getattr(widget, setter)

    if conf.hasKey(key):
        try:
            v = conf.getStrict(key)
        except TypeError:
            log.warning("uistuff.loadDialogWidget: Key '%s' from conf had the wrong type '%s', ignored" %
                        (key, type(conf.getStrict(key))))
            if first_value is not None:
                conf.set(key, first_value)
            else:
                conf.set(key, get_value())
        else:
            set_value(v)
    elif first_value is not None:
        conf.set(key, first_value)
        set_value(conf.getStrict(key))
    else:
        log.warning("Didn't load widget \"%s\": no conf value and no first_value arg" % widget_name)


def saveDialogWidget(widget, widget_name, config_number, get_value_=None):
    key = widget_name + "-" + str(config_number)

    if widget is None:
        raise AttributeError("key '%s' isn't in widgets" % widget_name)

    for class_, methods_ in METHODS:
        if isinstance(widget, class_):
            getter, setter, signal = methods_
            break
    else:
        if get_value_ is None:
            raise AttributeError("I don't have any knowledge of type: '%s'" %
                                 widget)

    if get_value_:
        def get_value():
            return get_value_(widget)
    else:
        get_value = getattr(widget, getter)

    if not conf.hasKey(key) or conf.getStrict(key) != get_value():
        conf.set(key, get_value())


POSITION_NONE, POSITION_CENTER, POSITION_GOLDEN = range(3)


def keepWindowSize(key,
                   window,
                   defaultSize=None,
                   defaultPosition=POSITION_NONE):
    """ You should call keepWindowSize before show on your windows """

    key = key + "window"

    def savePosition(window, *event):
        log.debug("keepWindowSize.savePosition: %s" % window.get_title())
        width = window.get_allocation().width
        height = window.get_allocation().height
        x_loc, y_loc = window.get_position()

        if width <= 0:
            log.error("Setting width = '%d' for %s to conf" % (width, key))
        if height <= 0:
            log.error("Setting height = '%d' for %s to conf" % (height, key))

        log.debug("Saving window position width=%s height=%s x=%s y=%s" %
                  (width, height, x_loc, y_loc))
        conf.set(key + "_width", width)
        conf.set(key + "_height", height)
        conf.set(key + "_x", x_loc)
        conf.set(key + "_y", y_loc)

        return False

    window.connect("delete-event", savePosition, "delete-event")

    def loadPosition(window):
        # log.debug("keepWindowSize.loadPosition: %s" % window.title)
        width, height = window.get_size_request()

        if conf.hasKey(key + "_width") and conf.hasKey(key + "_height"):
            width = conf.getStrict(key + "_width")
            height = conf.getStrict(key + "_height")
            log.debug("Resizing window to width=%s height=%s" %
                      (width, height))
            window.resize(width, height)

        elif defaultSize:
            width, height = defaultSize
            log.debug("Resizing window to width=%s height=%s" %
                      (width, height))
            window.resize(width, height)

        elif key == "mainwindow":
            monitor_x, monitor_y, monitor_width, monitor_height = getMonitorBounds(
            )
            width = int(monitor_width / 2)
            height = int(monitor_height / 4) * 3
            log.debug("Resizing window to width=%s height=%s" %
                      (width, height))
            window.resize(width, height)

        elif key == "preferencesdialogwindow":
            window.resize(1, 1)

        if conf.hasKey(key + "_x") and conf.hasKey(key + "_y"):
            log.debug("Moving window to x=%s y=%s" %
                      (conf.getStrict(key + "_x"), conf.getStrict(key + "_y")))
            window.move(conf.getStrict(key + "_x"), conf.getStrict(key + "_y"))

        elif defaultPosition in (POSITION_CENTER, POSITION_GOLDEN):
            monitor_x, monitor_y, monitor_width, monitor_height = getMonitorBounds(
            )
            x_loc = int(monitor_width / 2 - width / 2) + monitor_x
            if defaultPosition == POSITION_CENTER:
                y_loc = int(monitor_height / 2 - height / 2) + monitor_y
            else:
                # Place the window on the upper golden ratio line
                y_loc = int(monitor_height / 2.618 - height / 2) + monitor_y
            log.debug("Moving window to x=%s y=%s" % (x_loc, y_loc))
            window.move(x_loc, y_loc)

    loadPosition(window)

    # In rare cases, gtk throws some gtk_size_allocation error, which is
    # probably a race condition. To avoid the window forgets its size in
    # these cases, we add this extra hook
    def callback(window):
        loadPosition(window)

    onceWhenReady(window, callback)


# Some properties can only be set, once the window is sufficiently initialized,
# This function lets you queue your request until that has happened.
def onceWhenReady(window, func, *args, **kwargs):
    def cb(window, alloc, func, *args, **kwargs):
        func(window, *args, **kwargs)
        window.disconnect(handler_id)

    handler_id = window.connect_after("size-allocate", cb, func, *args, **
                                      kwargs)


def getMonitorBounds():
    screen = Gdk.Screen.get_default()
    root_window = screen.get_root_window()
    ptr_window, mouse_x, mouse_y, mouse_mods = root_window.get_pointer()
    current_monitor_number = screen.get_monitor_at_point(mouse_x, mouse_y)
    monitor_geometry = screen.get_monitor_geometry(current_monitor_number)
    return monitor_geometry.x, monitor_geometry.y, monitor_geometry.width, monitor_geometry.height


tooltip = Gtk.Window(Gtk.WindowType.POPUP)
tooltip.set_name('gtk-tooltip')
tooltip.ensure_style()
tooltipStyle = tooltip.get_style()


def makeYellow(box):
    def on_box_expose_event(box, context):
        # box.style.paint_flat_box (box.window,
        #    Gtk.StateType.NORMAL, Gtk.ShadowType.NONE, None, box, "tooltip",
        #    box.allocation.x, box.allocation.y,
        #    box.allocation.width, box.allocation.height)
        pass

    def cb(box):
        box.set_style(tooltipStyle)
        box.connect("draw", on_box_expose_event)

    onceWhenReady(box, cb)


linkre = re.compile("http://(?:www\.)?\w+\.\w{2,4}[^\s]+")
emailre = re.compile("[\w\.]+@[\w\.]+\.\w{2,4}")


def initTexviewLinks(textview, text):
    tags = []
    textbuffer = textview.get_buffer()

    while True:
        linkmatch = linkre.search(text)
        emailmatch = emailre.search(text)
        if not linkmatch and not emailmatch:
            textbuffer.insert(textbuffer.get_end_iter(), text)
            break

        if emailmatch and (not linkmatch or emailmatch.start() < linkmatch.start()):
            e_start = emailmatch.start()
            e_end = emailmatch.end()
            msg_type = "email"
        else:
            e_start = linkmatch.start()
            e_end = linkmatch.end()
            if text[e_end - 1] == ".":
                e_end -= 1
            msg_type = "link"
        textbuffer.insert(textbuffer.get_end_iter(), text[:e_start])

        tag = textbuffer.create_tag(None,
                                    foreground="blue",
                                    underline=Pango.Underline.SINGLE)
        tags.append([tag, text[e_start:e_end], msg_type, textbuffer.get_end_iter()])

        textbuffer.insert_with_tags(textbuffer.get_end_iter(), text[e_start:e_end], tag)

        tags[-1].append(textbuffer.get_end_iter())

        text = text[e_end:]

    def on_press_in_textview(textview, event):
        tv_iter = textview.get_iter_at_location(int(event.x), int(event.y))
        if not tv_iter:
            return

        # https://gramps-project.org/bugs/view.php?id=9335
        if not isinstance(tv_iter, Gtk.TextIter):
            tv_iter = tv_iter[1]

        for tag, link, msg_type, s, e in tags:
            if tv_iter.has_tag(tag):
                tag.props.foreground = "red"
                break

    def on_release_in_textview(textview, event):
        tv_iter = textview.get_iter_at_location(int(event.x), int(event.y))
        if not tv_iter:
            return

        # https://gramps-project.org/bugs/view.php?id=9335
        if not isinstance(tv_iter, Gtk.TextIter):
            tv_iter = tv_iter[1]

        for tag, link, msg_type, s, e in tags:
            if tv_iter and tv_iter.has_tag(tag) and \
                    tag.props.foreground_Gdk.red == 0xffff:
                if msg_type == "link":
                    webbrowser.open(link)
                else:
                    webbrowser.open("mailto:" + link)
            tag.props.foreground = "blue"

    stcursor = Gdk.Cursor(Gdk.CursorType.XTERM)
    linkcursor = Gdk.Cursor(Gdk.CursorType.HAND2)

    def on_motion_in_textview(textview, event):
        # textview.get_window().get_pointer()
        tv_iter = textview.get_iter_at_location(int(event.x), int(event.y))
        if not tv_iter:
            return

        # https://gramps-project.org/bugs/view.php?id=9335
        if not isinstance(tv_iter, Gtk.TextIter):
            tv_iter = tv_iter[1]

        for tag, link, msg_type, s, e in tags:
            if tv_iter.has_tag(tag):
                textview.get_window(Gtk.TextWindowType.TEXT).set_cursor(
                    linkcursor)
                break
        else:
            textview.get_window(Gtk.TextWindowType.TEXT).set_cursor(stcursor)

    textview.connect("motion-notify-event", on_motion_in_textview)
    textview.connect("leave_notify_event", on_motion_in_textview)
    textview.connect("button_press_event", on_press_in_textview)
    textview.connect("button_release_event", on_release_in_textview)


no_gettext = False


class GladeWidgets:
    """ A simple class that wraps a the glade get_widget function
        into the python __getitem__ version """

    def __init__(self, filename):
        # TODO: remove this when upstream fixes translations with Python3+Windows
        if PY3 and sys.platform == "win32" and not no_gettext:
            tree = ET.parse(addDataPrefix("glade/%s" % filename))
            for node in tree.iter():
                if 'translatable' in node.attrib:
                    node.text = _(node.text)
                if node.get('name') in ('pixbuf', 'logo'):
                    node.text = addDataPrefix("glade/%s" % node.text)
            # temp_file = BytesIO()
            temp_file = addDataPrefix("glade/%s.temp" % filename)
            tree.write(temp_file, encoding='utf-8', xml_declaration=True)
            # xml_text = temp_file.getvalue().decode()
            # self.builder = Gtk.Builder.new_from_string(xml_text, len(xml_text))
            self.builder = Gtk.Builder()
            self.builder.add_from_file(temp_file)
        else:
            self.builder = Gtk.Builder()
            if not no_gettext:
                self.builder.set_translation_domain("pychess")
            self.builder.add_from_file(addDataPrefix("glade/%s" % filename))

    def __getitem__(self, key):
        return self.builder.get_object(key)

    def getGlade(self):
        return self.builder
