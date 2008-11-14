
import re
import webbrowser
import colorsys
from math import log as ln, ceil
import random
import Queue

import gobject
import gtk, pango

from pychess.System import glock
from pychess.System import conf
from pychess.System.Log import log
from pychess.System.ThreadPool import pool
from pychess.System.prefix import addDataPrefix
from pychess.widgets.ToggleComboBox import ToggleComboBox

def createCombo (combo, data):
    ls = gtk.ListStore(gtk.gdk.Pixbuf, str)
    for icon, label in data:
        ls.append([icon, label])
    combo.clear()
    
    combo.set_model(ls)
    crp = gtk.CellRendererPixbuf()
    crp.set_property('xalign',0)
    crp.set_property('xpad', 2)
    combo.pack_start(crp, False)
    combo.add_attribute(crp, 'pixbuf', 0)
    
    crt = gtk.CellRendererText()
    crt.set_property('xalign',0)
    crt.set_property('xpad', 4)
    combo.pack_start(crt, True)
    combo.add_attribute(crt, 'text', 1)
    #crt.set_property('ellipsize', pango.ELLIPSIZE_MIDDLE)


def updateCombo (combo, data):
    def get_active(combobox):
        model = combobox.get_model()
        active = combobox.get_active()
        if active < 0:
            return None
        return model[active][1]

    last_active = get_active(combo)
    ls = combo.get_model()
    ls.clear()
    new_active = 0
    for i, row in enumerate(data):
        ls.append(row)
        if last_active == row[1]:
            new_active = i
    combo.set_active(new_active)


def genColor (n, startpoint=0):
    assert n >= 1
    # This splits the 0 - 1 segment in the pizza way
    h = (2*n-1)/(2**ceil(ln(n)/ln(2)))-1
    h = (h + startpoint) % 1
    # We set saturation based on the amount of green, in the range 0.6 to 0.8
    rgb = colorsys.hsv_to_rgb(h, 1, 1)
    rgb = colorsys.hsv_to_rgb(h, 1, (1-rgb[1])*0.2+0.6)
    return rgb



def keepDown (scrolledWindow):
    def changed (vadjust):
        if not hasattr(vadjust, "need_scroll") or vadjust.need_scroll:
            vadjust.set_value(vadjust.upper-vadjust.page_size)
            vadjust.need_scroll = True
    scrolledWindow.get_vadjustment().connect("changed", changed)
        
    def value_changed (vadjust):
        vadjust.need_scroll = abs(vadjust.value + vadjust.page_size - \
                vadjust.upper) < vadjust.step_increment
    scrolledWindow.get_vadjustment().connect("value-changed", value_changed)



def appendAutowrapColumn (treeview, defwidth, name, **kvargs):
    cell = gtk.CellRendererText()
    cell.props.wrap_mode = pango.WRAP_WORD
    cell.props.wrap_width = defwidth
    column = gtk.TreeViewColumn(name, cell, **kvargs)
    treeview.append_column(column)
    
    def callback (treeview, allocation, column, cell):
        otherColumns = (c for c in treeview.get_columns() if c != column)
        newWidth = allocation.width - sum(c.get_width() for c in otherColumns)
        newWidth -= treeview.style_get_property("horizontal-separator") * 2
        if cell.props.wrap_width == newWidth or newWidth <= 0:
            return
        cell.props.wrap_width = newWidth
        store = treeview.get_model()
        iter = store.get_iter_first()
        while iter and store.iter_is_valid(iter):
            store.row_changed(store.get_path(iter), iter)
            iter = store.iter_next(iter)
        treeview.set_size_request(0,-1)
    treeview.connect_after("size-allocate", callback, column, cell)
    
    return cell


methods = (
    # gtk.SpinButton should be listed prior to gtk.Entry, as it is a
    # subclass, but requires different handling
    (gtk.SpinButton, ("get_value", "set_value", "value-changed")),
    (gtk.Entry, ("get_text", "set_text", "changed")),
    (gtk.Expander, ("get_expanded", "set_expanded", "notify::expanded")),
    (gtk.ComboBox, ("get_active", "set_active", "changed")),
    # gtk.ToggleComboBox should be listed prior to gtk.ToggleButton, as it is a
    # subclass, but requires different handling
    (ToggleComboBox, ("_get_active", "_set_active", "changed")),
    (gtk.ToggleButton, ("get_active", "set_active", "toggled")),
    (gtk.CheckMenuItem, ("get_active", "set_active", "toggled")),
    (gtk.Range, ("get_value", "set_value", "value-changed")),
)

