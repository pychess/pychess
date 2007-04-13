""" The task of this module, is to save, load and init new games """

import gtk, os, random, pango

from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.System.Log import log
from pychess.System import myconf
from pychess.System.protoopen import protosave, isWriteable
from pychess.Utils.const import *
from pychess.Utils.Piece import Piece
from pychess.Utils.Cord import Cord
from pychess.Players import engineNest
from pychess.Players.Human import Human
from pychess.Savers import *
from pychess import Savers
from pychess.widgets import gamewidget
from pychess.widgets import BoardPreview
from pychess.widgets.SetupBoard import SetupBoard

discoverer = engineNest.EngineDiscoverer()
discoverer.start()

widgets = gtk.glade.XML(prefix("glade/newInOut.glade"))
class WidgetDic:
    def __init__ (self, widgets):
        self.widgets = widgets
    def __getitem__ (self, key):
        return self.widgets.get_widget(key)
widgets = WidgetDic (widgets)

################################################################################
# Initing Load/Save dialogs                                                    #
################################################################################

enddir = {}
types = []

savers = [getattr(Savers, s) for s in Savers.__all__]
for saver in savers:
    for ending in saver.__endings__:
        enddir[ending] = saver
    types.append((saver.__label__, saver.__endings__))

savedialog = gtk.FileChooserDialog(_("Save Game"), None, gtk.FILE_CHOOSER_ACTION_SAVE,
    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT))
