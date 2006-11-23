""" The task of this module, is to save, load and init new games """

import gtk, os, random

from pychess.Utils.Game import Game
from pychess.System.Log import log
from pychess.System import myconf
from pychess.Utils.const import prefix, WHITE, BLACK
from pychess.Players import engines
from pychess.Players.Human import Human
from pychess.Savers import *
from pychess import Savers
from pychess.widgets import gamewidget

widgets = gtk.glade.XML(prefix("glade/newInOut.glade"))
class WidgetDic:
    def __init__ (self, widgets):
        self.widgets = widgets
    def __getitem__ (self, key):
        return self.widgets.get_widget(key)
widgets = WidgetDic (widgets)

#
# Initing Load/Save dialogs
#

enddir = {}
types = []

savers = Savers.__all__
for saver in [getattr(Savers, s) for s in savers]:
    for ending in saver.__endings__:
        enddir[ending] = saver
    l = saver.__label__ + " (."+", .".join(saver.__endings__)+")"
    types.append((l, saver.__endings__))

savedialog = gtk.FileChooserDialog(_("Save Game"), None, gtk.FILE_CHOOSER_ACTION_SAVE,
    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))
opendialog = gtk.FileChooserDialog(_("Open Game"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
savedialog.set_current_folder(os.environ["HOME"])
opendialog.set_current_folder(os.environ["HOME"])

# TODO: Working with mime-types might gennerelly be a better idea.

star = gtk.FileFilter()
star.set_name(_("All Files"))
star.add_pattern("*")
opendialog.add_filter(star)

all = gtk.FileFilter()
all.set_name(_("All Chess Files"))
opendialog.add_filter(all)
opendialog.set_filter(all)

custom = gtk.FileFilter()
custom.set_name(_("Detect type automatically"))
custom.add_pattern("*")
savedialog.add_filter(custom)

for label, endings in types:
    f = gtk.FileFilter()
    f.set_name(label)
    for ending in endings:
        f.add_pattern("*."+ending)
        all.add_pattern("*."+ending)
    savedialog.add_filter(f)
    opendialog.add_filter(f)

filechooserbutton = gtk.FileChooserButton(opendialog)
widgets["ngfcalignment"].add(filechooserbutton)
filechooserbutton.show()

#
# Initing newGame dialog
#

isMakeNewGameDialogReady = False
def makeNewGameDialogReady ():
    
    # makeNewGameDialogReady uses lazy initializing,
    # to let engines have as much time as possible to figuere out there names.
    global isMakeNewGameDialogReady
    if isMakeNewGameDialogReady:
        return
    isMakeNewGameDialogReady = True

    def createCombo (combo, data):
        ls = gtk.ListStore(gtk.gdk.Pixbuf, str)
        for icon, label in data:
            ls.append([icon, label])
        combo.clear()
        combo.set_model(ls)
        crp = gtk.CellRendererPixbuf()
        crp.set_property('xalign',0)
        combo.pack_start(crp, False)
        combo.add_attribute(crp, 'pixbuf', 0)
        crt = gtk.CellRendererText()
        crt.set_property('xalign',0)
        combo.pack_start(crt, False)
        combo.add_attribute(crt, 'text', 1)

    it = gtk.icon_theme_get_default()

    icons = ((_("Beginner"), "stock_weather-few-clouds", "weather-few-clouds"), 
             (_("Intermediate"), "stock_weather-cloudy", "weather-overcast"),
             (_("Expert"), "stock_weather-storm", "weather-storm"))
                
    items = []
    for level, stock, altstock in icons:
        try:
            image = it.load_icon(stock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        except gobject.GError:
            image = it.load_icon(altstock, 16, gtk.ICON_LOOKUP_USE_BUILTIN)
        items += [(image, level)]

    for combo in (widgets["whiteDifficulty"], widgets["blackDifficulty"]):
        createCombo(combo, items)

    image = it.load_icon("stock_people", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
    items = [(image, _("Human Being"))]
    image = it.load_icon("stock_notebook", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
    
    for engine in [engines.getInfo((e,a))["name"] for e,a in engines.availableEngines]:
        items += [(image, engine)]
    for combo in (widgets["whitePlayerCombobox"], widgets["blackPlayerCombobox"]):
        createCombo(combo, items)
    
    def on_useTimeCB_clicked (widget):
        widgets["table6"].set_sensitive(widget.get_active())
    
    widgets["useTimeCB"].connect("clicked", on_useTimeCB_clicked)
    
    def on_playerCombobox_changed (widget, colorstring):
        if widget.get_active() > 0:
            widgets["%sDifficulty" % colorstring].set_sensitive(True)
            widgets["%sDifficulty" % colorstring].set_active(1)
        else:
            widgets["%sDifficulty" % colorstring].set_sensitive(False)
            widgets["%sDifficulty" % colorstring].set_active(-1)
    
    widgets["whitePlayerCombobox"].connect("changed", on_playerCombobox_changed, "white")
    widgets["blackPlayerCombobox"].connect("changed", on_playerCombobox_changed, "black")
    
    widgets["whitePlayerCombobox"].set_active(0)
    widgets["blackPlayerCombobox"].set_active(min(1,len(engines.availableEngines)))
    on_playerCombobox_changed (widgets["blackPlayerCombobox"], "black")
    
    for key in ("whitePlayerCombobox", "blackPlayerCombobox", "whiteDifficulty",
            "blackDifficulty", "spinbuttonH", "spinbuttonM", "spinbuttonS",
            "spinbuttonG", "useTimeCB"):
        v = myconf.get(key)
        if v != None:
            if hasattr(widgets[key], "set_active"):
                widgets[key].set_active(v)
            else: widgets[key].set_value(v)

#
# runNewGameDialog
#

def runNewGameDialog (hideFC=True):
    makeNewGameDialogReady ()
    
    #If the dialog should show or hide the filechooser button
    if hideFC:
        widgets["loadsidepanel"].hide()
    else: widgets["loadsidepanel"].show()

    res = widgets["newgamedialog"].run()
    widgets["newgamedialog"].hide()
    if res != gtk.RESPONSE_OK: return None,None
    
    #for widget in ("save_game1", "save_game_as1", "properties1", "close1"):
    #    if not widgets[widget]: print repr(widget)
    #    widgets[widget].set_property('sensitive', True)
        
    gmwidg = gamewidget.createGameWidget("")
    gmwidg.widgets["sidepanel"].connect("hide", \
        lambda w: widgets["side_panel1"].set_active(False))
    ccalign = gmwidg.widgets["ccalign"]
    
    if widgets["useTimeCB"].get_active():
        ccalign.show()
        clock = widgets["ChessClock"]
        secs = widgets["spinbuttonH"].get_value()*3600
        secs += widgets["spinbuttonM"].get_value()*60
        secs += widgets["spinbuttonS"].get_value()
        gain = widgets["spinbuttonG"].get_value()
    else:
        ccalign.hide()
        clock = None
        secs = 0
        gain = 0
        
    for widget in ("whitePlayerCombobox", "blackPlayerCombobox", "whiteDifficulty", "blackDifficulty", "spinbuttonH", "spinbuttonM", "spinbuttonS", "spinbuttonG", "useTimeCB"):
        if hasattr(widgets[widget], "get_active"):
            v = widgets[widget].get_active()
        else: v = widgets[widget].get_value()
        myconf.set(widget, v)
    
    players = []
    for box, dfcbox, color in (("whitePlayerCombobox","whiteDifficulty",WHITE),
                              ("blackPlayerCombobox","blackDifficulty",BLACK)):
        choise = widgets[box].get_active()
        dfc = widgets[dfcbox].get_active()
        if choise != 0:
            engine = engines.availableEngines[choise-1][0]
            player = engine(engines.availableEngines[choise-1][1],color)
            player.setStrength(dfc)
            if secs:
                player.setTime(secs, gain)
        else: player = Human(gmwidg.widgets["board"], color)
        players += [player]
    
    gmwidg.setTabText("%s vs %s" % (repr(players[0]), repr(players[1])))
    
    anaengines = [(e,a) for e,a in engines.availableEngines \
                                        if engines.getInfo((e,a))["canAnalyze"]]
    if len(anaengines) > 1:
        # We assume that the Pychess engine is the last of the list
        engine, args = random.choice(anaengines[:-1])
    else: engine, args = anaengines[0]
    analyzer = engine(args, WHITE)
    analyzer.analyze()
    log.debug("Analyzer: %s\n" % repr(analyzer))

    history = gmwidg.widgets["board"].view.history
    game = Game(gmwidg, history, analyzer, players[0], players[1], clock, secs, gain)
    
    gmwidg.connect("closed", closeGame, game)
    
    #game.connect("game_ended", GladeHandlers.__dict__["game_ended"])
    
    #TODO: enable this for tabs
    #widgets["properties1"].set_sensitive(True)
    return game, gmwidg

#
# For the user
#

def newGame ():
    game, gmwidg = runNewGameDialog()
    if game:
        game.run()
        return game, gmwidg
    return None, None

def loadGame (path = None):
    
    if not path:
        res = opendialog.run()
        opendialog.hide()
        if res != gtk.RESPONSE_ACCEPT: return
        uri = opendialog.get_uri()
    
    filechooserbutton.set_uri(uri)
    game, gmwidg = runNewGameDialog(hideFC=False)
    
    if game:
        uri = filechooserbutton.get_uri()
        loader = enddir[uri[uri.rfind(".")+1:]]
        game.load(uri, loader)
        game.run()
        return game, gmwidg
        
    return None, None

def saveGame (game):
    if not game.isChanged:
        return
    if game.lastSave[1]:
        saveGameSimple (game.lastSave[1], game)
    else:
        # When we do "Save as", user has a button to "Cancel"
        # If he do so, game should not be closed
        return saveGameAs (game)

def saveGameSimple (path, game):
    ending = os.path.splitext(path)[1]
    if not ending: return
    saver = enddir[ending]
    game.save(uri, saver)

def saveGameAs (game):
    
    def response (savedialog, r):
        pass #TODO
    savedialog.connect("response", response)
    savedialog.show_all()
    
    #FIXME: If file exists or has wrong filetype, the window is hidden..
    #       And the user has to reopen it to type a new name
    res = savedialog.run()
    if res != gtk.RESPONSE_ACCEPT: return False
    uri = savedialog.get_uri()[7:]
    ending = os.path.splitext(uri)[1]
    
    if savedialog.get_filter().filter((None,None,"foo",None)):
        if not ending in enddir:
            d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
            folder, file = os.path.split(uri)
            d.set_markup(_("<big><b>Unknown filetype '%s'</b></big>") % ending)
            d.format_secondary_text(_("Wasn't able to save '%s' as pychess doesn't know the format '%s'.") % (uri,ending))
            d.run()
            d.hide()
            return
        saver = enddir[ending]
    else:
        for e,sr in enddir.iteritems():
            if savedialog.get_filter().filter((None,None,"."+e,None)):
                if not ending in sr.__endings__:
                    uri += "." + e
                break
                
    if os.path.isfile(uri):
        d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
        d.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, _("_Replace"), gtk.RESPONSE_ACCEPT)
        d.set_title(_("File exists"))
        folder, file = os.path.split(uri)
        d.set_markup(_("<big><b>A file named '%s' alredy exists. Would you like to replace it?</b></big>") % file)
        d.format_secondary_text(_("The file alredy exists in '%s'. If you replace it, its content will be overwritten.") % folder)
        res = d.run()
        d.hide()
        if res != gtk.RESPONSE_ACCEPT:
            savedialog.hide()
            return
    savedialog.hide()
    saver = enddir[ending]
    game.save(uri, saver)

def saveGameBeforeClose (game, action):
    
    if not game.isChanged(): return

    d = gtk.MessageDialog (type = gtk.MESSAGE_WARNING)
    d.add_button(gtk.STOCK_REVERT_TO_SAVED, gtk.RESPONSE_NO)
    d.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    d.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_YES)

    d.set_markup(_("<b><big>Save the current game before %s?</big></b>") % action)
    d.format_secondary_text (_(
        "It is not possible later to continue the game,\nif do don't save it."))
    response = d.run()
    d.hide()
    
    if response == gtk.RESPONSE_YES:
        if saveGame(game) == False:
            return gtk.RESPONSE_CANCEL
    return response

def closeAllGames (games):
    names = ["%s vs %s" % (g.player1, g.player2) for g in games if g.isChanged]
    if len(names) == 0:
        return gtk.RESPONSE_OK
    d = gtk.MessageDialog (type = gtk.MESSAGE_WARNING)
    d.add_button(gtk.STOCK_REVERT_TO_SAVED, gtk.RESPONSE_OK)
    d.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    d.set_markup(
        _("<big><b>There are %d games with unsaved changes:</b></big>") % len(names))
    d.format_secondary_text("\n".join(names))
    response = d.run()
    d.hide()
    return response

def closeGame (gmwidg, game):
    if saveGameBeforeClose (game, _("you close it")) != gtk.RESPONSE_CANCEL:
        game.kill()
        gamewidget.delGameWidget (gmwidg)
