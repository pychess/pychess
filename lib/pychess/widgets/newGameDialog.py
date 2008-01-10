
import gettext, locale
from cStringIO import StringIO

import gtk
from cairo import ImageSurface
from gtksourceview import *

from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import *
from pychess.System import uistuff, protoopen
from pychess.System.prefix import getDataPrefix, isInstalled, addDataPrefix
from pychess.Players.engineNest import discoverer
from pychess.Players.Human import Human
from pychess.widgets import BoardPreview
from pychess.widgets import ionest
from pychess.Savers import pgn

# We init players here, to have a better balance between application and dialog
# startup time.
# This way we also make it accessible to the Background.Taskers and let them
# have a very simmilar look

it = gtk.icon_theme_get_default()

image = it.load_icon("stock_people", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
playerItems = [(image, _("Human Being"), "stock_people")]
image = it.load_icon("stock_notebook", 24, gtk.ICON_LOOKUP_USE_BUILTIN)

for engine in discoverer.getEngines().values():
    playerItems += [(image, discoverer.getName(engine), "stock_notebook")]

difItems = []
for level, stock, altstock in \
        ((_("Beginner"), "stock_weather-few-clouds", "weather-few-clouds"), 
            (_("Intermediate"), "stock_weather-cloudy", "weather-overcast"),
            (_("Expert"), "stock_weather-storm", "weather-storm")):
    try:
        image = it.load_icon(stock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        difItems += [(image, level, stock)]
    except gobject.GError:
        image = it.load_icon(altstock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        difItems += [(image, level, altstock)]

################################################################################
# GameInitializationMode                                                       #
################################################################################

class _GameInitializationMode:
    @classmethod
    def _ensureReady (cls):
        if not hasattr(_GameInitializationMode, "superhasRunInit"):
            _GameInitializationMode._init()
            _GameInitializationMode.superhasRunInit = True
        if not hasattr(cls, "hasRunInit"):
            cls._init()
            cls.hasRunInit = True
    
    @classmethod
    def _init (cls):
        cls.widgets = uistuff.GladeWidgets ("newInOut.glade")
        
        for combo in (cls.widgets["whiteDifficulty"], cls.widgets["blackDifficulty"]):
            uistuff.createCombo(combo, [i[:2] for i in difItems])
        
        for combo in (cls.widgets["whitePlayerCombobox"], cls.widgets["blackPlayerCombobox"]):
            uistuff.createCombo(combo, [i[:2] for i in playerItems])
        
        def on_useTimeCB_clicked (widget):
            cls.widgets["table6"].set_sensitive(widget.get_active())
        cls.widgets["useTimeCB"].connect("clicked", on_useTimeCB_clicked)
        
        def on_playerCombobox_changed (widget, colorstring):
            if widget.get_active() > 0:
                cls.widgets["%sDifficulty" % colorstring].set_sensitive(True)
                cls.widgets["%sDifficulty" % colorstring].set_active(1)
            else:
                cls.widgets["%sDifficulty" % colorstring].set_sensitive(False)
                cls.widgets["%sDifficulty" % colorstring].set_active(-1)
        
        cls.widgets["whitePlayerCombobox"].connect(
                "changed", on_playerCombobox_changed, "white")
        cls.widgets["blackPlayerCombobox"].connect(
                "changed", on_playerCombobox_changed, "black")
        
        cls.widgets["whitePlayerCombobox"].set_active(0)
        cls.widgets["blackPlayerCombobox"].set_active(1)
        on_playerCombobox_changed (cls.widgets["blackPlayerCombobox"], "black")
        
        for key in ("whitePlayerCombobox", "blackPlayerCombobox", "whiteDifficulty",
                "blackDifficulty", "spinbuttonH", "spinbuttonM", "spinbuttonS",
                "spinbuttonG", "useTimeCB"):
            uistuff.keep(cls.widgets[key], key)
    
    @classmethod
    def _generalRun (cls, callback):
        def onResponse(dialog, res):
            cls.widgets["newgamedialog"].hide()
            cls.widgets["newgamedialog"].disconnect(handlerId)
            if res != gtk.RESPONSE_OK:
                return None
            
            # Find time
            if cls.widgets["useTimeCB"].get_active():
                secs = cls.widgets["spinbuttonH"].get_value()*3600
                secs += cls.widgets["spinbuttonM"].get_value()*60
                secs += cls.widgets["spinbuttonS"].get_value()
                incr = cls.widgets["spinbuttonG"].get_value()
            else:
                secs = 0
                incr = 0
            
            # Find players
            player0 = cls.widgets["whitePlayerCombobox"].get_active()
            diffi0 = cls.widgets["whiteDifficulty"].get_active()
            player1 = cls.widgets["blackPlayerCombobox"].get_active()
            diffi1 = cls.widgets["blackDifficulty"].get_active()
            
            # Prepare players for ionest
            playertups = []
            for i, playerno, diffi, color in ((0, player0, diffi0, WHITE),
                                              (1, player1, diffi1, BLACK)):
                if playerno > 0:
                    engine = discoverer.getEngineN (playerno-1)
                    name = discoverer.getName(engine)
                    playertups.append((ARTIFICIAL, discoverer.initAndStartEngine,
                            (engine, color, diffi, secs, incr), name))
                else:
                    playertups.append((LOCAL, Human, (color, ""), _("Human")))
            
            if secs > 0:
                timemodel = TimeModel (secs, incr)
            else: timemodel = None
            gamemodel = GameModel (timemodel)
            
            callback((gamemodel, playertups[0], playertups[1]))
        
        handlerId = cls.widgets["newgamedialog"].connect("response", onResponse)
        cls.widgets["newgamedialog"].show()
    
    @classmethod
    def _hideOthers (cls):
        for extension in ("loadsidepanel", "enterGameNotationSidePanel",
                "enterGameNotationSidePanel"):
            cls.widgets[extension].hide()

################################################################################
# NewGameMode                                                                  #
################################################################################

class NewGameMode (_GameInitializationMode):
    @classmethod
    def _init (cls):
        # We have to override this, so the GameInitializationMode init method
        # isn't called twice
        pass
    
    @classmethod
    def run (cls, callback):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return
        
        cls._hideOthers()
        cls.widgets["newgamedialog"].set_title(_("New Game"))
        cls._generalRun(callback)

################################################################################
# LoadFileExtension                                                            #
################################################################################

class LoadFileExtension (_GameInitializationMode):
    @classmethod
    def _init (cls):
        cls.filechooserbutton = gtk.FileChooserButton(ionest.opendialog)
        cls.loadSidePanel = BoardPreview.BoardPreview(cls.widgets,
                cls.filechooserbutton, ionest.opendialog, ionest.enddir)
    
    @classmethod
    def run (cls, callback, uri=None):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return
        
        if not uri:
            res = ionest.opendialog.run()
            ionest.opendialog.hide()
            if res != gtk.RESPONSE_ACCEPT:
                return
        else:
            if not uri[uri.rfind(".")+1:] in ionest.enddir:
                log.log("Ignoring strange file: %s" % uri)
                return
            cls.loadSidePanel.set_filename(uri)
            cls.filechooserbutton.emit("file-activated")
            
        cls._hideOthers()
        cls.widgets["newgamedialog"].set_title(_("Open Game"))
        cls.widgets["loadsidepanel"].show()
        
        def _callback (startdata):
            if not cls.loadSidePanel.is_empty():
                uri =  cls.loadSidePanel.get_filename()
                loader = ionest.enddir[uri[uri.rfind(".")+1:]]
                position = cls.loadSidePanel.get_position()
                gameno = cls.loadSidePanel.get_gameno()
                callback(startdata + ((uri, loader, gameno, position),))
            else:
                callback(startdata)
        cls._generalRun(_callback)

################################################################################
# EnterNotationExtension                                                       #
################################################################################

class EnterNotationExtension (_GameInitializationMode):
    @classmethod
    def _init (cls):
        def callback (widget, allocation):
            cls.widgets["enterGameNotationFrame"].set_size_request(
                    223, allocation.height-4)
        cls.widgets["enterGameNotationSidePanel"].connect_after("size-allocate", callback)
        
        flags = []
        if isInstalled():
            path = gettext.find("pychess")
        else:
            path = gettext.find("pychess", localedir=addDataPrefix("lang"))
        if path:
            loc = locale.getdefaultlocale()[0][-2:].lower()
            flags.append(addDataPrefix("flags/%s.png" % loc))
        
        flags.append(addDataPrefix("flags/us.png"))
        
        cls.ib = ImageButton(flags)
        cls.widgets["imageButtonDock"].add(cls.ib)
        cls.ib.show()
        
        cls.sourcebuffer = SourceBuffer()
        sourceview = SourceView(cls.sourcebuffer)
        cls.widgets["scrolledwindow6"].add(sourceview)
        sourceview.show()
        
        # Pgn format does not allow tabulator
        sourceview.set_insert_spaces_instead_of_tabs(True)
        sourceview.set_wrap_mode(gtk.WRAP_WORD)
        
        man = SourceLanguagesManager()
        lang = [l for l in man.get_available_languages() if l.get_name() == "PGN"][0]
        cls.sourcebuffer.set_language(lang)
        
        cls.sourcebuffer.set_highlight(True)
    
    @classmethod
    def run (cls, callback):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return
        
        cls._hideOthers()
        cls.widgets["newgamedialog"].set_title(_("Enter Game"))
        cls.widgets["enterGameNotationSidePanel"].show()
        
        def _callback (startdata):
            text = cls.sourcebuffer.get_text(
                cls.sourcebuffer.get_start_iter(), cls.sourcebuffer.get_end_iter())
            
            # Test if the ImageButton has two layers and is set on the local language
            if len(cls.ib.surfaces) == 2 and cls.ib.current == 0:
                # 2 step used to avoid backtranslating
                # (local and english piece letters can overlap)
                for i, sign in enumerate(localReprSign[1:]):
                    if sign.strip():
                        text = text.replace(sign, FAN_PIECES[0][i+1])
                for i, sign in enumerate(FAN_PIECES[0][1:7]):
                    text = text.replace(sign, reprSign[i+1])
                text = str(text)
            
            callback(startdata + ((StringIO(text), pgn, 0, -1),))
        cls._generalRun(_callback)

class ImageButton(gtk.DrawingArea):
    def __init__ (self, imagePaths):
        gtk.DrawingArea.__init__(self)
        self.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.BUTTON_PRESS_MASK)
        
        self.connect("expose-event", self.draw)
        self.connect("button_press_event", self.buttonPress)
        
        self.surfaces = [ImageSurface.create_from_png(path) for path in imagePaths]
        self.current = 0
        
        width, height = self.surfaces[0].get_width(), self.surfaces[0].get_height()
        self.size = gtk.gdk.Rectangle(0, 0, width, height)
        self.set_size_request(width, height)
    
    def draw (self, self_, event):
        context = self.window.cairo_create()
        context.rectangle (event.area.x, event.area.y,
                            event.area.width, event.area.height)
        context.set_source_surface(self.surfaces[self.current], 0, 0)
        context.fill()
    
    def buttonPress (self, self_, event):
        self.current = (self.current + 1) % len(self.surfaces)
        self.window.invalidate_rect(self.size, True)
        self.window.process_updates(True)
