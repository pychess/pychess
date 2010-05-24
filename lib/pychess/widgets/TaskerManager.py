import math

import gtk, cairo, pango
from gobject import SIGNAL_RUN_FIRST, TYPE_NONE

from pychess.System.prefix import addDataPrefix
from pychess.System import uistuff
from pychess.System.glock import glock_connect_after 
from ToggleComboBox import ToggleComboBox
from Background import giveBackground
import newGameDialog

from pychess.widgets import newGameDialog
from pychess.ic import ICLogon

from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.Utils.const import LOCAL, ARTIFICIAL, WHITE, NORMALCHESS
from pychess.ic import ICLogon
from pychess.widgets import ionest
from pychess.widgets import newGameDialog
from pychess.Variants import variants

class TaskerManager (gtk.Table):
    
    def __init__ (self):
        gtk.Table.__init__(self)
        self.border = 20
        giveBackground(self)
        self.connect("expose_event", self.expose)
        #self.set_homogeneous(True)
    
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
            
            cr.rectangle (x-self.border, y+height-30, width+self.border*2, 30)
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
    
    def packTaskers (self, *widgets):
        
        self.widgets = widgets
        
        for widget in widgets:
            widget.connect("size-allocate", lambda *a:
                           self.window.invalidate_rect(self.get_allocation(), False))
        
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

class NewGameTasker (gtk.Alignment):
    
    def __init__ (self):
        gtk.Alignment.__init__(self,0,0,0,0)
        self.widgets = widgets = uistuff.GladeWidgets("taskers.glade")
        tasker = widgets["newGameTasker"]
        tasker.unparent()
        self.add(tasker)
        
        self.colorCombo = combo = ToggleComboBox()
        combo.addItem(_("White"), "stock_draw-rounded-square-unfilled")
        combo.addItem(_("Black"), "stock_draw-rounded-square")
        combo.setMarkup("<b>", "</b>")
        widgets["colorDock"].add(combo)
        uistuff.keep(self.colorCombo, "newgametasker_colorcombo")
        
        # We need to wait until after engines have been discovered, to init the
        # playerCombos. We use connect_after to make sure, that newGameDialog
        # has also had time to init the constants we share with them.
        self.playerCombo = ToggleComboBox()
        widgets["opponentDock"].add(self.playerCombo)
        glock_connect_after(discoverer, "all_engines_discovered",
                            self.__initPlayerCombo, widgets)
        
        def on_skill_changed (scale):
            pix = newGameDialog.skillToIconLarge[int(scale.get_value())]
            widgets["skillImage"].set_from_pixbuf(pix)
        widgets["skillSlider"].connect("value-changed", on_skill_changed)
        on_skill_changed(widgets["skillSlider"])
        
        widgets["startButton"].connect("clicked", self.startClicked)
        self.widgets["opendialog1"].connect("clicked", self.openDialogClicked)
    
    def __initPlayerCombo (self, discoverer, widgets):
        combo = self.playerCombo
        for image, name in newGameDialog.smallPlayerItems[0]:
            combo.addItem(name, image)
        combo.label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        combo.setMarkup("<b>", "</b>")
        combo.active = 1
        uistuff.keep(self.playerCombo, "newgametasker_playercombo")
        
        def on_playerCombobox_changed (widget, event):
            widgets["skillSlider"].props.visible = widget.active > 0
        combo.connect("changed", on_playerCombobox_changed)
        uistuff.keep(widgets["skillSlider"], "taskerSkillSlider")
        widgets["skillSlider"].set_no_show_all(True)
        on_playerCombobox_changed(self.playerCombo, None)
    
    def openDialogClicked (self, button):
        newGameDialog.NewGameMode.run()
    
    def startClicked (self, button):
        color = self.widgets["colorDock"].child.active
        opponent = self.widgets["opponentDock"].child.active
        difficulty = int(self.widgets["skillSlider"].get_value())
        
        gamemodel = GameModel(TimeModel(5*60, 0))
        
        player0tup = (LOCAL, Human, (color, ""), _("Human"))
        if opponent == 0:
            player1tup = (LOCAL, Human, (1-color, ""), _("Human"))
        else:
            engine = discoverer.getEngineN (opponent-1)
            name = discoverer.getName(engine)
            player1tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                    (engine, 1-color, difficulty, variants[NORMALCHESS], 5*60, 0), name)
        
        if color == WHITE:
            ionest.generalStart(gamemodel, player0tup, player1tup)
        else: ionest.generalStart(gamemodel, player1tup, player0tup)

class InternetGameTasker (gtk.Alignment):
    
    def __init__ (self):
        gtk.Alignment.__init__(self,0,0,0,0)
        self.widgets = uistuff.GladeWidgets("taskers.glade")
        tasker = self.widgets["internetGameTasker"]
        tasker.unparent()
        self.add(tasker)
        
        def asGuestCallback (checkbutton):
            for widget in (self.widgets["usernameLabel"], self.widgets["usernameEntry"],
                           self.widgets["passwordLabel"], self.widgets["passwordEntry"]):
                widget.set_sensitive(not checkbutton.get_active())
        self.widgets["asGuestCheck"].connect("toggled", asGuestCallback)
        
        uistuff.keep(self.widgets["asGuestCheck"], "asGuestCheck")
        uistuff.keep(self.widgets["usernameEntry"], "usernameEntry")
        uistuff.keep(self.widgets["passwordEntry"], "passwordEntry")
        
        self.widgets["connectButton"].connect("clicked", self.connectClicked)
        self.widgets["opendialog2"].connect("clicked", self.openDialogClicked)
    
    def openDialogClicked (self, button):
        ICLogon.run()
    
    def connectClicked (self, button):
        asGuest = self.widgets["asGuestCheck"].get_active()
        username = self.widgets["usernameEntry"].get_text()
        password = self.widgets["passwordEntry"].get_text()
        
        ICLogon.run()
        if not ICLogon.dialog.connection:
            ICLogon.dialog.widgets["logOnAsGuest"].set_active(asGuest)
            ICLogon.dialog.widgets["nameEntry"].set_text(username)
            ICLogon.dialog.widgets["passEntry"].set_text(password)
            ICLogon.dialog.widgets["connectButton"].clicked()
