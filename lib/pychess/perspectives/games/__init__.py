""" The task of this perspective, is to save, load and init new games """

import asyncio
import os
import subprocess
import tempfile

from collections import defaultdict
from io import StringIO

from gi.repository import Gtk
from gi.repository import GObject

from pychess.Savers.ChessFile import LoadingError
from pychess.Savers import epd, fen, pgn, olv, png, database, html, txt
from pychess.System import conf
from pychess.System.Log import log
from pychess.System.protoopen import isWriteable
from pychess.System.uistuff import GladeWidgets
from pychess.System.prefix import addUserConfigPrefix
from pychess.Savers.pgn import parseDateTag
from pychess.Utils.const import UNFINISHED_STATES, ABORTED, ABORTED_AGREEMENT, LOCAL, ARTIFICIAL, MENU_ITEMS
from pychess.Utils.Offer import Offer
from pychess.widgets import gamewidget, mainwindow, new_notebook
from pychess.widgets.gamenanny import game_nanny
from pychess.perspectives import Perspective, perspective_manager, panel_name
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock.__init__ import CENTER, EAST, SOUTH
from pychess.ic.ICGameModel import ICGameModel

enddir = {}
savers = (pgn, epd, fen, olv, png, html, txt)  # chessalpha2 is broken

saveformats = Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT)
exportformats = Gtk.ListStore(str, str, GObject.TYPE_PYOBJECT)

auto = _("Detect type automatically")
saveformats.append([auto, "", None])
exportformats.append([auto, "", None])

for saver in savers:
    label, ending = saver.__label__, saver.__ending__
    endstr = "(%s)" % ending
    enddir[ending] = saver
    if hasattr(saver, "load"):
        saveformats.append([label, endstr, saver])
    else:
        exportformats.append([label, endstr, saver])


