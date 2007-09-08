
import gtk, pango

from pychess.System import conf
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
    gtk.Expander: ("get_expanded", "set_expanded", "notify::expanded"),
    gtk.CheckButton: ("get_active", "set_active", "toggled"),
    gtk.RadioButton: ("get_active", "set_active", "toggled"),
    gtk.ComboBox: ("get_active", "set_active", "changed"),
    ToggleComboBox: ("_get_active", "_set_active", "changed")
}

def keep (widget, key, get_value_=None, set_value_=None, first_value=None):
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
    
    if first_value != None:
        conf.set(key, first_value)
    if conf.hasKey(key):
        set_value(conf.getStrict(key))
    
    signal = methodDict[type(widget)][2]
    widget.connect(signal, lambda *args: conf.set(key, get_value()))
    conf.notify_add(key, lambda *args: set_value(conf.getStrict(key)))

tooltip = gtk.Tooltips()
tooltip.force_window()
if hasattr(tooltip, 'tip_window') and tooltip.tip_window != None:
    tooltip.tip_window.ensure_style()
    tooltipStyle = tooltip.tip_window.get_style()
else:
    tooltipStyle = None

def makeYellow (box):
    if tooltipStyle:
        box.set_style(tooltipStyle)
    def on_box_expose_event (box, event):
        allocation = box.allocation
        box.style.paint_flat_box (box.window,
            gtk.STATE_NORMAL, gtk.SHADOW_NONE, None, box, "tooltip",
            allocation.x, allocation.y, allocation.width, allocation.height)
        if not hasattr(box, "hasHadFirstDraw") or not box.hasHadFirstDraw:
            box.queue_draw()
            box.hasHadFirstDraw = True
    box.connect("expose-event", on_box_expose_event)

