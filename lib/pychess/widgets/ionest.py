""" The task of this module, is to save, load and init new games """

import os
from StringIO import StringIO

import gtk
import gobject

from pychess.System.Log import log
from pychess.System import conf
from pychess.System.protoopen import isWriteable
from pychess.System.GtkWorker import GtkWorker
from pychess.System.uistuff import GladeWidgets
from pychess.System import conf
from pychess.Utils.GameModel import GameModel
from pychess.Utils.const import *
from pychess.Players.engineNest import discoverer
from pychess import Savers
from pychess.Savers import *
from pychess.Savers.ChessFile import LoadingError
from pychess.widgets import gamewidget
from pychess.widgets import gamenanny


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
                gamenanny.nurseGame(gmwidg, game)
                handler.emit("gmwidg_created", gmwidg, game)

            # Then the worker will publish functions setting up widget stuff
            elif callable(val):
                val()
    worker.connect("published", onPublished)

    def onDone (worker, (gmwidg, game)):
        gmwidg.connect("close_clicked", closeGame, game)
        worker.__del__()
    worker.connect("done", onDone)

    worker.execute()

def workfunc (worker, gamemodel, player0tup, player1tup, loaddata=None):
    gmwidg = gamewidget.GameWidget(gamemodel)

    player0 = {}
    player1 = {}
    for player, playertup in ((player0, player0tup), (player1, player1tup)):
        player["name"] = playertup[3]
        player["rating"] = (len(playertup) > 4 and playertup[4]) and "("+playertup[4]+")" or None
        player["tabtext"] = player["rating"] and player["name"] + " " + player["rating"] \
                or player["name"]
    text = [ player0["tabtext"], _("vs"), player1["tabtext"] ]
    gmwidg.setTabText(" ".join(text))

    # Initing analyze engines
    # We have to do this before publishing gmwidg to make sure that
    # gamemodel.*EngineSupportsVariant is set right before on_gmwidg_created() is called
    anaengines = discoverer.getAnalyzers()
    specs = {}
    engine = discoverer.getEngineByMd5(conf.get("ana_combobox", 0))
    if not engine: engine = anaengines[0]
    if gamemodel.variant.board.variant in discoverer.getEngineVariants(engine) or \
       gamemodel.variant.standard_rules:
        if conf.get("analyzer_check", True):
            hintanalyzer = discoverer.initAnalyzerEngine(engine, ANALYZING,
                                                         gamemodel.variant)
            specs[HINT] = hintanalyzer
            log.debug("Hint Analyzer: %s\n" % repr(hintanalyzer))
        gamemodel.hintEngineSupportsVariant = True
    else:
        gamemodel.hintEngineSupportsVariant = False
    engine = discoverer.getEngineByMd5(conf.get("inv_ana_combobox", 0))
    if not engine: engine = anaengines[0]
    if gamemodel.variant.board.variant in discoverer.getEngineVariants(engine) or \
       gamemodel.variant.standard_rules:
        if conf.get("inv_analyzer_check", True):
            spyanalyzer = discoverer.initAnalyzerEngine(engine, INVERSE_ANALYZING,
                                                        gamemodel.variant)
            specs[SPY] = spyanalyzer
            log.debug("Spy Analyzer: %s\n" % repr(spyanalyzer))
        gamemodel.spyEngineSupportsVariant = True            
    else:
        gamemodel.spyEngineSupportsVariant = False

    worker.publish((gmwidg,gamemodel))

    # For updating names
    players = []
    def updateTitle (color=None):

        name0_name1 = gmwidg.getTabText().split(" %s "%_("vs"))
        if not name0_name1:
            name0, name1 = _("White"), _("Black")
        else: name0, name1 = name0_name1

        if color == None:
            name0 = repr(players[WHITE])
            name0 += player0["rating"] and " "+player0["rating"] or ""
            name1 = repr(players[BLACK])
            name1 += player1["rating"] and " "+player1["rating"] or ""
        elif color == WHITE:
            name0 = repr(players[WHITE])
            name0 += player0["rating"] and " "+player0["rating"] or ""
        elif color == BLACK:
            name1 = repr(players[BLACK])
            name1 += player1["rating"] and " "+player1["rating"] or ""

        gmwidg.setTabText("%s %s %s" % (name0, _("vs"), name1))

    # Initing players
    for i, playertup in enumerate((player0tup, player1tup)):
        type, func, args = (playertup[0:3])
        if type != LOCAL:
            players.append(func(*args))
            if type == ARTIFICIAL:
                def readyformoves (player, color):
                    updateTitle(color)
                players[i].connect("readyForMoves", readyformoves, i)
        else:
            # Until PyChess has a proper profiles system, as discussed on the
            # issue tracker, we need to give human players special treatment
            ichandle = None
            if len(args) > 2:
                ichandle = args[2]
                args = [ v for v in args[0:2] ]
            player = func(gmwidg, ichandle=ichandle, *args)
            players.append(player)
            if i == 0 or (i == 1 and player0tup[0] != LOCAL):
                key = "firstName"
                alt = conf.username
            else:
                key = "secondName"
                alt = _("Guest")
            player.setName(conf.get(key, alt))

            def callback (none, color, key, alt):
                players[color].setName(conf.get(key, alt))
                updateTitle(color)
            conf.notify_add(key, callback, i, key, alt)

    worker.publish(updateTitle)

    # Setting game
    gamemodel.setPlayers(players)
    gamemodel.setSpectactors(specs)

    # Starting
    if loaddata:
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

    else:
        if gamemodel.variant.need_initial_board:
            for player in gamemodel.players + gamemodel.spectactors.values():
                player.setOptionInitialBoard(gamemodel)

        gamemodel.start()

    return gmwidg, gamemodel