class Games(GObject.GObject, Perspective):
    __gsignals__ = {
        'gmwidg_created': (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        Perspective.__init__(self, "games", _("Games"))

        self.notebooks = {}
        self.first_run = True
        self.gamewidgets = set()
        self.gmwidg_cids = {}
        self.board_cids = {}
        self.notify_cids = defaultdict(list)

        self.key2gmwidg = {}
        self.key2cid = {}

        self.dock = None
        self.dockAlign = None
        self.dockLocation = addUserConfigPrefix("pydock.xml")

    @asyncio.coroutine
    def generalStart(self, gamemodel, player0tup, player1tup, loaddata=None):
        """ The player tuples are:
        (The type af player in a System.const value,
        A callable creating the player,
        A list of arguments for the callable,
        A preliminary name for the player)

        If loaddata is specified, it should be a tuple of:
        (A text uri or fileobj,
        A Savers.something module with a load function capable of loading it,
        An int of the game in file you want to load,
        The position from where to start the game)
        """

        log.debug("Games.generalStart: %s\n %s\n %s" %
                  (gamemodel, player0tup, player1tup))
        gmwidg = gamewidget.GameWidget(gamemodel, self)
        self.gamewidgets.add(gmwidg)
        self.gmwidg_cids[gmwidg] = gmwidg.connect("game_close_clicked", self.closeGame)

        # worker.publish((gmwidg,gamemodel))
        self.attachGameWidget(gmwidg)
        game_nanny.nurseGame(gmwidg, gamemodel)
        log.debug("Games.generalStart: -> emit gmwidg_created: %s" % (gmwidg))
        self.emit("gmwidg_created", gmwidg)
        log.debug("Games.generalStart: <- emit gmwidg_created: %s" % (gmwidg))

        # Initing players

        def xxxset_name(none, player, key, alt):
            player.setName(conf.get(key, alt))

        players = []
        for i, playertup in enumerate((player0tup, player1tup)):
            type, func, args, prename = playertup
            if type != LOCAL:
                if type == ARTIFICIAL:
                    player = yield from func(*args)
                else:
                    player = func(*args)
                players.append(player)
                # if type == ARTIFICIAL:
                #    def readyformoves (player, color):
                #        gmwidg.setTabText(gmwidg.display_text))
                #    players[i].connect("readyForMoves", readyformoves, i)
            else:
                # Until PyChess has a proper profiles system, as discussed on the
                # issue tracker, we need to give human players special treatment
                player = func(gmwidg, *args)
                players.append(player)
        assert len(players) == 2
        if player0tup[0] == ARTIFICIAL and player1tup[0] == ARTIFICIAL:

            def emit_action(board, action, player, param, gmwidg):
                if gmwidg.isInFront():
                    gamemodel.curplayer.emit("offer", Offer(action, param=param))

            self.board_cids[gmwidg.board] = gmwidg.board.connect("action", emit_action, gmwidg)

        log.debug("Games.generalStart: -> gamemodel.setPlayers(): %s" %
                  (gamemodel))
        gamemodel.setPlayers(players)
        log.debug("Games.generalStart: <- gamemodel.setPlayers(): %s" %
                  (gamemodel))

        # Forward information from the engines
        for playertup, tagname in ((player0tup, "WhiteElo"), (player1tup, "BlackElo")):
            if playertup[0] == ARTIFICIAL:
                elo = playertup[2][0].get("elo")
                if elo:
                    gamemodel.tags[tagname] = elo

        # Starting
        if loaddata:
            try:
                uri, loader, gameno, position = loaddata
                gamemodel.loadAndStart(uri, loader, gameno, position)
                if position != gamemodel.ply and position != -1:
                    gmwidg.board.view.shown = position
            except LoadingError as e:
                d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.WARNING,
                                      buttons=Gtk.ButtonsType.OK)
                d.set_markup(_("<big><b>Error loading game</big></b>"))
                d.format_secondary_text(", ".join(str(a) for a in e.args))
                d.show()
                d.destroy()

        else:
            if gamemodel.variant.need_initial_board:
                for player in gamemodel.players:
                    player.setOptionInitialBoard(gamemodel)
            log.debug("Games..generalStart: -> gamemodel.start(): %s" %
                      (gamemodel))
            gamemodel.emit("game_loaded", "")
            gamemodel.start()
            log.debug("Games.generalStart: <- gamemodel.start(): %s" %
                      (gamemodel))

        log.debug("Games.generalStart: returning gmwidg=%s\n gamemodel=%s" %
                  (gmwidg, gamemodel))

    ################################################################################
    # Saving                                                                       #
    ################################################################################

    def saveGame(self, game, position=None):
        if not game.isChanged():
            return
        if game.uri and isWriteable(game.uri):
            self.saveGameSimple(game.uri, game, position=position)
        else:
            return self.saveGameAs(game, position=position)

    def saveGameSimple(self, uri, game, position=None):
        ending = os.path.splitext(uri)[1]
        if not ending:
            return
        saver = enddir[ending[1:]]
        game.save(uri, saver, append=False, position=position)

    def saveGamePGN(self, game):
        if conf.get("saveOwnGames") and not game.hasLocalPlayer():
            return True

        filename = conf.get("autoSaveFormat")
        filename = filename.replace("#n1", game.tags["White"])
        filename = filename.replace("#n2", game.tags["Black"])
        year, month, day = parseDateTag(game.tags["Date"])
        year = '' if year is None else str(year)
        month = '' if month is None else str(month)
        day = '' if day is None else str(day)
        filename = filename.replace("#y", "%s" % year)
        filename = filename.replace("#m", "%s" % month)
        filename = filename.replace("#d", "%s" % day)
        pgn_path = conf.get("autoSavePath") + "/" + filename + ".pgn"
        append = True
        try:
            if not os.path.isfile(pgn_path):
                # create new file
                with open(pgn_path, "w"):
                    pass
            base_offset = os.path.getsize(pgn_path)

            # save to .sqlite
            database_path = os.path.splitext(pgn_path)[0] + '.sqlite'
            database.save(database_path, game, base_offset)

            # save to .scout
            from pychess.Savers.pgn import scoutfish_path
            if scoutfish_path is not None:
                pgn_text = pgn.save(StringIO(), game)

                tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
                pgnfile = tmp.name
                with tmp.file as f:
                    f.write(pgn_text)

                # create new .scout from pgnfile we are importing
                args = [scoutfish_path, "make", pgnfile, "%s" % base_offset]
                output = subprocess.check_output(args, stderr=subprocess.STDOUT)

                # append it to our existing one
                if output.decode().find(u"Processing...done") > 0:
                    old_scout = os.path.splitext(pgn_path)[0] + '.scout'
                    new_scout = os.path.splitext(pgnfile)[0] + '.scout'

                    with open(old_scout, "ab") as file1, open(new_scout, "rb") as file2:
                        file1.write(file2.read())

            # TODO: do we realy want to update .bin ? It can be huge/slow!

            # save to .pgn
            game.save(pgn_path, pgn, append)

            return True
        except IOError:
            return False

    def saveGameAs(self, game, position=None, export=False):
        savedialog, savecombo = get_save_dialog(export)

        # Keep running the dialog until the user has canceled it or made an error
        # free operation
        title = _("Save Game") if not export else _("Export position")
        savedialog.set_title(title)
        while True:
            filename = "%s-%s" % (game.players[0], game.players[1])
            savedialog.set_current_name(filename.replace(" ", "_"))

            res = savedialog.run()
            if res != Gtk.ResponseType.ACCEPT:
                break

            uri = savedialog.get_filename()
            ending = os.path.splitext(uri)[1]
            if ending.startswith("."):
                ending = ending[1:]
            append = False

            index = savecombo.get_active()
            if index == 0:
                if ending not in enddir:
                    d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                          buttons=Gtk.ButtonsType.OK)
                    folder, file = os.path.split(uri)
                    d.set_markup(_("<big><b>Unknown file type '%s'</b></big>") %
                                 ending)
                    d.format_secondary_text(_(
                        "Was unable to save '%(uri)s' as PyChess doesn't know the format '%(ending)s'.") %
                        {'uri': uri, 'ending': ending})
                    d.run()
                    d.destroy()
                    continue
                else:
                    saver = enddir[ending]
            else:
                format = exportformats[index] if export else saveformats[index]
                saver = format[2]
                if ending not in enddir or not saver == enddir[ending]:
                    uri += ".%s" % saver.__ending__

            if os.path.isfile(uri) and not os.access(uri, os.W_OK):
                d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR,
                                      buttons=Gtk.ButtonsType.OK)
                d.set_markup(_("<big><b>Unable to save file '%s'</b></big>") % uri)
                d.format_secondary_text(_(
                    "You don't have the necessary rights to save the file.\n\
    Please ensure that you have given the right path and try again."))
                d.run()
                d.destroy()
                continue

            if os.path.isfile(uri):
                d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.QUESTION)
                d.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                              _("_Replace"), Gtk.ResponseType.ACCEPT)
                if saver.__append__:
                    d.add_buttons(Gtk.STOCK_ADD, 1)
                d.set_title(_("File exists"))
                folder, file = os.path.split(uri)
                d.set_markup(_(
                    "<big><b>A file named '%s' already exists. Would you like to replace it?</b></big>") % file)
                d.format_secondary_text(_(
                    "The file already exists in '%s'. If you replace it, its content will be overwritten.") % folder)
                replaceRes = d.run()
                d.destroy()

                if replaceRes == 1:
                    append = True
                elif replaceRes == Gtk.ResponseType.CANCEL:
                    continue
            else:
                print(repr(uri))

            try:
                flip = self.cur_gmwidg().board.view.rotation > 0
                game.save(uri, saver, append, position, flip)
            except IOError as e:
                d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.ERROR)
                d.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
                d.set_title(_("Could not save the file"))
                d.set_markup(_(
                    "<big><b>PyChess was not able to save the game</b></big>"))
                d.format_secondary_text(_("The error was: %s") % ", ".join(
                    str(a) for a in e.args))
                d.run()
                d.destroy()
                continue

            break

        savedialog.destroy()
        return res

    ################################################################################
    # Closing                                                                      #
    ################################################################################
    def closeAllGames(self, gamewidgets):
        log.debug("Games.closeAllGames")
        response = None
        changedPairs = [(gmwidg, gmwidg.gamemodel) for gmwidg in gamewidgets
                        if gmwidg.gamemodel.isChanged()]
        if len(changedPairs) == 0:
            response = Gtk.ResponseType.OK

        elif len(changedPairs) == 1:
            response = self.closeGame(changedPairs[0][0])
        else:
            markup = "<big><b>" + ngettext("There is %d game with unsaved moves.",
                                           "There are %d games with unsaved moves.",
                                           len(changedPairs)) % len(changedPairs) + " " + \
                _("Save moves before closing?") + "</b></big>"

            for gmwidg, game in changedPairs:
                if not gmwidg.gamemodel.isChanged():
                    response = Gtk.ResponseType.OK
                else:
                    if conf.get("autoSave"):
                        x = self.saveGamePGN(game)
                        if x:
                            response = Gtk.ResponseType.OK
                        else:
                            response = None
                            markup = "<b><big>" + _("Unable to save to configured file. \
                                                    Save the games before closing?") + "</big></b>"
                            break

            if response is None:
                widgets = GladeWidgets("saveGamesDialog.glade")
                dialog = widgets["saveGamesDialog"]
                heading = widgets["saveGamesDialogHeading"]
                saveLabel = widgets["saveGamesDialogSaveLabel"]
                treeview = widgets["saveGamesDialogTreeview"]

                heading.set_markup(markup)

                liststore = Gtk.ListStore(bool, str)
                treeview.set_model(liststore)
                renderer = Gtk.CellRendererToggle()
                renderer.props.activatable = True
                treeview.append_column(Gtk.TreeViewColumn("", renderer, active=0))
                treeview.append_column(Gtk.TreeViewColumn("",
                                                          Gtk.CellRendererText(),
                                                          text=1))
                for gmwidg, game in changedPairs:
                    liststore.append((True, "%s %s %s" % (game.players[0], _("vs."), game.players[1])))

                def callback(cell, path):
                    if path:
                        liststore[path][0] = not liststore[path][0]
                    saves = len(tuple(row for row in liststore if row[0]))
                    saveLabel.set_text(ngettext(
                        "_Save %d document", "_Save %d documents", saves) % saves)
                    saveLabel.set_use_underline(True)

                renderer.connect("toggled", callback)

                callback(None, None)

                while True:
                    response = dialog.run()
                    if response == Gtk.ResponseType.YES:
                        for i in range(len(liststore) - 1, -1, -1):
                            checked, name = liststore[i]
                            if checked:
                                cgmwidg, cgame = changedPairs[i]
                                if self.saveGame(cgame) == Gtk.ResponseType.ACCEPT:
                                    liststore.remove(liststore.get_iter((i, )))
                                    del changedPairs[i]
                                    if cgame.status in UNFINISHED_STATES:
                                        cgame.end(ABORTED, ABORTED_AGREEMENT)
                                    cgame.terminate()
                                    self.delGameWidget(cgmwidg)
                                else:
                                    break
                        else:
                            break
                    else:
                        break
                dialog.destroy()

        if response not in (Gtk.ResponseType.DELETE_EVENT,
                            Gtk.ResponseType.CANCEL):
            pairs = [(gmwidg, gmwidg.gamemodel) for gmwidg in gamewidgets]
            for gmwidg, game in pairs:
                if game.status in UNFINISHED_STATES:
                    game.end(ABORTED, ABORTED_AGREEMENT)
                game.terminate()
                if gmwidg.notebookKey in self.key2gmwidg:
                    self.delGameWidget(gmwidg)

        return response

    def closeGame(self, gmwidg):
        log.debug("Games.closeGame")
        response = None
        if not gmwidg.gamemodel.isChanged():
            response = Gtk.ResponseType.OK
        else:
            markup = "<b><big>" + _("Save the current game before you close it?") + "</big></b>"
            if conf.get("autoSave"):
                x = self.saveGamePGN(gmwidg.gamemodel)
                if x:
                    response = Gtk.ResponseType.OK
                else:
                    markup = "<b><big>" + _("Unable to save to configured file. \
                                            Save the current game before you close it?") + "</big></b>"

            if response is None:
                d = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.WARNING)
                d.add_button(_("Close _without Saving"), Gtk.ResponseType.OK)
                d.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
                if gmwidg.gamemodel.uri:
                    d.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.YES)
                else:
                    d.add_button(Gtk.STOCK_SAVE_AS, Gtk.ResponseType.YES)

                gmwidg.bringToFront()

                d.set_markup(markup)
                d.format_secondary_text(_(
                    "It is not possible later to continue the game,\nif you don't save it."))

                response = d.run()
                d.destroy()

            if response == Gtk.ResponseType.YES:
                # Test if cancel was pressed in the save-file-dialog
                if self.saveGame(gmwidg.gamemodel) != Gtk.ResponseType.ACCEPT:
                    response = Gtk.ResponseType.CANCEL

        if response not in (Gtk.ResponseType.DELETE_EVENT,
                            Gtk.ResponseType.CANCEL):
            if gmwidg.gamemodel.status in UNFINISHED_STATES:
                gmwidg.gamemodel.end(ABORTED, ABORTED_AGREEMENT)

            gmwidg.disconnect(self.gmwidg_cids[gmwidg])
            del self.gmwidg_cids[gmwidg]

            for cid in self.notify_cids[gmwidg]:
                conf.notify_remove(cid)
            del self.notify_cids[gmwidg]

            if gmwidg.board in self.board_cids:
                gmwidg.board.disconnect(self.board_cids[gmwidg.board])
                del self.board_cids[gmwidg.board]

            self.delGameWidget(gmwidg)
            self.gamewidgets.remove(gmwidg)
            gmwidg.gamemodel.terminate()

            db_persp = perspective_manager.get_perspective("database")
            if len(self.gamewidgets) == 0:
                for widget in MENU_ITEMS:
                    if widget in ("copy_pgn", "copy_fen") and db_persp.preview_panel is not None:
                        continue
                    gamewidget.getWidgets()[widget].set_property('sensitive', False)

        return response

    def delGameWidget(self, gmwidg):
        """ Remove the widget from the GUI after the game has been terminated """
        log.debug("Games.delGameWidget: starting %s" % repr(gmwidg))
        gmwidg.closed = True
        gmwidg.emit("closed")

        called_from_preferences = False
        window_list = Gtk.Window.list_toplevels()
        widgets = gamewidget.getWidgets()
        for window in window_list:
            if window.is_active() and window == widgets["preferences"]:
                called_from_preferences = True
                break

        pageNum = gmwidg.getPageNumber()
        headbook = self.getheadbook()

        if gmwidg.notebookKey in self.key2gmwidg:
            del self.key2gmwidg[gmwidg.notebookKey]

        if gmwidg.notebookKey in self.key2cid:
            headbook.disconnect(self.key2cid[gmwidg.notebookKey])
            del self.key2cid[gmwidg.notebookKey]

        headbook.remove_page(pageNum)
        for notebook in self.notebooks.values():
            notebook.remove_page(pageNum)

        if headbook.get_n_pages() == 1 and conf.get("hideTabs"):
            self.show_tabs(False)

        if headbook.get_n_pages() == 0:
            if not called_from_preferences:
                # If the last (but not the designGW) gmwidg was closed
                # and we are FICS-ing, present the FICS lounge
                perspective_manager.disable_perspective("games")

        gmwidg._del()

    def init_layout(self):
        perspective_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        perspective_manager.set_perspective_widget("games", perspective_widget)

        self.notebooks = {"board": new_notebook("board"),
                          "buttons": new_notebook("buttons"),
                          "messageArea": new_notebook("messageArea")}
        self.main_notebook = self.notebooks["board"]
        for panel in self.sidePanels:
            self.notebooks[panel_name(panel.__name__)] = new_notebook(panel_name(panel.__name__))

        # Initing headbook

        align = gamewidget.createAlignment(4, 4, 0, 4)
        align.set_property("yscale", 0)

        headbook = Gtk.Notebook()
        headbook.set_name("headbook")
        headbook.set_scrollable(True)
        align.add(headbook)
        perspective_widget.pack_start(align, False, True, 0)
        self.show_tabs(not conf.get("hideTabs"))

        # Initing center

        centerVBox = Gtk.VBox()

        # The dock

        self.dock = PyDockTop("main", self)
        self.dockAlign = gamewidget.createAlignment(4, 4, 0, 4)
        self.dockAlign.add(self.dock)
        centerVBox.pack_start(self.dockAlign, True, True, 0)
        self.dockAlign.show()
        self.dock.show()

        self.docks["board"] = (Gtk.Label(label="Board"), self.notebooks["board"], None)
        for panel in self.sidePanels:
            self.docks[panel_name(panel.__name__)][1] = self.notebooks[panel_name(panel.__name__)]

        self.load_from_xml()

        # Default layout of side panels
        first_time_layout = False
        if not os.path.isfile(self.dockLocation):
            first_time_layout = True
            leaf = self.dock.dock(self.docks["board"][1],
                                  CENTER,
                                  Gtk.Label(label=self.docks["board"][0]),
                                  "board")
            self.docks["board"][1].show_all()
            leaf.setDockable(False)

            # S
            epanel = leaf.dock(self.docks["bookPanel"][1], SOUTH, self.docks["bookPanel"][0],
                               "bookPanel")
            epanel.default_item_height = 45
            epanel = epanel.dock(self.docks["engineOutputPanel"][1], CENTER,
                                 self.docks["engineOutputPanel"][0],
                                 "engineOutputPanel")

            # NE
            leaf = leaf.dock(self.docks["annotationPanel"][1], EAST,
                             self.docks["annotationPanel"][0], "annotationPanel")
            leaf = leaf.dock(self.docks["historyPanel"][1], CENTER,
                             self.docks["historyPanel"][0], "historyPanel")
            leaf = leaf.dock(self.docks["scorePanel"][1], CENTER,
                             self.docks["scorePanel"][0], "scorePanel")

            # SE
            leaf = leaf.dock(self.docks["chatPanel"][1], SOUTH, self.docks["chatPanel"][0],
                             "chatPanel")
            leaf = leaf.dock(self.docks["commentPanel"][1], CENTER,
                             self.docks["commentPanel"][0], "commentPanel")

        def unrealize(dock, notebooks):
            # unhide the panel before saving so its configuration is saved correctly
            self.notebooks["board"].get_parent().get_parent().zoomDown()
            dock.saveToXML(self.dockLocation)
            dock._del()

        self.dock.connect("unrealize", unrealize, self.notebooks)

        hbox = Gtk.HBox()

        # Buttons
        self.notebooks["buttons"].set_border_width(4)
        hbox.pack_start(self.notebooks["buttons"], False, True, 0)

        # The message area
        # TODO: If you try to fix this first read issue #958 and 1018
        align = gamewidget.createAlignment(0, 0, 0, 0)
        # sw = Gtk.ScrolledWindow()
        # port = Gtk.Viewport()
        # port.add(self.notebooks["messageArea"])
        # sw.add(port)
        # align.add(sw)
        align.add(self.notebooks["messageArea"])
        hbox.pack_start(align, True, True, 0)

        def ma_switch_page(notebook, gpointer, page_num):
            notebook.props.visible = notebook.get_nth_page(page_num).\
                get_child().props.visible

        self.notebooks["messageArea"].connect("switch-page", ma_switch_page)
        centerVBox.pack_start(hbox, False, True, 0)

        perspective_widget.pack_start(centerVBox, True, True, 0)
        centerVBox.show_all()
        perspective_widget.show_all()

        perspective_manager.set_perspective_menuitems("games", self.menuitems, default=first_time_layout)

        conf.notify_add("hideTabs", self.tabsCallback)

        # Connecting headbook to other notebooks

        def hb_switch_page(notebook, gpointer, page_num):
            for notebook in self.notebooks.values():
                notebook.set_current_page(page_num)

            gmwidg = self.key2gmwidg[self.getheadbook().get_nth_page(page_num)]
            if isinstance(gmwidg.gamemodel, ICGameModel):
                primary = "primary " + str(gmwidg.gamemodel.ficsgame.gameno)
                gmwidg.gamemodel.connection.client.run_command(primary)

        headbook.connect("switch-page", hb_switch_page)

        if hasattr(headbook, "set_tab_reorderable"):

            def page_reordered(widget, child, new_num, headbook):
                old_num = self.notebooks["board"].page_num(self.key2gmwidg[child].boardvbox)
                if old_num == -1:
                    log.error('Games and labels are out of sync!')
                else:
                    for notebook in self.notebooks.values():
                        notebook.reorder_child(
                            notebook.get_nth_page(old_num), new_num)

            headbook.connect("page-reordered", page_reordered, headbook)

    def adjust_divider(self, diff):
        """ Try to move paned (containing board) divider to show/hide captured pieces """
        if self.dock is None:
            return
        child = self.dock.get_children()[0]
        c1 = child.paned.get_child1()
        if hasattr(c1, "paned"):
            c1.paned.set_position(c1.paned.get_position() + diff)
        else:
            child.paned.set_position(child.paned.get_position() + diff)

    def getheadbook(self):
        if len(self.key2gmwidg) == 0:
            return None
        headbook = self.widget.get_children()[0].get_children()[0].get_child()
        # to help StoryText create widget description
        # headbook.get_tab_label_text = customGetTabLabelText
        return headbook

    def cur_gmwidg(self):
        if len(self.key2gmwidg) == 0:
            return None
        headbook = self.getheadbook()
        notebookKey = headbook.get_nth_page(headbook.get_current_page())
        return self.key2gmwidg[notebookKey]

    def customGetTabLabelText(self, child):
        gmwidg = self.key2gmwidg[child]
        return gmwidg.display_text

    def zoomToBoard(self, view_zoomed):
        if not self.notebooks["board"].get_parent():
            return
        if view_zoomed:
            self.notebooks["board"].get_parent().get_parent().zoomUp()
        else:
            self.notebooks["board"].get_parent().get_parent().zoomDown()

    def show_tabs(self, show):
        head = self.getheadbook()
        if head is None:
            return
        head.set_show_tabs(show)

    def tabsCallback(self, widget):
        head = self.getheadbook()
        if not head:
            return
        if head.get_n_pages() == 1:
            self.show_tabs(not conf.get("hideTabs"))

    def attachGameWidget(self, gmwidg):
        log.debug("attachGameWidget: %s" % gmwidg)
        if self.first_run:
            self.init_layout()
            self.first_run = False
        perspective_manager.activate_perspective("games")

        gmwidg.panels = [panel.Sidepanel().load(gmwidg) for panel in self.sidePanels]
        self.key2gmwidg[gmwidg.notebookKey] = gmwidg
        headbook = self.getheadbook()

        headbook.append_page(gmwidg.notebookKey, gmwidg.tabcontent)
        gmwidg.notebookKey.show_all()

        if hasattr(headbook, "set_tab_reorderable"):
            headbook.set_tab_reorderable(gmwidg.notebookKey, True)

        def callback(notebook, gpointer, page_num, gmwidg):
            if notebook.get_nth_page(page_num) == gmwidg.notebookKey:
                gmwidg.infront()
                if gmwidg.gamemodel.players and gmwidg.gamemodel.isObservationGame():
                    gmwidg.light_on_off(False)
                    text = gmwidg.game_info_label.get_text()
                    gmwidg.game_info_label.set_markup(
                        '<span color="black" weight="bold">%s</span>' % text)

        self.key2cid[gmwidg.notebookKey] = headbook.connect_after("switch-page", callback, gmwidg)
        gmwidg.infront()

        align = gamewidget.createAlignment(0, 0, 0, 0)
        align.show()
        align.add(gmwidg.infobar)
        self.notebooks["messageArea"].append_page(align, None)
        self.notebooks["board"].append_page(gmwidg.boardvbox, None)
        gmwidg.boardvbox.show_all()
        for panel, instance in zip(self.sidePanels, gmwidg.panels):
            self.notebooks[panel_name(panel.__name__)].append_page(instance, None)
            instance.show_all()
        self.notebooks["buttons"].append_page(gmwidg.stat_hbox, None)
        gmwidg.stat_hbox.show_all()

        if headbook.get_n_pages() == 1:
            self.show_tabs(not conf.get("hideTabs"))
        else:
            # We should always show tabs if more than one exists
            self.show_tabs(True)

        headbook.set_current_page(-1)

        widgets = gamewidget.getWidgets()
        if headbook.get_n_pages() == 1 and not widgets["show_sidepanels"].get_active():
            self.zoomToBoard(True)