opendialog = gtk.FileChooserDialog(_("Open Game"), None, gtk.FILE_CHOOSER_ACTION_OPEN,
    (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
savedialog.set_current_folder(os.environ["HOME"])
saveformats = gtk.ListStore(str, str)

# TODO: Working with mime-types might gennerelly be a better idea.

star = gtk.FileFilter()
star.set_name(_("All Files"))
star.add_pattern("*")
opendialog.add_filter(star)
saveformats.append([_("Detect type automatically"), ""])

all = gtk.FileFilter()
all.set_name(_("All Chess Files"))
opendialog.add_filter(all)
opendialog.set_filter(all)

for label, endings in types:
    endstr = "(%s)" % ", ".join(endings)
    f = gtk.FileFilter()
    f.set_name(label+" "+endstr)
    for ending in endings:
        f.add_pattern("*."+ending)
        all.add_pattern("*."+ending)
    opendialog.add_filter(f)
    saveformats.append([label, endstr])

savecombo = gtk.ComboBox()
savecombo.set_model(saveformats)
crt = gtk.CellRendererText()
savecombo.pack_start(crt, True)
savecombo.add_attribute(crt, 'text', 0)
crt = gtk.CellRendererText()
savecombo.pack_start(crt, False)
savecombo.add_attribute(crt, 'text', 1)
savecombo.set_active(0)
savedialog.set_extra_widget(savecombo)

################################################################################
# Initing sidepanels                                                           #
################################################################################

panels = ["loadsidepanel", "enterGameNotationSidePanel", "setUpPositionSidePanel"]

def setActiveSidePanel (panelname):
    """ Set to None to hide all panels """
    for panel in panels:
        if panel != panelname:
            widgets[panel].hide()
    if panelname:
        widgets[panelname].show()

################################################################################
# Initing Load sidepanel                                                       #
################################################################################

filechooserbutton = gtk.FileChooserButton(opendialog)
loadSidePanel = BoardPreview.BoardPreview()
loadSidePanel.addFileChooserButton(filechooserbutton, opendialog, enddir)
filechooserbutton.show()
widgets["loadsidepanel"].add(loadSidePanel)

################################################################################
# Initing enter notation sidepanel                                             #
################################################################################

from gtksourceview import *
buffer = SourceBuffer()
sourceview = SourceView(buffer)
widgets["scrolledwindow6"].add(sourceview)
sourceview.show()

# Pgn format does not allow tabulator
sourceview.set_insert_spaces_instead_of_tabs(True)
sourceview.set_wrap_mode(gtk.WRAP_WORD)

man = SourceLanguagesManager()
lang = [l for l in man.get_available_languages() if l.get_name() == "PGN"][0]
buffer.set_language(lang)

buffer.set_highlight(True)

################################################################################
# Initing set up position sidepanel                                            #
################################################################################

    ############################################################################
    # Buttons                                                                  #
    ############################################################################

def invertOther (button, other):
    other.set_active(not button.get_active())
widgets["togglebutton2"].connect("toggled", invertOther, widgets["togglebutton5"])
widgets["togglebutton5"].connect("toggled", invertOther, widgets["togglebutton2"])

    ############################################################################
    # Board                                                                    #
    ############################################################################

setupBoard = SetupBoard()
widgets["boardSpace"].add(setupBoard)
setupBoard.show_all()

def cord_clicked (setupBoard, cord):
    store0, treeiter0 = widgets["treeview0"].get_selection().get_selected()
    store1, treeiter1 = widgets["treeview1"].get_selection().get_selected()
    if treeiter0 != None or treeiter1 != None:
        brush = PIECE
        if treeiter0 != None:
            color = WHITE
            sign = store0.get_path(treeiter0)[0]
        else:
            color = BLACK
            sign = store1.get_path(treeiter1)[0]
    else:
        store2, treeiter2 = widgets["treeview2"].get_selection().get_selected()
        if treeiter2 != None:
            brush = CLEAR
        else: brush = ENPAS
    
    if brush == ENPAS:
        if setupBoard.view.history[-1].enpassant:
            setupBoard.view.showEnpassant = False
        setupBoard.view.history[-1].enpassant = cord
        setupBoard.view.showEnpassant = True
        
    else:
        board = setupBoard.view.history[-1].clone()
        if brush == CLEAR:
            board[cord] = None
            if board.enpassant == cord:
                board.enpassant = None
            cords = setupBoard.getLegalCords()
            cords.remove(cord)
            setupBoard.setLegalCords(cords)
        else:
            board[cord] = Piece(color, sign)
        
        enpascords = []
        for y in (3,4):
            for x in range(8):
                piece = board.data[y][x]
                if piece and piece.sign == PAWN:
                    if y == 3 and piece.color == WHITE and \
                            not board.data[2][x] and not board.data[1][x]:
                        enpascords.append(Cord(x,2))
                    elif y == 4 and piece.color == BLACK and \
                            not board.data[5][x] and not board.data[6][x]:
                        enpascords.append(Cord(x,5))
        if not setupBoard.view.history[-1].enpassant in enpascords:
            print "hiding"
            setupBoard.view.showEnpassant = False
            board.enpassant = None
        
        setupBoard.view.history.moves.append(None)
        setupBoard.view.history.boards.append(board)
        setupBoard.view.history.emit("changed")

setupBoard.connect("cord_clicked", cord_clicked)

    ############################################################################
    # Lists                                                                    #
    ############################################################################
    
def selected (selection, viewno):
    liststore, treeiter = selection.get_selected()
    if treeiter == None:
        return # We don't unselect others, if we have been unselected
    
    for i in range(4):
        if i == viewno: continue
        widgets["treeview%d"%i].get_selection().unselect_all()
    
    treepath = liststore.get_path(treeiter)
    row = treepath[0]
    
    if liststore in [widgets["treeview%d"%i].get_model() for i in range(2)]:
        setupBoard.setLegalCords()
    elif liststore == widgets["treeview2"].get_model():
        legalCords = []
        for y in range(8):
            for x in range(8):
                if setupBoard.view.history[-1].data[y][x]:
                    legalCords.append(Cord(x,y))
        if setupBoard.view.history[-1].enpassant:
            legalCords += [setupBoard.view.history[-1].enpassant]
        setupBoard.setLegalCords(legalCords)
    else:
        legalCords = []
        for y in (3,4):
            for x in range(8):
                piece = setupBoard.view.history[-1].data[y][x]
                if piece and piece.sign == PAWN:
                    if y == 3 and piece.color == WHITE:
                        legalCords.append(Cord(x,2))
                    elif y == 4 and piece.color == BLACK:
                        legalCords.append(Cord(x,5))
        setupBoard.setLegalCords(legalCords)
    
for i in range(4):
    widgets["treeview%d"%i].set_model(gtk.ListStore(str))
    widgets["treeview%d"%i].append_column(gtk.TreeViewColumn(
            None, gtk.CellRendererText(), text=0))
    widgets["treeview%d"%i].get_selection().set_mode(gtk.SELECTION_BROWSE)
    widgets["treeview%d"%i].get_selection().connect_after('changed', selected, i)
    
widgets["treeview0"].set_model(gtk.ListStore(str))
widgets["treeview1"].set_model(gtk.ListStore(str))

for piece in reprPiece:
    widgets["treeview0"].get_model().append([piece])
    widgets["treeview1"].get_model().append([piece])
            
widgets["treeview2"].get_model().append(["Clear"])
widgets["treeview3"].get_model().append(["En pas"])

################################################################################
# Initing newGame dialog                                                       #
################################################################################

# Init items for difficulty list

it = gtk.icon_theme_get_default()

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

# Init items for player list

image = it.load_icon("stock_people", 24, gtk.ICON_LOOKUP_USE_BUILTIN)
playerItems = [(image, _("Human Being"), "stock_people")]
image = it.load_icon("stock_notebook", 24, gtk.ICON_LOOKUP_USE_BUILTIN)

for engine in discoverer.getEngines().values():
    playerItems += [(image, discoverer.getName(engine), "stock_notebook")]

# Init widgets

isNewGameDialogReady = False
def ensureNewGameDialogReady ():
    
    global isNewGameDialogReady
    if isNewGameDialogReady:
        return
    isNewGameDialogReady = True
    
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
        combo.pack_start(crt, True)
        combo.add_attribute(crt, 'text', 1)
        crt.set_property('ellipsize', pango.ELLIPSIZE_MIDDLE)
    
    for combo in (widgets["whiteDifficulty"], widgets["blackDifficulty"]):
        createCombo(combo, [i[:2] for i in difItems])
    
    for combo in (widgets["whitePlayerCombobox"], widgets["blackPlayerCombobox"]):
        createCombo(combo, [i[:2] for i in playerItems])
    
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
    
    widgets["whitePlayerCombobox"].connect(
            "changed", on_playerCombobox_changed, "white")
    widgets["blackPlayerCombobox"].connect(
            "changed", on_playerCombobox_changed, "black")
    
    widgets["whitePlayerCombobox"].set_active(0)
    widgets["blackPlayerCombobox"].set_active(1)
    on_playerCombobox_changed (widgets["blackPlayerCombobox"], "black")
    
    for key in ("whitePlayerCombobox", "blackPlayerCombobox", "whiteDifficulty",
            "blackDifficulty", "spinbuttonH", "spinbuttonM", "spinbuttonS",
            "spinbuttonG", "useTimeCB"):
        v = myconf.get(key)
        if v != None:
            if hasattr(widgets[key], "set_active"):
                widgets[key].set_active(v)
            else: widgets[key].set_value(v)

################################################################################
# runNewGameDialog                                                             #
################################################################################

def runNewGameDialog ():
    ensureNewGameDialogReady ()
    res = widgets["newgamedialog"].run()
    widgets["newgamedialog"].hide()
    if res != gtk.RESPONSE_OK: return None,None
    
    # Finding time
    
    if widgets["useTimeCB"].get_active():
        secs = widgets["spinbuttonH"].get_value()*3600
        secs += widgets["spinbuttonM"].get_value()*60
        secs += widgets["spinbuttonS"].get_value()
        incr = widgets["spinbuttonG"].get_value()
    else:
        secs = 0
        incr = 0
    
    # Saving widget states
    
    for widget in ("whitePlayerCombobox", "blackPlayerCombobox",
                   "whiteDifficulty", "blackDifficulty", "spinbuttonH",
                   "spinbuttonM", "spinbuttonS", "spinbuttonG", "useTimeCB"):
        if hasattr(widgets[widget], "get_active"):
            v = widgets[widget].get_active()
        else: v = widgets[widget].get_value()
        myconf.set(widget, v)
    
    # Finding players
    
    player0 = widgets["whitePlayerCombobox"].get_active()
    diffi0 = widgets["whiteDifficulty"].get_active()
    player1 = widgets["blackPlayerCombobox"].get_active()
    diffi1 = widgets["blackDifficulty"].get_active()
    
    return createGame (player0, player1, diffi0, diffi1, secs, incr)

def createGame (player0, player1, diffi0, diffi1, secs=300, incr=0):
    
    # Init time model
    
    if secs:
        timemodel = TimeModel (secs, incr)
    else: timemodel = None
    
    # Init game model and widget
    
    game = GameModel (timemodel)
    gmwidg = gamewidget.createGameWidget(game)
    
    # Finding players
    
    players = []
    for playerno, diffi, color in ((player0, diffi0, WHITE),\
                                 (player1, diffi1, BLACK)):
        if playerno > 0:
            engine = discoverer.getEngineN (playerno-1)
            player = discoverer.initEngine (engine, color)
            player.setStrength(diffi)
            if secs:
                player.setTime(secs, incr)
        else: player = Human(gmwidg.widgets["board"], color)
        players += [player]
    
    gmwidg.setTabText("%s vs %s" % (repr(players[0]), repr(players[1])))
    
    # Initing analyze engines

    anaengines = discoverer.getAnalyzers()
    specs = {}
    
    if myconf.get("analyzer_check"):
        engine = discoverer.getEngineByMd5(myconf.get("ana_combobox"))
        if not engine: engine = anaengines[0]
        hintanalyzer = discoverer.initEngine(engine, WHITE)
        hintanalyzer.analyze(inverse=False)
        specs[HINT] = hintanalyzer
        log.debug("Hint Analyzer: %s\n" % repr(hintanalyzer))
    
    if myconf.get("inv_analyzer_check"):
        engine = discoverer.getEngineByMd5(myconf.get("inv_ana_combobox"))
        if not engine: engine = anaengines[0]
        spyanalyzer = discoverer.initEngine(engine, WHITE)
        spyanalyzer.analyze(inverse=True)
        specs[SPY] = spyanalyzer
        log.debug("Spy Analyzer: %s\n" % repr(spyanalyzer))
    
    # Setting game
    
    game.setPlayers(players)
    game.setSpectactors(specs)
    gmwidg.connect("closed", closeGame, game)
    if timemodel:
        gmwidg.widgets["ccalign"].show()
        gmwidg.widgets["cclock"].setModel(timemodel)
    
    return game, gmwidg

################################################################################
# newGame                                                                      #
################################################################################

def newGame ():
    setActiveSidePanel(None)
    widgets["newgamedialog"].set_title(_("New Game"))
    game, gmwidg = runNewGameDialog()
    if game:
        game.start()
        handler.emit("game_started", gmwidg, game)

def simpleNewGame (game, gmwidg):
    game.start()
    handler.emit("game_started", gmwidg, game)

################################################################################
# loadGame                                                                     #
################################################################################

def loadGame (uri = None):
    if uri:
        opendialog.set_uri(uri)
    
    res = opendialog.run()
    opendialog.hide()
    if res != gtk.RESPONSE_ACCEPT: return None, None
    
    setActiveSidePanel("loadsidepanel")
    widgets["newgamedialog"].set_title(_("Open Game"))
    game, gmwidg = runNewGameDialog()
    
    if game:
        uri = loadSidePanel.get_uri()
        loader = enddir[uri[uri.rfind(".")+1:]]
        simpleLoadGame(game, gmwidg, uri, loader,
                       loadSidePanel.get_gameno(), loadSidePanel.get_position())

def simpleLoadGame (game, gmwidg, uri, loader, gameno=0, position=-1):
    # As Main.py connects to game, when it recieves the game_started signal,
    # we have to emit it before loadAndStart is called, which emits signals
    # Main.py are supposed to recieve.
    handler.emit("game_started", gmwidg, game)
    game.loadAndStart (uri, gameno, position, loader)

################################################################################
# setUpPosition                                                                #
################################################################################

def setUpPosition ():
    setActiveSidePanel("setUpPositionSidePanel")
    widgets["newgamedialog"].set_title(_("Set up Game"))
    game, gmwidg = runNewGameDialog()
    if game:
        game.kill()
    
################################################################################
# enterGameNotation                                                            #
################################################################################

from cStringIO import StringIO

def enterGameNotation ():
    setActiveSidePanel("enterGameNotationSidePanel")
    widgets["newgamedialog"].set_title(_("Enter Game"))
    game, gmwidg = runNewGameDialog()
    
    if game:
        buf = sourceview.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
        file = StringIO(text)
        loader = enddir["pgn"]
        game.loadAndStart (file, 0, -1, loader)
        handler.emit("game_started", gmwidg, game)
        
################################################################################
# saveGame                                                                     #
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
    
################################################################################
# saveGameAs                                                                   #
################################################################################

def saveGameAs (game):
    
    def response (savedialog, res):
        if res != gtk.RESPONSE_ACCEPT:
            savedialog.disconnect(conid)
            savedialog.hide()
            return
        
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
                          _("<big><b>Unknown filetype '%s'</b></big>") % ending)
                d.format_secondary_text(_("Wasn't able to save '%s' as pychess doesn't know the format '%s'.") % (uri,ending))
                d.run()
                d.hide()
                return
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
            return
        
        if os.path.isfile(uri):
            d = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION)
            d.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, _("_Replace"),
                        gtk.RESPONSE_ACCEPT)
            if saver.__append__ == True:
                d.add_buttons(gtk.STOCK_ADD, 1)
            d.set_title(_("File exists"))
            folder, file = os.path.split(uri)
            d.set_markup(_("<big><b>A file named '%s' alredy exists. Would you like to replace it?</b></big>") % file)
            d.format_secondary_text(_("The file alredy exists in '%s'. If you replace it, its content will be overwritten.") % folder)
            res = d.run()
            d.hide()
            
            if res == 1:
                append = True
            elif res != gtk.RESPONSE_ACCEPT:
                return
        
        savedialog.disconnect(conid)
        savedialog.hide()
        game.save("file://"+uri, saver, append)
        
    conid = savedialog.connect("response", response)
    savedialog.show_all()