def keep (widget, key, get_value_=None, set_value_=None, first_value=None):
    if widget == None:
        raise AttributeError, "key '%s' isn't in widgets" % key
    
    for class_, methods_ in methods:
        if isinstance(widget, class_):
            getter, setter, signal = methods_
            break
    else:
        raise AttributeError, "I don't have any knowledge of type: '%s'" % widget
    
    if get_value_:
        get_value = lambda: get_value_(widget)
    else:
        get_value = getattr(widget, getter)
    
    if set_value_:
        set_value = lambda v: set_value_(widget, v)
    else:
        set_value = getattr(widget, setter)
    
    def setFromConf ():
        try:
            set_value(conf.getStrict(key))
        except TypeError:
            log.warn("Key '%s' from conf had the wrong type '%s', ignored" % 
                     (key, type(conf.getStrict(key))))
            if first_value != None:
                conf.set(key, first_value)
            else: conf.set(key, get_value())
    if conf.hasKey(key):
        setFromConf()
    elif first_value != None:
        conf.set(key, first_value)
    
    def callback(*args):
        if not conf.hasKey(key) or conf.getStrict(key) != get_value():
            conf.set(key, get_value())
    widget.connect(signal, callback)
    conf.notify_add(key, lambda *args: setFromConf)



POSITION_NONE, POSITION_CENTER, POSITION_GOLDEN = range(3)
def keepWindowSize (key, window, defaultSize=None, defaultPosition=POSITION_NONE):
    key = key + "window"
    
    def savePosition (window, *event):
        
        width = window.get_allocation().width
        height = window.get_allocation().height
        x, y = window.get_position()
        
        if width <= 0:
            log.error("Setting width = '%d' for %s to conf" % (width,key))
        if height <= 0:
            log.error("Setting height = '%d' for %s to conf" % (height,key))
        
        conf.set(key+"_width",  width)
        conf.set(key+"_height", height)
        conf.set(key+"_x", x)
        conf.set(key+"_y", y)
    window.connect("delete-event", savePosition, "delete-event")
    
    def loadPosition (window):
        if conf.hasKey(key+"_width") and conf.hasKey(key+"_height"):
            width = conf.getStrict(key+"_width")
            height = conf.getStrict(key+"_height")
            window.set_size_request(width, height)
        elif defaultSize:
            width, height = defaultSize
            window.set_size_request(width, height)
        
        if conf.hasKey(key+"_x") and conf.hasKey(key+"_y"):
            window.move(conf.getStrict(key+"_x"),
                        conf.getStrict(key+"_y"))
        
        elif defaultPosition in (POSITION_CENTER, POSITION_GOLDEN):
            width, height = window.get_size_request()
            x = int(gtk.gdk.screen_width()/2-width/2)
            if defaultPosition == POSITION_CENTER:
                y = int(gtk.gdk.screen_height()/2-height/2)
            else:
                # Place the window on the upper golden ratio line
                y = int(gtk.gdk.screen_height()/2.618-height/2)
            window.move(x, y)
    loadPosition(window)
    
    # In rare cases, gtk throws some gtk_size_allocation error, which is
    # probably a race condition. To avoid the window forgets its size in
    # these cases, we add this extra hook
    def callback (window, *args):
        # Disconnect ourselves to get run_once effect
        window.disconnect(handle_id)
        loadPosition(window)
        gobject.idle_add(window.set_size_request, -1, -1)
    handle_id = window.connect("size-allocate", callback)




tooltip = gtk.Window(gtk.WINDOW_POPUP)
tooltip.set_name('gtk-tooltip')
tooltip.ensure_style()
tooltipStyle = tooltip.get_style()

def makeYellow (box):
    def on_box_expose_event (box, event):
        box.style.paint_flat_box (box.window,
            gtk.STATE_NORMAL, gtk.SHADOW_NONE, None, box, "tooltip",
            box.allocation.x, box.allocation.y,
            box.allocation.width, box.allocation.height)
    def cb (box, a):
        box.set_style(tooltipStyle)
        box.connect("expose-event", on_box_expose_event)
    box.connect_after("size-allocate", cb)