def get_save_dialog(export=False):
    savedialog = Gtk.FileChooserDialog(
        "", mainwindow(), Gtk.FileChooserAction.SAVE,
        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE,
         Gtk.ResponseType.ACCEPT))
    savedialog.set_current_folder(os.path.expanduser("~"))

    # Add widgets to the savedialog
    savecombo = Gtk.ComboBox()
    savecombo.set_name("savecombo")

    crt = Gtk.CellRendererText()
    savecombo.pack_start(crt, True)
    savecombo.add_attribute(crt, 'text', 0)

    crt = Gtk.CellRendererText()
    savecombo.pack_start(crt, False)
    savecombo.add_attribute(crt, 'text', 1)

    if export:
        savecombo.set_model(exportformats)
    else:
        savecombo.set_model(saveformats)

    savecombo.set_active(1)  # pgn
    savedialog.set_extra_widget(savecombo)

    return savedialog, savecombo


def get_open_dialog():
    opendialog = Gtk.FileChooserDialog(
        _("Open chess file"), mainwindow(), Gtk.FileChooserAction.OPEN,
        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
         Gtk.ResponseType.OK))
    opendialog.set_show_hidden(True)
    opendialog.set_select_multiple(True)

    # All chess files filter
    all_filter = Gtk.FileFilter()
    all_filter.set_name(_("All Chess Files"))
    opendialog.add_filter(all_filter)
    opendialog.set_filter(all_filter)

    # Specific filters and save formats
    for ending, saver in enddir.items():
        label = saver.__label__
        endstr = "(%s)" % ending
        f = Gtk.FileFilter()
        f.set_name(label + " " + endstr)
        if hasattr(saver, "load"):
            f.add_pattern("*." + ending)
            all_filter.add_pattern("*." + ending)
            opendialog.add_filter(f)

    return opendialog
