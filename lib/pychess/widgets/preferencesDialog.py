import gtk, gobject, sys

from pychess.System import myconf
from pychess.System import gstreamer
from pychess.Utils.const import *

firstRun = True
def run():
    global firstRun
    if firstRun:
        initialize()
        firstRun = False
    widgets["preferences"].show()

def initialize():
    
    global widgets
    class Widgets:
        def __init__ (self, glades):
            self.widgets = glades
        def __getitem__(self, key):
            return self.widgets.get_widget(key)
    widgets = Widgets(gtk.glade.XML(prefix("glade/preferences.glade")))
    
    ############################################################################
    # Window initing                                                           #
    ############################################################################
    
    def delete_event (widget, *args):
        widgets["preferences"].hide()
        return True
    widgets["preferences"].connect("delete-event", delete_event)
    widgets["preferences_close_button"].connect("clicked", delete_event)
    
    ############################################################################
    # General initing                                                          #
    ############################################################################
    
    firstName = myconf.get("firstName")
    if not firstName:
        from pwd import getpwuid
        from os import getuid
        userdata = getpwuid(getuid())
        firstName = userdata.pw_gecos
        if not firstName:
            firstName = userdata.pw_name
        myconf.set("firstName", firstName)
    
    secondName = myconf.get("secondName")
    if not secondName:
        myconf.set("secondName", _("Guest"))
    
    ############################################################################
    # Sound initing                                                            #
    ############################################################################
    
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
    
    icons = ((_("No sound"), "audio-volume-muted", "audio-volume-muted"),
             (_("Beep"), "stock_bell", "audio-x-generic"), 
             (_("Select sound file..."), "gtk-open", "document-open"))
    
    it = gtk.icon_theme_get_default()
    items = []
    for level, stock, altstock in icons:
        try:
            image = it.load_icon(stock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        except gobject.GError:
            image = it.load_icon(altstock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        items += [(image, level)]
    
    opendialog = gtk.FileChooserDialog (
        _("Open Sound File"), None,gtk.FILE_CHOOSER_ACTION_OPEN,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT)
        )
    import os
    if os.path.isdir("/usr/share/sounds"):
        opendialog.set_current_folder("/usr/share/sounds")
    elif os.path.isdir("/usr/local/share/sounds"):
        opendialog.set_current_folder("/usr/local/share/sounds")
    else: opendialog.set_current_folder(os.environ["HOME"])
    
    sound = gtk.FileFilter()
    sound.add_custom(sound.get_needed(), lambda data: data[3].startswith("audio/"))
    opendialog.add_filter(sound)
    opendialog.set_filter(sound)
    
    audioIco = it.load_icon("audio-x-generic", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
    
    def callback (combobox, index):
        if combobox.get_active() == SELECT:
            if opendialog.run() == gtk.RESPONSE_ACCEPT:
                uri = opendialog.get_uri()
                model = combobox.get_model()
                myconf.set("sounduri%d"%index, uri)
                label = os.path.split(uri)[1]
                if len(model) == 3:
                    model.append([audioIco, label])
                else:
                    model.set(model.get_iter((3,)), 1, label)
                combobox.set_active(3)
            else:
                combobox.set_active(myconf.get("soundcombo%d"%index))
            opendialog.hide()
    
    for i in range (10):
        combo = widgets["soundcombo%d"%i]
        createCombo (combo, items)
        combo.set_active(2)
        combo.connect("changed", callback, i)
        
        uri = myconf.get("sounduri%d"%i)
        if uri:
            model = combo.get_model()
            model.append([audioIco, os.path.split(uri)[1]])
            combo.set_active(3)
    
    def playCallback (button, index):
        value = widgets["soundcombo%d"%index].get_active()
        if value == BEEP:
            sys.stdout.write("\a")
            sys.stdout.flush()
        elif value == URI:
            uri = myconf.get("sounduri%d"%index)
            gstreamer.playSound(uri)
    
    for i in range (10):
        button = widgets["soundbutton%d"%i]
        button.connect("clicked", playCallback, i)
    
    def checkCallBack (*args):
        checkbox = widgets["useSystemSounds"]
        widgets["frame23"].set_property("sensitive", checkbox.get_active())
    myconf.notify_add("useSystemSounds", checkCallBack)
    if not myconf.get("useSystemSounds"):
        # We don't call it ourselves if it is true in conf, as the easy initing
        # part will do so
        checkCallBack ()
    
    ############################################################################
    # Easy initing                                                             #
    ############################################################################
    
    methodDict = {
        gtk.CheckButton: ("get_active", "set_active", "toggled"),
        gtk.Entry: ("get_text", "set_text", "changed"),
        gtk.ComboBox: ("get_active", "set_active", "changed")
    }
    
    easyWidgets = [
        "firstName", "secondName",
        "figuresInNotation", "hideTabs", "showClockAlways",
        "showLastMove", "animateMoves",
        "useSystemSounds",
    ]
    easyWidgets += ["soundcombo%d"%i for i in range (10)]
    
    class ConnectionKeeper:
        def __init__ (self, key):
            self.key = key
            self.widget = widget = widgets[key]
            self.get_value = getattr(widget, methodDict[type(widget)][0])
            self.set_value = getattr(widget, methodDict[type(widget)][1])
            self.signal = methodDict[type(widget)][2]
            
            self.set_value(myconf.get(key))
            widget.connect(self.signal,
                lambda *args: myconf.set(self.key, self.get_value()))
            myconf.notify_add(self.key,
                lambda *args: self.set_value(myconf.get(self.key)))
            
    for key in easyWidgets:
        ConnectionKeeper(key)