################################################################################
# Global Load and Save variables                                               #
################################################################################

opendialog = None
savedialog = None
enddir = {}
def getOpenAndSaveDialogs():
    global opendialog, savedialog, enddir, savecombo, savers

    if not opendialog:
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

    return opendialog, savedialog, enddir, savecombo, savers

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
    opendialog, savedialog, enddir, savecombo, savers = getOpenAndSaveDialogs()

    # Keep running the dialog until the user has canceled it or made an error
    # free operation
    while True:
        savedialog.set_current_name("%s %s %s" %
                                   (game.players[0], _("vs."), game.players[1]))
        res = savedialog.run()
        if res != gtk.RESPONSE_ACCEPT:
            break

        uri = savedialog.get_filename()
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
                d.format_secondary_text(_("Was unable to save '%(uri)s' as PyChess doesn't know the format '%(ending)s'.") % {
                                            'uri': uri, 'ending': ending})
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
        else:
            print repr(uri)
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
        widgets = GladeWidgets("saveGamesDialog.glade")
        dialog = widgets["saveGamesDialog"]
        heading = widgets["saveGamesDialogHeading"]
        saveLabel = widgets["saveGamesDialogSaveLabel"]
        treeview = widgets["saveGamesDialogTreeview"]

        heading.set_markup("<big><b>" +
                           ngettext("There is %d game with unsaved moves.",
                              "There are %d games with unsaved moves.",
                              len(changedPairs)) % len(changedPairs) +
                           " " + _("Save moves before closing?") +
                           "</b></big>")

        liststore = gtk.ListStore(bool, str)
        treeview.set_model(liststore)
        renderer = gtk.CellRendererToggle()
        renderer.props.activatable = True
        treeview.append_column(gtk.TreeViewColumn("", renderer, active=0))
        treeview.append_column(gtk.TreeViewColumn("", gtk.CellRendererText(), text=1))
        for gmwidg, game in changedPairs:
            liststore.append((True, "%s %s %s" %
                             (game.players[0], _("vs."), game.players[1])))

        def callback (cell, path):
            if path:
                liststore[path][0] = not liststore[path][0]
            saves = len(tuple(row for row in liststore if row[0]))
            saveLabel.set_text(ngettext("_Save %d document", "_Save %d documents", saves) % saves)
            saveLabel.set_use_underline(True)
        renderer.connect("toggled", callback)

        callback(None, None)

        while True:
            response = dialog.run()
            if response == gtk.RESPONSE_YES:
                for i in xrange(len(liststore)-1, -1, -1):
                    checked, name = liststore[i]
                    if checked:
                        gmwidg, game = changedPairs[i]
                        if saveGame(game) == gtk.RESPONSE_ACCEPT:
                            del pairs[i]
                            liststore.remove(liststore.get_iter((i,)))
                            game.end(ABORTED, ABORTED_AGREEMENT)
                            gamewidget.delGameWidget(gmwidg)
                        else:
                            break
                else:
                    break
            else:
                break
        dialog.destroy()

    if response not in (gtk.RESPONSE_DELETE_EVENT, gtk.RESPONSE_CANCEL):
        for gmwidg, game in pairs:
            game.end(ABORTED, ABORTED_AGREEMENT)
            game.terminate()

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
            "It is not possible later to continue the game,\nif you don't save it."))
        response = d.run()
        d.destroy()

        if response == gtk.RESPONSE_YES:
            # Test if cancel was pressed in the save-file-dialog
            if saveGame(game) != gtk.RESPONSE_ACCEPT:
                response = gtk.RESPONSE_CANCEL

    if response not in (gtk.RESPONSE_DELETE_EVENT, gtk.RESPONSE_CANCEL):
        if game.status in UNFINISHED_STATES:
            game.end(ABORTED, ABORTED_AGREEMENT)
        game.terminate()
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