################################################################################
# saveGameBeforeClose                                                          #
################################################################################

def saveGameBeforeClose (game):
    
    if not game.isChanged(): return gtk.RESPONSE_OK

    d = gtk.MessageDialog (type = gtk.MESSAGE_WARNING)
    d.add_button(_("Close _without Saving"), gtk.RESPONSE_OK)
    d.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    d.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_YES)

    d.set_markup(_("<b><big>Save the current game before you close it?</big></b>"))
    d.format_secondary_text (_(
        "It is not possible later to continue the game,\nif do don't save it."))
    response = d.run()
    d.hide()
    
    if response == gtk.RESPONSE_YES:
        if saveGame(game) == False:
            return gtk.RESPONSE_CANCEL
    return response

################################################################################
# closeAllGames                                                                #
################################################################################

def closeAllGames (games):
    if len(games) == 1:
        return saveGameBeforeClose (games[0])
    
    names = ["%s vs %s" % tuple(g.players) for g in games if g.isChanged()]
    if len(names) == 0:
        return gtk.RESPONSE_OK
    d = gtk.MessageDialog (type = gtk.MESSAGE_WARNING)
    d.add_button(_("Close _without Saving"), gtk.RESPONSE_OK)
    d.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    if len(names) == 1:
        d.set_markup(
            _("<big><b>There is 1 game with unsaved changes:</b></big>"))
    else:
        d.set_markup(
            _("<big><b>There are %d games with unsaved changes:</b></big>") % len(names))
    d.format_secondary_text("\n".join(names))
    response = d.run()
    d.hide()
    return response

################################################################################
# closeGames                                                                   #
################################################################################

def closeGame (gmwidg, game):
    if saveGameBeforeClose (game) != gtk.RESPONSE_CANCEL:
        game.kill()
        gamewidget.delGameWidget (gmwidg)
        handler.emit("game_closed", gmwidg, game)

################################################################################
# signal handler                                                               #
################################################################################

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class Handler (GObject):
    """ The goal of this class, is to provide signal handling for the ionest
        module """
        
    __gsignals__ = {
        'game_started': (SIGNAL_RUN_FIRST, TYPE_NONE, (object, object)),
        'game_closed': (SIGNAL_RUN_FIRST, TYPE_NONE, (object, object))
    }
    
    def __init__ (self):
        GObject.__init__(self)

#nori: ugly?
handler = Handler()
