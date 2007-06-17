
import gtk, pango

from pychess.System import myconf
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
    crt.set_property('ellipsize', pango.ELLIPSIZE_MIDDLE)

methodDict = {
    gtk.Entry: ("get_text", "set_text", "changed"),
    gtk.CheckButton: ("get_active", "set_active", "toggled"),
    gtk.RadioButton: ("get_active", "set_active", "toggled"),
    gtk.ComboBox: ("get_active", "set_active", "changed"),
    ToggleComboBox: ("_get_active", "_set_active", "changed")
}

def keep (widget, key, get_value_=None, set_value_=None):
    if widget == None:
        raise AttributeError, "key '%s' isn't in widgets" % key
    
    if get_value_:
        get_value = lambda: get_value_(widget)
    else:
        get_value = getattr(widget, methodDict[type(widget)][0])
    
    if set_value_:
        set_value = lambda v: set_value_(widget, v)
    else:
        set_value = getattr(widget, methodDict[type(widget)][1])
    
    set_value(myconf.get(key))
    
    signal = methodDict[type(widget)][2]
    widget.connect(signal, lambda *args: myconf.set(key, get_value()))
    myconf.notify_add(key, lambda *args: set_value(myconf.get(key)))
