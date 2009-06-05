
import gettext
import locale
from time import sleep
from cStringIO import StringIO
from operator import attrgetter
from itertools import groupby

import gtk
import gobject
from cairo import ImageSurface

try:
    from gtksourceview import SourceBuffer
    from gtksourceview import SourceView
    from gtksourceview import SourceLanguagesManager
except ImportError:
    from gtksourceview2 import Buffer as SourceBuffer
    from gtksourceview2 import View as SourceView
    from gtksourceview2 import LanguageManager as SourceLanguagesManager

from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import *
from pychess.System import uistuff, protoopen
from pychess.System.Log import log
from pychess.System import conf
from pychess.System.prefix import getDataPrefix, isInstalled, addDataPrefix
from pychess.Players.engineNest import discoverer
from pychess.Players.Human import Human
from pychess.widgets import BoardPreview
from pychess.widgets import ionest
from pychess.widgets import ImageMenu
from pychess.Savers import pgn
from pychess.Variants import variants
from pychess.Variants.normal import NormalChess

#===============================================================================
# We init most dialog icons global to make them accessibly to the
# Background.Taskers so they have a similar look.
#===============================================================================

it = gtk.icon_theme_get_default()

iwheels = it.load_icon("gtk-execute", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
ipeople = it.load_icon("stock_people", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
inotebook = it.load_icon("stock_notebook", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
speople = it.load_icon("stock_people", 16, gtk.ICON_LOOKUP_USE_BUILTIN)
snotebook = it.load_icon("stock_notebook", 16, gtk.ICON_LOOKUP_USE_BUILTIN)

skillToIcon = {
    1: it.load_icon("weather-clear", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
    2: it.load_icon("weather-few-clouds", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
    3: it.load_icon("weather-few-clouds", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
    4: it.load_icon("weather-overcast", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
    5: it.load_icon("weather-overcast", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
    6: it.load_icon("weather-showers", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
    7: it.load_icon("weather-showers", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
    8: it.load_icon("weather-storm", 16, gtk.ICON_LOOKUP_USE_BUILTIN),
}

# Used by TaskerManager. Put here to help synchronization
skillToIconLarge = {
    1: it.load_icon("weather-clear", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
    2: it.load_icon("weather-few-clouds", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
    3: it.load_icon("weather-few-clouds", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
    4: it.load_icon("weather-overcast", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
    5: it.load_icon("weather-overcast", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
    6: it.load_icon("weather-showers", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
    7: it.load_icon("weather-showers", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
    8: it.load_icon("weather-storm", 48, gtk.ICON_LOOKUP_USE_BUILTIN),
}

playerItems = []
smallPlayerItems = []

def createPlayerUIGlobals (discoverer):
    global playerItems
    global smallPlayerItems
    for variantClass in variants.values():
        playerItems += [ [(ipeople, _("Human Being"))] ]
        smallPlayerItems += [ [(speople, _("Human Being"))] ]
    for engine in discoverer.getEngines().values():
        name = discoverer.getName(engine)
        c = discoverer.getCountry(engine)
        if c: flag_icon = gtk.gdk.pixbuf_new_from_file(addDataPrefix("flags/%s.png" % c))
        else: flag_icon = inotebook
        for variant in discoverer.getEngineVariants(engine):
            playerItems[variant] += [(flag_icon, name)]
            smallPlayerItems[variant] += [(snotebook, name)]

discoverer.connect("all_engines_discovered", createPlayerUIGlobals)

#===============================================================================
# GameInitializationMode is the super class of new game dialogs. Dialogs include
# the standard new game dialog, the load file dialog and the enter notation
# dialog.
#===============================================================================

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

        uistuff.createCombo(cls.widgets["whitePlayerCombobox"],
                            (i[:2] for i in playerItems[0]))
        uistuff.createCombo(cls.widgets["blackPlayerCombobox"],
                            (i[:2] for i in playerItems[0]))


        def on_playerCombobox_changed (widget, skillHbox):
            skillHbox.props.visible = widget.get_active() > 0
        cls.widgets["whitePlayerCombobox"].connect(
                "changed", on_playerCombobox_changed, cls.widgets["skillHbox1"])
        cls.widgets["blackPlayerCombobox"].connect(
                "changed", on_playerCombobox_changed, cls.widgets["skillHbox2"])
        cls.widgets["whitePlayerCombobox"].set_active(0)
        cls.widgets["blackPlayerCombobox"].set_active(1)


        def on_skill_changed (scale, image):
            image.set_from_pixbuf(skillToIcon[int(scale.get_value())])
        cls.widgets["skillSlider1"].connect("value-changed", on_skill_changed,
                                            cls.widgets["skillIcon1"])
        cls.widgets["skillSlider2"].connect("value-changed", on_skill_changed,
                                            cls.widgets["skillIcon2"])
        cls.widgets["skillSlider1"].set_value(3)
        cls.widgets["skillSlider2"].set_value(3)


        cls.__initTimeRadio(_("Blitz"), "ngblitz", cls.widgets["blitzRadio"],
                            cls.widgets["configImageBlitz"], 5, 0)
        cls.__initTimeRadio(_("Rapid"), "ngrapid", cls.widgets["rapidRadio"],
                            cls.widgets["configImageRapid"], 15, 5)
        cls.__initTimeRadio(_("Normal"), "ngnormal", cls.widgets["normalRadio"],
                            cls.widgets["configImageNormal"], 40, 15)

        cls.__initVariantRadio("ngvariant1", cls.widgets["playVariant1Radio"],
                               cls.widgets["configImageVariant1"],
                               FISCHERRANDOMCHESS)
        cls.__initVariantRadio("ngvariant2", cls.widgets["playVariant2Radio"],
                               cls.widgets["configImageVariant2"], LOSERSCHESS)

        def updateCombos(*args):
            if cls.widgets["playNormalRadio"].get_active():
                variant = NORMALCHESS
            elif cls.widgets["playVariant1Radio"].get_active():
                variant = conf.get("ngvariant1", FISCHERRANDOMCHESS)
            else:
                variant = conf.get("ngvariant2", LOSERSCHESS)
            uistuff.updateCombo(cls.widgets["blackPlayerCombobox"], playerItems[variant])
            uistuff.updateCombo(cls.widgets["whitePlayerCombobox"], playerItems[variant])
        conf.notify_add("ngvariant1", updateCombos)
        conf.notify_add("ngvariant2", updateCombos)
        cls.widgets["playNormalRadio"].connect("toggled", updateCombos)
        cls.widgets["playVariant1Radio"].connect("toggled", updateCombos)
        cls.widgets["playVariant2Radio"].connect("toggled", updateCombos)

        # The "variant" has to come before players, because the engine positions
        # in the user comboboxes can be different in different variants
        for key in ("whitePlayerCombobox", "blackPlayerCombobox",
                    "skillSlider1", "skillSlider2",
                    "notimeRadio", "blitzRadio", "rapidRadio", "normalRadio",
                    "playNormalRadio", "playVariant1Radio", "playVariant2Radio"):
            uistuff.keep(cls.widgets[key], key)

        # We don't want the dialog to deallocate when closed. Rather we hide
        # it on respond
        cls.widgets["newgamedialog"].connect("delete_event", lambda *a: True)

    @classmethod
    def __initTimeRadio (cls, name, id, radiobutton, configImage, defmin, defgain):
        minSpin = gtk.SpinButton(gtk.Adjustment(1,1,240,1))
        gainSpin = gtk.SpinButton(gtk.Adjustment(0,-60,60,1))
        cls.widgets["%s min" % id] = minSpin
        cls.widgets["%s gain" % id] = gainSpin
        uistuff.keep(minSpin, "%s min" % id, first_value=defmin)
        uistuff.keep(gainSpin, "%s gain" % id, first_value=defgain)

        table = gtk.Table(2, 2)
        table.props.row_spacing = 3
        table.props.column_spacing = 12
        label = gtk.Label(_("Minutes")+":")
        label.props.xalign = 0
        table.attach(label, 0, 1, 0, 1)
        table.attach(minSpin, 1, 2, 0, 1)
        label = gtk.Label(_("Gain")+":")
        label.props.xalign = 0
        table.attach(label, 0, 1, 1, 2)
        table.attach(gainSpin, 1, 2, 1, 2)
        alignment = gtk.Alignment(1,1,1,1)
        alignment.set_padding(6,6,12,12)
        alignment.add(table)
        ImageMenu.switchWithImage(configImage, alignment)

        def updateString (spin):
            minutes = minSpin.get_value_as_int()
            gain = gainSpin.get_value_as_int()
            if gain > 0:
                radiobutton.set_label(_("%(name)s %(minutes)d min + %(gain)d sec/move") % {
                                        'name': name, 'minutes': minutes, 'gain': gain})
            elif gain < 0:
                radiobutton.set_label(_("%(name)s %(minutes)d min %(gain)d sec/move") % {
                                        'name': name, 'minutes': minutes, 'gain': gain})
            else:
                radiobutton.set_label(_("%(name)s %(minutes)d min") % {
                                        'name': name, 'minutes': minutes})
        minSpin.connect("value-changed", updateString)
        gainSpin.connect("value-changed", updateString)
        updateString(None)

    @classmethod
    def __initVariantRadio (cls, confid, radiobutton, configImage, default):
        model = gtk.TreeStore(str)
        treeview = gtk.TreeView(model)
        treeview.set_headers_visible(False)
        treeview.append_column(gtk.TreeViewColumn(None, gtk.CellRendererText(), text=0))
        alignment = gtk.Alignment(1,1,1,1)
        alignment.set_padding(6,6,12,12)
        alignment.add(treeview)
        ImageMenu.switchWithImage(configImage, alignment)

        groupNames = {VARIANTS_BLINDFOLD: _("Blindfold"),
                      VARIANTS_ODDS: _("Odds"),
                      VARIANTS_SHUFFLE: _("Shuffle"),
                      VARIANTS_OTHER: _("Other")}
        specialVariants = [v for v in variants.values() if v != NormalChess]
        groups = groupby(specialVariants, attrgetter("variant_group"))
        pathToVariant = {}
        variantToPath = {}
        for i, (id, group) in enumerate(groups):
            iter = model.append(None, (groupNames[id],))
            for variant in group:
                subiter = model.append(iter, (variant.name,))
                path = model.get_path(subiter)
                pathToVariant[path] = variant.board.variant
                variantToPath[variant.board.variant] = path
            treeview.expand_row((i,), True)

        selection = treeview.get_selection()
        selection.set_mode(gtk.SELECTION_BROWSE)
        selection.set_select_function(lambda path: len(path) > 1)
        selection.select_path(variantToPath[conf.get(confid, default)])

        def callback (selection):
            model, iter = selection.get_selected()
            if iter:
                radiobutton.set_label("%s" % model.get(iter, 0))
                path = model.get_path(iter)
                variant = pathToVariant[path]
                conf.set(confid, variant)
        selection.connect("changed", callback)
        callback(selection)

    @classmethod
    def _generalRun (cls, callback):
        def onResponse(dialog, res):
            cls.widgets["newgamedialog"].hide()
            cls.widgets["newgamedialog"].disconnect(handlerId)
            if res != gtk.RESPONSE_OK:
                return

            # Find variant
            if cls.widgets["playNormalRadio"].get_active():
                variant_index = NORMALCHESS
            elif cls.widgets["playVariant1Radio"].get_active():
                variant_index = conf.get("ngvariant1", FISCHERRANDOMCHESS)
            else:
                variant_index = conf.get("ngvariant2", LOSERSCHESS)
            variant = variants[variant_index]

            # Find time
            if cls.widgets["notimeRadio"].get_active():
                secs = 0
                incr = 0
            elif cls.widgets["blitzRadio"].get_active():
                secs = cls.widgets["ngblitz min"].get_value_as_int()*60
                incr = cls.widgets["ngblitz gain"].get_value_as_int()
            elif cls.widgets["rapidRadio"].get_active():
                secs = cls.widgets["ngrapid min"].get_value_as_int()*60
                incr = cls.widgets["ngrapid gain"].get_value_as_int()
            elif cls.widgets["normalRadio"].get_active():
                secs = cls.widgets["ngnormal min"].get_value_as_int()*60
                incr = cls.widgets["ngnormal gain"].get_value_as_int()

            # Find players
            player0 = cls.widgets["whitePlayerCombobox"].get_active()
            player0 = playerItems[0].index(playerItems[variant_index][player0])
            diffi0 = int(cls.widgets["skillSlider1"].get_value())
            player1 = cls.widgets["blackPlayerCombobox"].get_active()
            player1 = playerItems[0].index(playerItems[variant_index][player1])
            diffi1 = int(cls.widgets["skillSlider2"].get_value())

            # Prepare players for ionest
            playertups = []
            for i, playerno, diffi, color in ((0, player0, diffi0, WHITE),
                                              (1, player1, diffi1, BLACK)):
                if playerno > 0:
                    engine = discoverer.getEngineN (playerno-1)
                    name = discoverer.getName(engine)
                    playertups.append((ARTIFICIAL, discoverer.initPlayerEngine,
                            (engine, color, diffi, variant, secs, incr), name))
                else:
                    playertups.append((LOCAL, Human, (color, ""), _("Human")))

            if secs > 0:
                timemodel = TimeModel (secs, incr)
            else: timemodel = None

            gamemodel = GameModel (timemodel, variant)

            callback(gamemodel, playertups[0], playertups[1])

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
    def run (cls):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return

        cls._hideOthers()
        cls.widgets["newgamedialog"].set_title(_("New Game"))
        cls._generalRun(ionest.generalStart)

################################################################################
# LoadFileExtension                                                            #
################################################################################

class LoadFileExtension (_GameInitializationMode):
    @classmethod
    def _init (cls):
        opendialog, savedialog, enddir, savecombo, savers = ionest.getOpenAndSaveDialogs()
        cls.filechooserbutton = gtk.FileChooserButton(opendialog)
        cls.loadSidePanel = BoardPreview.BoardPreview(cls.widgets,
                cls.filechooserbutton, opendialog, enddir)

    @classmethod
    def run (cls, uri=None, chessFiles=None):
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

        def _callback (gamemodel, p0, p1):
            if not cls.loadSidePanel.is_empty():
                uri =  cls.loadSidePanel.get_filename()
                loader = ionest.enddir[uri[uri.rfind(".")+1:]]
                position = cls.loadSidePanel.get_position()
                gameno = cls.loadSidePanel.get_gameno()
                if chessFiles:
                    chessFiles[uri] = cls.loadSidePanel.chessfile
                ionest.generalStart(gamemodel, p0, p1, (uri, loader, gameno, position))
            else:
                ionest.generalStart(gamemodel, p0, p1)
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
    def run (cls):
        cls._ensureReady()
        if cls.widgets["newgamedialog"].props.visible:
            cls.widgets["newgamedialog"].present()
            return

        cls._hideOthers()
        cls.widgets["newgamedialog"].set_title(_("Enter Game"))
        cls.widgets["enterGameNotationSidePanel"].show()

        def _callback (gamemodel, p0, p1):
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

            ionest.generalStart(gamemodel, p0, p1, (StringIO(text), pgn, 0, -1))
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
        if event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
            self.current = (self.current + 1) % len(self.surfaces)
            self.window.invalidate_rect(self.size, True)
            self.window.process_updates(True)

def createRematch (gamemodel):
    if gamemodel.timemodel:
        secs = gamemodel.timemodel.intervals[0][WHITE]
        gain = gamemodel.timemodel.gain
        newgamemodel = GameModel(TimeModel(secs, gain), gamemodel.variant)
    else:
        secs = 0
        gain = 0
        newgamemodel = GameModel(variant=gamemodel.variant)

    wp = gamemodel.players[WHITE]
    bp = gamemodel.players[BLACK]

    if wp.__type__ == LOCAL:
        player1tup = (wp.__type__, wp.__class__, (BLACK, ""), repr(wp))
        if bp.__type__ == LOCAL:
            player0tup = (bp.__type__, bp.__class__, (WHITE, ""), repr(bp))
        else:
            binname = bp.engine.path.split("/")[-1]
            if binname == "python":
                binname = bp.engine.args[1].split("/")[-1]
            xmlengine = discoverer.getEngines()[binname]
            player0tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                          (xmlengine, WHITE, bp.strength, gamemodel.variant,
                           secs, gain), repr(bp))
    else:
        player0tup = (bp.__type__, bp.__class__, (WHITE, ""), repr(bp))
        binname = wp.engine.path.split("/")[-1]
        if binname == "python":
            binname = wp.engine.args[1].split("/")[-1]
        xmlengine = discoverer.getEngines()[binname]
        player1tup = (ARTIFICIAL, discoverer.initPlayerEngine,
                      (xmlengine, BLACK, wp.strength, gamemodel.variant,
                       secs, gain), repr(wp))

    ionest.generalStart(newgamemodel, player0tup, player1tup)
