""" The task of this module, is to save, load and init new games """

import os
from StringIO import StringIO

import gtk, gobject

from pychess.System.Log import log
from pychess.System import conf
from pychess.System.protoopen import isWriteable
from pychess.System.GtkWorker import GtkWorker
from pychess.Utils import const
from pychess.Utils.const import *
from pychess.Players.engineNest import discoverer
from pychess import Savers
from pychess.Savers import *
from pychess.Savers.ChessFile import LoadingError
from pychess.widgets import gamewidget

def generalStart (gamemodel, player0tup, player1tup, loaddata=None):
    """ The player tuples are:
        (The type af player in a System.const value,
         A callable creating the player,
         A list of arguments for the callable,
         A preliminary name for the player)
        
        If loaddata is specified, it should be a tuple of:
        (A text uri or fileobj,
         A Savers.something module with a load function capable of loading it,
         An int of the game in file you want to load,
         The position from where to start the game) """
    
    worker = GtkWorker (lambda w:
            workfunc(w, gamemodel, player0tup, player1tup, loaddata))
    
    def onPublished (worker, vallist):
        for val in vallist:
            # The worker will start by publishing (gmwidg, game)
            if type(val) == tuple:
                gmwidg, game = val
                gamewidget.attachGameWidget(gmwidg)
                handler.emit("gmwidg_created", gmwidg, game)
            
            # Then the worker will publish functions setting up widget stuff
            elif callable(val):
                val()
    worker.connect("published", onPublished)
    
    def onDone (worker, (gmwidg, game)):
        gmwidg.connect("close_clicked", closeGame, game)
    worker.connect("done", onDone)
    
    worker.execute()

def workfunc (worker, gamemodel, player0tup, player1tup, loaddata=None):
    gmwidg = gamewidget.GameWidget(gamemodel)
    
    text = [name for t, f, a, name in (player0tup, player1tup)]
    text.insert(1,_("vs"))
    gmwidg.setTabText(" ".join(text))
    
    worker.publish((gmwidg,gamemodel))
    
    # For updating names
    players = []
    def updateTitle (*args):
        gmwidg.setTabText("%s %s %s" %
                (repr(players[0]), _("vs"), repr(players[1])) )
    
    # Initing players
    for i, playertup in enumerate((player0tup, player1tup)):
        type, func, args, name = playertup
        if type != LOCAL:
            players.append(func(*args))
        else:
            # Until PyChess has a proper profiles system, as discussed on the
            # issue tracker, we need to give human players special treatment
            player = func(gmwidg, *args)
            players.append(player)
            if i == 0 or (i == 1 and player0tup[0] != LOCAL):
                key = "firstName"
                alt = const.username
            else:
                key = "secondName"
                alt = _("Guest")
            player.setName(conf.get(key, alt))
            def callback (*args):
                player.setName(conf.get(key, alt))
                updateTitle()
            conf.notify_add(key, callback)
    
    worker.publish(updateTitle)
    
    # Initing analyze engines
    anaengines = discoverer.getAnalyzers()
    specs = {}
    
    if conf.get("analyzer_check", True):
        engine = discoverer.getEngineByMd5(conf.get("ana_combobox", 0))
        if not engine: engine = anaengines[0]
        hintanalyzer = discoverer.initEngine(engine, WHITE)
        specs[HINT] = hintanalyzer
        log.debug("Hint Analyzer: %s\n" % repr(hintanalyzer))
    
    if conf.get("inv_analyzer_check", True):
        engine = discoverer.getEngineByMd5(conf.get("inv_ana_combobox", 0))
        if not engine: engine = anaengines[0]
        spyanalyzer = discoverer.initEngine(engine, WHITE)
        specs[SPY] = spyanalyzer
        log.debug("Spy Analyzer: %s\n" % repr(spyanalyzer))
    
    # Setting game
    gamemodel.setPlayers(players)
    gamemodel.setSpectactors(specs)
    
    # Starting
    if not loaddata:
        gamemodel.start()
    else:
        try:
            uri, loader, gameno, position = loaddata
            gamemodel.loadAndStart (uri, loader, gameno, position)
        except LoadingError, e:
            d = gtk.MessageDialog (type=gtk.MESSAGE_WARNING, buttons=gtk.BUTTONS_OK)
            d.set_markup ("<big><b>%s</b></big>" % e.args[0])
            d.format_secondary_text (e.args[1] + "\n\n" +
                    _("Correct the move, or start playing with what could be read"))
            d.connect("response", lambda d,a: d.hide())
            worker.publish(d.show)
    
    if HINT in specs:
        specs[HINT].autoAnalyze(inverse=False)
    if SPY in specs:
        specs[SPY].autoAnalyze(inverse=True)
    
    return gmwidg, gamemodel

