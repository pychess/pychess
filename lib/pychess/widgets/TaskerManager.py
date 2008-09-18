import math

import gtk, cairo, pango
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.prefix import addDataPrefix
from pychess.System import uistuff
from ToggleComboBox import ToggleComboBox
from Background import giveBackground
import newGameDialog

class TaskerManager (gtk.Table):
    
    def __init__ (self):
        gtk.Table.__init__(self)
        self.border = 20
        giveBackground(self)
        self.connect("expose_event", self.expose)
        self.set_homogeneous(True)
    
    def expose (self, widget, event):
        cr = widget.window.cairo_create()
        
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
        table.attach(label, 0, 1, 0, 1, xoptions=0)
        self.colorCombo = combo = ToggleComboBox()
        combo.addItem(_("White"), "stock_draw-rounded-square-unfilled")
        combo.addItem(_("Black"), "stock_draw-rounded-square")
        combo.setMarkup("<b>", "</b>")
        uistuff.keep(self.colorCombo, "newgametasker_colorcombo")
        table.attach(combo, 1, 2, 0, 1)
        # Seccond row
        label = gtk.Label(_("Opponent")+":")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 1, 2, xoptions=0)
        self.playerCombo = combo = ToggleComboBox()
        for image, name, stock in newGameDialog.playerItems[0]:
            combo.addItem(name, stock)
        combo.label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        combo.setMarkup("<b>", "</b>")
        combo.active = 1
        uistuff.keep(self.playerCombo, "newgametasker_playercombo")
        table.attach(combo, 1, 2, 1, 2)
        # Third row
        label = gtk.Label(_("Difficulty")+":")
        label.props.xalign = 0
        labelSizeGroup.add_widget(label)
        table.attach(label, 0, 1, 2, 3, xoptions=0)
        self.difCombo = combo = ToggleComboBox()
        for image, name, stock in newGameDialog.difItems:
            combo.addItem(name, stock)
        combo.setMarkup("<b>", "</b>")
        def func (playerCombo, oldactive):
            self.difCombo.props.sensitive = playerCombo.active > 0
        self.playerCombo.connect("changed", func)
        func(self.playerCombo, self.playerCombo.active)
        uistuff.keep(self.difCombo, "newgametasker_difcombo")
        table.attach(combo, 1, 2, 2, 3)
        table.set_row_spacings(3)
        table.set_col_spacings(3)
        vbox.add(table)
        # Start button
        button = createButton ("gtk-ok", _("Start Game"))
        button.set_flags(gtk.CAN_DEFAULT)
        vbox.add(button)
        button.connect ("clicked", self.startClicked)
    
    def startClicked (self, button):
        self.emit ("startClicked",
                   self.colorCombo.active,
                   self.playerCombo.active,
                   self.difCombo.active)

class InternetGameTasker (gtk.HBox):
    __gsignals__ = {
        'connectClicked': (SIGNAL_RUN_FIRST, TYPE_NONE, (bool, str, str))
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
        # Table
        table = gtk.Table()
        table.set_row_spacings(3)
        table.set_col_spacings(3)
        vbox.add(table)
        self.add(vbox)
        # First row
        self.asGuestCheck = gtk.CheckButton(_("Log on as _Guest"))
        def asGuestCallback (checkbutton):
            for widget in (self.usernameLabel, self.usernameEntry,
                           self.passwordLabel, self.passwordEntry):
                widget.set_sensitive(not checkbutton.get_active())
        self.asGuestCheck.connect("toggled", asGuestCallback)
        table.attach(self.asGuestCheck, 0, 2, 0, 1)
        # Seccond row
        self.usernameLabel = gtk.Label(_("Name")+":")
        self.usernameLabel.props.xalign = 0
        labelSizeGroup.add_widget(self.usernameLabel)
        table.attach(self.usernameLabel, 0, 1, 1, 2, xoptions=0)
        self.usernameEntry = gtk.Entry()
        self.usernameEntry.props.activates_default = True
        self.usernameEntry.set_width_chars(0)
        table.attach(self.usernameEntry, 1, 2, 1, 2)
        # Third row
        self.passwordLabel = gtk.Label(_("Password")+":")
        self.passwordLabel.props.xalign = 0
        labelSizeGroup.add_widget(self.passwordLabel)
        table.attach(self.passwordLabel, 0, 1, 2, 3, xoptions=0)
        self.passwordEntry = gtk.Entry()
        self.passwordEntry.set_visibility(False)
        self.passwordEntry.props.activates_default = True
        self.passwordEntry.set_width_chars(0)
        table.attach(self.passwordEntry, 1, 2, 2, 3)
        # Button
        self.connectButton = createButton("gtk-ok", _("Connect to FICS"))
        vbox.add(self.connectButton)
        self.connectButton.set_flags(gtk.CAN_DEFAULT)
        self.connectButton.connect ("clicked", self.connectClicked)
        # On activate
        def onActivateCallback (entry):
            self.connectButton.clicked()
        self.usernameEntry.connect("activate", onActivateCallback)
        self.passwordEntry.connect("activate", onActivateCallback)
        # Keep
        uistuff.keep(self.asGuestCheck, "logOnAsGuest")
        asGuestCallback(self.asGuestCheck)
    
    def connectClicked (self, button):
        self.emit ("connectClicked",
                   self.asGuestCheck.get_active(),
                   self.usernameEntry.get_text(),
                   self.passwordEntry.get_text())
