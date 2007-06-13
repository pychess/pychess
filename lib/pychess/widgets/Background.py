import gtk, cairo, pango
from os import path, mkdir
from pychess.Utils.const import prefix
from array import array
import math
from ToggleComboBox import ToggleComboBox
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE
import ionest

class TaskerManager (gtk.Table):
    
    def __init__ (self):
        gtk.Table.__init__(self)
        self.border = 20
        self.connect("expose_event", self.expose)
        self.connect("style-set", self.newtheme)
        self.clearpath = prefix("glade/clear.png")
        self.set_homogeneous(True)
        self.surface = None
    
    def expose (self, widget, event):
        cr = widget.window.cairo_create()
        cr.rectangle (event.area.x, event.area.y, event.area.width, event.area.height)
        if not self.surface:
            self.newtheme(self, self.get_style())
        cr.set_source_surface(self.surface, 0, 0)
        pattern = cr.get_source()
        pattern.set_extend(cairo.EXTEND_REPEAT)
        cr.fill()
        
        for widget in self.widgets:
            x = widget.get_allocation().x
            y = widget.get_allocation().y
            width = widget.get_allocation().width
            height = widget.get_allocation().height
            
            cr.move_to  (x-self.border, y)
            cr.curve_to (x-self.border, y-self.border/2.,
                         x-self.border/2., y-self.border,
                         x, y-self.border)
            cr.line_to  (x+width, y-self.border)
            cr.curve_to (x+width+self.border/2., y-self.border,
                         x+width+self.border, y-self.border/2.,
                         x+width+self.border, y)
            cr.line_to  (x+width+self.border, y+height)
            cr.curve_to (x+width+self.border, y+height+self.border/2.,
                         x+width+self.border/2., y+height+self.border,
                         x+width, y+height+self.border)
            cr.line_to  (x, y+height+self.border)
            cr.curve_to (x-self.border/2., y+height+self.border,
                         x-self.border, y+height+self.border/2.,
                         x-self.border, y+height)
            
            cr.set_source_color(self.get_style().bg[gtk.STATE_NORMAL])
            cr.fill()
            
            cr.rectangle (x-self.border, y+height-29, width+self.border*2, 29)
            cr.set_source_color(self.get_style().dark[gtk.STATE_NORMAL])
            cr.fill()
    
    def newtheme (self, widget, oldstyle):
        
        lnew = self.get_style().bg[gtk.STATE_NORMAL]
        dnew = self.get_style().dark[gtk.STATE_NORMAL]
        
        if oldstyle:
            lold = oldstyle.bg[gtk.STATE_NORMAL]
            dold = oldstyle.dark[gtk.STATE_NORMAL]
            
            if lnew.red == lold.red and \
               lnew.green == lold.green and \
               lnew.blue == lold.blue and \
               dnew.red == dold.red and \
               dnew.green == dold.green and \
               dnew.blue == dold.blue:
                return
        
        dark = array('B',map(lambda x: x/256, (dnew.red, dnew.green, dnew.blue)))
        
        pydir = path.expanduser("~/.pychess/")
        temppngdir = path.join(pydir,"temp.png")
        if not path.isdir(pydir):
            mkdir(pydir)
        if path.isfile(temppngdir):
            f = open(temppngdir)
            b,g,r = [ord(c) for c in f.read(3)]
            if dark[0] == r and dark[1] == g and dark[2] == b:
                self.surface = cairo.ImageSurface.create_from_png(f)
                return
        
        surface = cairo.ImageSurface.create_from_png(self.clearpath)
        if hasattr(surface, "get_data_as_rgba"):
            buffer = surface.get_data_as_rgba()
        else: buffer = surface.get_data()
        
        data = array ('B', 'a' * surface.get_width() * surface.get_height() * 4)
        surf = cairo.ImageSurface.create_for_data (data, cairo.FORMAT_ARGB32,
                surface.get_width(), surface.get_height(), surface.get_stride())
        ctx = cairo.Context (surf)
        ctx.rectangle (0, 0, surface.get_width(), surface.get_height())
        ctx.set_source_surface(surface, 0, 0)
        ctx.fill()
        
        dark.reverse()

        rang3 = range(3)
        for s in xrange(0, len(data), 4):
            for i in rang3:
                data[s+i] = (dark[i] + data[s+i]) /3
        
        self.surface = cairo.ImageSurface.create_for_data (
            data, cairo.FORMAT_ARGB32,
            surface.get_width(), surface.get_height(),
            surface.get_stride())
        
        f = open(temppngdir, "w")
        for color in dark:
            f.write(chr(color))
        self.surface.write_to_png(f)
    
    def calcSpacings (self, n):
        """ Will yield ranges like
            ((.50,.50),)
            ((.66,.33), (.33,.66))
            ((.75,.25), (.50,.50), (.25,.75))
            ((.80,.20), (.60,.40), (.40,.60), (.20,.80))
            Used to create the centering in the table """
        
        first = next = (n)/float(n+1)
        for i in range(n):
            yield (next, 1-next)
            next = first-(1-next)
    
    def packTaskers (self, widgets):
        
        self.widgets = widgets
        
        root = math.sqrt(len(widgets))
        # Calculate number of rows
        rows = int(math.ceil(root))
        # Calculate number of filled out rows
        rrows = int(math.floor(root))
        # Calculate number of cols in filled out rows
        cols = int(math.ceil( len(widgets)/float(rows) ))
        
        
        # Calculate spacings
        
        vspac = [s[0] for s in self.calcSpacings(rows)]
        hspac = [s[0] for s in self.calcSpacings(cols)]
        
        
        # Clear and set up new size
        
        for child in self.get_children():
            self.remove(child)
        
        self.props.n_columns = cols
        self.props.n_rows = rows
        
        
        # Add filled out rows
        
        for row in range(rrows):
            for col in range(cols):
                widget = widgets[row*cols + col]
                alignment = gtk.Alignment(hspac[col], vspac[row])
                alignment.add(widget)
                self.attach(alignment, col, col+1, row, row+1)
        
        
        # Add last row
        
        if rows > rrows:
            lastrow = gtk.HBox()
            # Calculate number of widgets in last row
            numw = len(widgets) - cols*rrows
            hspac = [s[0] for s in self.calcSpacings(numw)]
            for col, widget in enumerate(widgets[-numw:]):
                alignment = gtk.Alignment(hspac[col], vspac[-1])
                alignment.add(widget)
                alignment.set_padding(self.border, self.border, self.border, self.border)
                lastrow.pack_start(alignment)    
            
            self.attach(lastrow, 0, cols, rrows, rrows+1)