################################################################################
# Global Load and Save variables                                               #
################################################################################

enddir = {}
types = []
savers = [getattr(Savers, s) for s in Savers.__all__]
for saver in savers:
    for ending in saver.__endings__:
        enddir[ending] = saver
    types.append((saver.__label__, saver.__endings__))

opendialog = gtk.FileChooserDialog(_("Open Game"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
savedialog = gtk.FileChooserDialog(_("Save Game"), None, gtk.FILE_CHOOSER_ACTION_SAVE,
    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))

savedialog.set_current_folder(os.environ["HOME"])
saveformats = gtk.ListStore(str, str)

# All files filter
star = gtk.FileFilter()
star.set_name(_("All Files"))
star.add_pattern("*")
opendialog.add_filter(star)
saveformats.append([_("Detect type automatically"), ""])

# All chess files filter
all = gtk.FileFilter()
all.set_name(_("All Chess Files"))
opendialog.add_filter(all)
opendialog.set_filter(all)

# Specific filters and save formats
default = 0
for i, (label, endings) in enumerate(types):
    endstr = "(%s)" % ", ".join(endings)
    f = gtk.FileFilter()
    f.set_name(label+" "+endstr)
    for ending in endings:
        f.add_pattern("*."+ending)
        all.add_pattern("*."+ending)
    opendialog.add_filter(f)
    saveformats.append([label, endstr])
    if "pgn" in endstr:
        default = i + 1

# Add widgets to the savedialog
savecombo = gtk.ComboBox()
savecombo.set_model(saveformats)
crt = gtk.CellRendererText()
savecombo.pack_start(crt, True)
savecombo.add_attribute(crt, 'text', 0)
crt = gtk.CellRendererText()
savecombo.pack_start(crt, False)
savecombo.add_attribute(crt, 'text', 1)
savecombo.set_active(default)
savedialog.set_extra_widget(savecombo)

################################################################################
# Saving                                                                       #
################################################################################

def saveGame (game):
    if not game.isChanged():
        return
    if game.uri and isWriteable (game.uri):
        saveGameSimple (game.uri, game)
    else:
        return saveGameAs (game)

def saveGameSimple (uri, game):
    ending = os.path.splitext(uri)[1]
    if not ending: return
    saver = enddir[ending[1:]]
    game.save(uri, saver, append=False)

def saveGameAs (game):
    while True:
        res = savedialog.run()
        if res != gtk.RESPONSE_ACCEPT:
            break
        
        uri = savedialog.get_uri()[7:]
        ending = os.path.splitext(uri)[1]
        if ending.startswith("."): ending = ending[1:]
        
        append = False
        
        if savecombo.get_active() == 0:
            if not ending in enddir:
                d = gtk.MessageDialog(
                        type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
                folder, file = os.path.split(uri)
                d.set_markup(
                          _("<big><b>Unknown file type '%s'</b></big>") % ending)
                d.format_secondary_text(_("Was unable to save '%s' as PyChess doesn't know the format '%s'.") % (uri,ending))
                d.run()
                d.hide()
                continue
            else:
                saver = enddir[ending]
        else:
            saver = savers[savecombo.get_active()-1]
            if not ending in enddir or not saver == enddir[ending]:
                uri += ".%s" % saver.__endings__[0]
        
        if os.path.isfile(uri) and not os.access (uri, os.W_OK):
            d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
            d.set_markup(_("<big><b>Unable to save file '%s'</b></big>") % uri)
            d.format_secondary_text(
                _("You don't have the necessary rights to save the file.\n\
Please ensure that you have given the right path and try again."))
            d.run()
            d.hide()
            continue
        
        if os.path.isfile(uri):
            d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
            d.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, _("_Replace"),
                        gtk.RESPONSE_ACCEPT)
            if saver.__append__:
                d.add_buttons(gtk.STOCK_ADD, 1)
            d.set_title(_("File exists"))
            folder, file = os.path.split(uri)
            d.set_markup(_("<big><b>A file named '%s' already exists. Would you like to replace it?</b></big>") % file)
            d.format_secondary_text(_("The file already exists in '%s'. If you replace it, its content will be overwritten.") % folder)
            replaceRes = d.run()
            d.hide()
            
            if replaceRes == 1:
                append = True
            elif replaceRes == gtk.RESPONSE_CANCEL:
                continue
        
        try:
            game.save(uri, saver, append)
        except IOError, e:
            d = gtk.MessageDialog(type=gtk.MESSAGE_ERROR)
            d.add_buttons(gtk.STOCK_OK, gtk.RESPONSE_OK)
            d.set_title(_("Could not save the file"))
            d.set_markup(_("<big><b>PyChess was not able to save the game</b></big>"))
            d.format_secondary_text(_("The error was: %s") % ", ".join(str(a) for a in e.args))
            os.remove(uri)
            d.run()
            d.hide()
            continue
        
        break
    
    savedialog.hide()
    return res

################################################################################
# Closing                                                                      #
################################################################################

def closeAllGames (pairs):
    changedPairs = [(gmwidg, game) for gmwidg, game in pairs if game.isChanged()]
    if len(changedPairs) == 0:
        response = gtk.RESPONSE_OK
    elif len(changedPairs) == 1:
        response = closeGame(*changedPairs[0])
    else:
        names = ["%s vs %s" % tuple(g.players) for w, g in changedPairs]
        d = gtk.MessageDialog (type = gtk.MESSAGE_WARNING)
        d.add_button(_("Close _without Saving"), gtk.RESPONSE_OK)
        d.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        d.set_markup(_("<big><b>There are %d games with unsaved changes:</b></big>")
                % len(changedPairs))
        d.format_secondary_text("\n".join(names))
        response = d.run()
        d.hide()
    
    if response != gtk.RESPONSE_CANCEL:
        for gmwidg, game in pairs:
            game.end(ABORTED, ABORTED_AGREEMENT)
    
    return response

def closeGame (gmwidg, game):
    if not game.isChanged():
        response = gtk.RESPONSE_OK
    else:
        d = gtk.MessageDialog (type = gtk.MESSAGE_WARNING)
        d.add_button(_("Close _without Saving"), gtk.RESPONSE_OK)
        d.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        if game.uri:
            d.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_YES)
        else: d.add_button(gtk.STOCK_SAVE_AS, gtk.RESPONSE_YES)
        
        gmwidg.bringToFront()
        
        d.set_markup(_("<b><big>Save the current game before you close it?</big></b>"))
        d.format_secondary_text (_(
            "It is not possible later to continue the game,\nif do don't save it."))
        response = d.run()
        d.hide()
        
        if response == gtk.RESPONSE_YES:
            # Test if cancel was pressed in the save-file-dialog
            if saveGame(game) != gtk.RESPONSE_ACCEPT:
                response = gtk.RESPONSE_CANCEL
    
    if response != gtk.RESPONSE_CANCEL:
        game.end(ABORTED, ABORTED_AGREEMENT)
        gamewidget.delGameWidget (gmwidg)
    
    return response

################################################################################
# Signal handler                                                               #
################################################################################

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class Handler (GObject):
    """ The goal of this class, is to provide signal handling for the ionest
        module.
        Emit objects are gmwidg, gameobject """
        
    __gsignals__ = {
        'gmwidg_created': (SIGNAL_RUN_FIRST, TYPE_NONE, (object, object))
    }
    
    def __init__ (self):
        GObject.__init__(self)

handler = Handler()