linkre = re.compile("http://(?:www\.)?\w+\.\w{2,4}[^\s]+")
emailre = re.compile("[\w\.]+@[\w\.]+\.\w{2,4}")
def initTexviewLinks (textview, text):
    tags = []
    textbuffer = textview.get_buffer()
    
    while True:
        linkmatch = linkre.search(text)
        emailmatch = emailre.search(text)
        if not linkmatch and not emailmatch:
            textbuffer.insert (textbuffer.get_end_iter(), text)
            break
        
        if emailmatch and (not linkmatch or \
                emailmatch.start() < linkmatch.start()):
            s = emailmatch.start()
            e = emailmatch.end()
            type = "email"
        else:
            s = linkmatch.start()
            e = linkmatch.end()
            if text[e-1] == ".":
                e -= 1
            type = "link"
        textbuffer.insert (textbuffer.get_end_iter(), text[:s])
        
        tag = textbuffer.create_tag (None, foreground="blue",
                underline=pango.UNDERLINE_SINGLE)
        tags.append([tag, text[s:e], type, textbuffer.get_end_iter()])
        
        textbuffer.insert_with_tags (
                textbuffer.get_end_iter(), text[s:e], tag)
        
        tags[-1].append(textbuffer.get_end_iter())
        
        text = text[e:]
    
    def on_press_in_textview (textview, event):
        iter = textview.get_iter_at_location (int(event.x), int(event.y))
        if not iter: return
        for tag, link, type, s, e in tags:
            if iter.has_tag(tag):
                tag.props.foreground = "red"
                break
    
    def on_release_in_textview (textview, event):
        iter = textview.get_iter_at_location (int(event.x), int(event.y))
        if not iter: return
        for tag, link, type, s, e in tags:
            if iter and iter.has_tag(tag) and \
                    tag.props.foreground_gdk.red == 65535:
                if type == "link":
                    webbrowser.open(link)
                else: webbrowser.open("mailto:"+link)
            tag.props.foreground = "blue"
    
    stcursor = gtk.gdk.Cursor(gtk.gdk.XTERM)
    linkcursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
    def on_motion_in_textview(textview, event):
        textview.window.get_pointer()
        iter = textview.get_iter_at_location (int(event.x), int(event.y))
        if not iter: return
        for tag, link, type, s, e in tags:
            if iter.has_tag(tag):
                textview.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor (
                        linkcursor)
                break
        else: textview.get_window(gtk.TEXT_WINDOW_TEXT).set_cursor(stcursor)
    
    textview.connect ("motion-notify-event", on_motion_in_textview)
    textview.connect ("leave_notify_event", on_motion_in_textview)
    textview.connect("button_press_event", on_press_in_textview)
    textview.connect("button_release_event", on_release_in_textview)



def initLabelLinks (text, url):
    label = gtk.Label()
    
    eventbox = gtk.EventBox()
    label.set_markup("<span color='blue'><u>%s</u></span>" % text)
    eventbox.add(label)
    
    def released (eventbox, event):
        webbrowser.open(url)
        label.set_markup("<span color='blue'><u>%s</u></span>" % text)
    eventbox.connect("button_release_event", released)
    
    def pressed (eventbox, event):
        label.set_markup("<span color='red'><u>%s</u></span>" % text)
    eventbox.connect("button_press_event", pressed)
    
    eventbox.connect_after("realize",
        lambda w: w.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2)))
    
    return eventbox


cachedGlades = {}
def cacheGladefile(filename):
    """ gtk.glade automatically caches the file, so we only need to use this
        file once """
    if filename not in cachedGlades:
        cachedGlades[filename] = Queue.Queue()
        def readit ():
            glade = gtk.glade.XML(addDataPrefix("glade/%s" % filename))
            cachedGlades[filename].put(glade)
        pool.start(readit)

class GladeWidgets:
    """ A simple class that wraps a the glade get_widget function
        into the python __getitem__ version """
    def __init__ (self, filename):
        self.glade = None
        try:
            if filename in cachedGlades:
                self.glade = cachedGlades[filename].get(block=False)
        except Queue.Empty:
            pass
        
        if not self.glade:
            glock.acquire()
            self.glade = gtk.glade.XML(addDataPrefix("glade/%s" % filename))
            glock.release()
        
        self.extras = {}
    
    def __getitem__(self, key):
        if key in self.extras:
            return self.extras[key]
        return self.glade.get_widget(key)
    
    def __setitem__(self, key, widget):
        self.extras[key] = widget
    
    def getGlade (self):
        return self.glade