it = gtk.icon_theme_get_default()
labelSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

def createButton (iconname, text):
    button = gtk.Button(None)
    alignment = gtk.Alignment()
    alignment.props.xalign = .5
    hbox = gtk.HBox()
    hbox.set_spacing(6)
    alignment.add(hbox)
    button.add(alignment)
    button.set_relief(gtk.RELIEF_NONE)
    button.set_size_request(-1, 29)
    
    pix = it.load_icon(iconname, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
    image = gtk.Image()
    image.set_from_pixbuf(pix)
    
    hbox.pack_start(image)
    label = gtk.Label("<b>%s</b>"%text)
    label.set_use_markup(True)
    hbox.pack_start(label)
    return button

class NewGameTasker (gtk.HBox):
    __gsignals__ = {
        'startClicked': (SIGNAL_RUN_FIRST, TYPE_NONE, (int, int, int))
    }
    def __init__ (self):
        gtk.HBox.__init__(self)
        # Sun
        pix = it.load_icon("stock_weather-sunny", 48, gtk.ICON_LOOKUP_USE_BUILTIN)
        image = gtk.Image()
        image.set_from_pixbuf(pix)
        image.set_size_request(75, -1)
        image.props.yalign = 0.2
        image.props.xalign = 0.5
        self.add(image)
        vbox = gtk.VBox()
        vbox.set_spacing(3)
        vbox.set_size_request(250, -1)
        self.add(vbox)
        table = gtk.Table()
        # First row
        label = gtk.Label(_("Your Color")+":")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 0, 1, 0)
        self.colorCombo = combo = ToggleComboBox()
        combo.addItem(_("White"), "stock_draw-rounded-square-unfilled")
        combo.addItem(_("Black"), "stock_draw-rounded-square")
        combo.setMarkup("<b>", "</b>")
        table.attach(combo, 1, 2, 0, 1)
        # Seccond row
        label = gtk.Label(_("Opponent")+":")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 1, 2, 0)
        self.playerCombo = combo = ToggleComboBox()
        for image, name, stock in ionest.playerItems:
            combo.addItem(name, stock)
        combo.label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        combo.setMarkup("<b>", "</b>")
        combo.active = 1
        table.attach(combo, 1, 2, 1, 2)
        # Third row
        label = gtk.Label(_("Difficulty")+":")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 2, 3, 0)
        self.difCombo = combo = ToggleComboBox()
        for image, name, stock in ionest.difItems:
            combo.addItem(name, stock)
        combo.setMarkup("<b>", "</b>")
        def func (playerCombo, active):
            self.difCombo.set_sensitive(active > 0)
        self.playerCombo.connect("changed", func)
        func(self.playerCombo, self.playerCombo.active)
        table.attach(combo, 1, 2, 2, 3)
        table.set_row_spacings(3)
        table.set_col_spacings(3)
        vbox.add(table)
        # Start button
        button = createButton ("gtk-ok", _("Start Game"))
        vbox.add(button)
        button.connect ("clicked", self.startClicked)
    
    def startClicked (self, button):
        self.emit ("startClicked",
                   self.colorCombo.active,
                   self.playerCombo.active,
                   self.difCombo.active)

class InternetGameTasker (gtk.HBox):
    __gsignals__ = {
        'listClicked': (SIGNAL_RUN_FIRST, TYPE_NONE, (int, str, str)),
        'quickClicked': (SIGNAL_RUN_FIRST, TYPE_NONE, (int, str, str))
    }
    def __init__ (self):
        gtk.HBox.__init__(self)
        # Image
        pix = it.load_icon("stock_init", 48, gtk.ICON_LOOKUP_USE_BUILTIN)
        image = gtk.Image()
        image.set_from_pixbuf(pix)
        image.set_size_request(75, -1)
        image.props.yalign = 0.2
        image.props.xalign = 0.5
        self.add(image)
        vbox = gtk.VBox()
        vbox.set_spacing(3)
        vbox.set_size_request(250, -1)
        table = gtk.Table()
        # First row
        label = gtk.Label("Connect to:")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 0, 1, 0)
        combo = ToggleComboBox()
        combo.addItem(_("Free Internet Chess Server"), "gtk-network")
        combo.addItem(_("Another Internet Chess Server"), "gtk-network")
        combo.setMarkup("<b>", "</b>")
        combo.label.set_ellipsize(pango.ELLIPSIZE_END)
        table.attach(combo, 1, 2, 0, 1)
        # Seccond row
        label = gtk.Label(_("Username")+":")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 1, 2, 0)
        table.attach(gtk.Entry(), 1, 2, 1, 2)
        # Third row
        label = gtk.Label(_("Password")+":")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 2, 3, 0)
        entry = gtk.Entry()
        entry.set_visibility(False)
        table.attach(entry, 1, 2, 2, 3)
        table.set_row_spacings(3)
        table.set_col_spacings(3)
        vbox.add(table)
        hb = gtk.HBox()
        # Buttons
        button = createButton("gtk-network", _("Game List"))
        hb.add(button)
        hb.add(createButton("gtk-ok", _("Quick Game")))
        vbox.add(hb)
        self.add(vbox)
