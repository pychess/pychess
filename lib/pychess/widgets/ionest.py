""" The task of this module, is to save, load and init new games """

import asyncio
import os
import subprocess
import tempfile
from collections import defaultdict
from io import StringIO

from gi.repository import Gtk
from gi.repository import GObject

from pychess.Savers.ChessFile import LoadingError
from pychess.Savers import chessalpha2, epd, fen, pgn, png, database
from pychess.System import conf
from pychess.System.Log import log
from pychess.System.protoopen import isWriteable
from pychess.System.uistuff import GladeWidgets
from pychess.Utils.const import UNFINISHED_STATES, ABORTED, ABORTED_AGREEMENT, LOCAL, ARTIFICIAL, MENU_ITEMS
from pychess.Utils.Offer import Offer
from pychess.widgets import gamewidget
from pychess.widgets.gamenanny import game_nanny
from pychess.perspectives import perspective_manager


enddir = {}
savers = (pgn, epd, fen, png, chessalpha2)

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


class GameHandler(GObject.GObject):

    __gsignals__ = {
        'gmwidg_created': (GObject.SignalFlags.RUN_FIRST, None, (object, ))
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.gamewidgets = set()
        self.gmwidg_cids = {}
        self.board_cids = {}
        self.notify_cids = defaultdict(list)

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

        log.debug("ionest.generalStart: %s\n %s\n %s" %
                  (gamemodel, player0tup, player1tup))
        gmwidg = gamewidget.GameWidget(gamemodel)
        self.gamewidgets.add(gmwidg)
        self.gmwidg_cids[gmwidg] = gmwidg.connect("game_close_clicked", self.closeGame)

        # worker.publish((gmwidg,gamemodel))
        gamewidget.attachGameWidget(gmwidg)
        game_nanny.nurseGame(gmwidg, gamemodel)
        log.debug("ionest.generalStart: -> emit gmwidg_created: %s" % (gmwidg))
        self.emit("gmwidg_created", gmwidg)
        log.debug("ionest.generalStart: <- emit gmwidg_created: %s" % (gmwidg))

        # Initing players

        def set_name(none, player, key, alt):
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

                # Connect to conf
                if i == 0 or (i == 1 and player0tup[0] != LOCAL):
                    key = "firstName"
                    alt = _("You")
                else:
                    key = "secondName"
                    alt = _("Guest")

                if prename == conf.get(key, alt):
                    self.notify_cids[gmwidg].append(conf.notify_add(key, set_name, player, key, alt))

        if player0tup[0] == ARTIFICIAL and player1tup[0] == ARTIFICIAL:

            def emit_action(board, action, param, gmwidg):
                if gmwidg.isInFront():
                    gamemodel.curplayer.emit("offer", Offer(action, param=param))

            self.board_cids[gmwidg.board] = gmwidg.board.connect("action", emit_action, gmwidg)

        log.debug("ionest.generalStart: -> gamemodel.setPlayers(): %s" %
                  (gamemodel))
        gamemodel.setPlayers(players)
        log.debug("ionest.generalStart: <- gamemodel.setPlayers(): %s" %
                  (gamemodel))

        # Starting
        if loaddata:
            try:
                uri, loader, gameno, position = loaddata
                gamemodel.loadAndStart(uri, loader, gameno, position)
                if position != gamemodel.ply:
                    gmwidg.board.view.shown = position
            except LoadingError as e:
                d = Gtk.MessageDialog(type=Gtk.MessageType.WARNING,
                                      buttons=Gtk.ButtonsType.OK)
                d.set_markup(_("<big><b>Error loading game</big></b>"))
                d.format_secondary_text(", ".join(str(a) for a in e.args))
                d.show()
                d.hide()

        else:
            if gamemodel.variant.need_initial_board:
                for player in gamemodel.players:
                    player.setOptionInitialBoard(gamemodel)
            log.debug("ionest..generalStart: -> gamemodel.start(): %s" %
                      (gamemodel))

            gamemodel.start()
            log.debug("ionest.generalStart: <- gamemodel.start(): %s" %
                      (gamemodel))

        log.debug("ionest.generalStart: returning gmwidg=%s\n gamemodel=%s" %
                  (gmwidg, gamemodel))

    ################################################################################
    # Creating .pgn                                                                #
    ################################################################################

    def create_database(self):
        dialog = Gtk.FileChooserDialog(
            _("Create New Pgn Database"), None, Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_NEW, Gtk.ResponseType.ACCEPT))

        dialog.set_current_folder(os.path.expanduser("~"))
        dialog.set_current_name("new.pgn")

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            new_pgn = dialog.get_filename()
            if not new_pgn.endswith(".pgn"):
                new_pgn = "%s.pgn" % new_pgn

            if not os.path.isfile(new_pgn):
                perspective = perspective_manager.get_perspective("database")
                # create new file
                with open(new_pgn, "w"):
                    pass
                perspective.open_chessfile(new_pgn)
            else:
                d = Gtk.MessageDialog(type=Gtk.MessageType.ERROR,
                                      buttons=Gtk.ButtonsType.OK)
                d.set_markup(_("<big><b>File '%s' already exists.</b></big>") % new_pgn)
                d.run()
                d.hide()
                print("%s allready exist." % new_pgn)

        dialog.destroy()

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
        if conf.get("saveOwnGames", False) and not game.hasLocalPlayer():
            return True
        filename = conf.get("autoSaveFormat", "pychess")
        filename = filename.replace("#n1", game.tags["White"])
        filename = filename.replace("#n2", game.tags["Black"])
        filename = filename.replace("#y", "%s" % game.tags["Year"])
        filename = filename.replace("#m", "%s" % game.tags["Month"])
        filename = filename.replace("#d", "%s" % game.tags["Day"])
        pgn_path = conf.get("autoSavePath", os.path.expanduser("~")) + \
            "/" + filename + ".pgn"
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

                tmp = tempfile.NamedTemporaryFile(mode="w", delete=False)
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
            savedialog.set_current_name(
                "%s %s %s" % (game.players[0], _("vs."), game.players[1]))

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
                    d = Gtk.MessageDialog(type=Gtk.MessageType.ERROR,
                                          buttons=Gtk.ButtonsType.OK)
                    folder, file = os.path.split(uri)
                    d.set_markup(_("<big><b>Unknown file type '%s'</b></big>") %
                                 ending)
                    d.format_secondary_text(_(
                        "Was unable to save '%(uri)s' as PyChess doesn't know the format '%(ending)s'.") %
                        {'uri': uri, 'ending': ending})
                    d.run()
                    d.hide()
                    continue
                else:
                    saver = enddir[ending]
            else:
                format = exportformats[index] if export else saveformats[index]
                saver = format[2]
                if ending not in enddir or not saver == enddir[ending]:
                    uri += ".%s" % saver.__ending__

            if os.path.isfile(uri) and not os.access(uri, os.W_OK):
                d = Gtk.MessageDialog(type=Gtk.MessageType.ERROR,
                                      buttons=Gtk.ButtonsType.OK)
                d.set_markup(_("<big><b>Unable to save file '%s'</b></big>") % uri)
                d.format_secondary_text(_(
                    "You don't have the necessary rights to save the file.\n\
    Please ensure that you have given the right path and try again."))
                d.run()
                d.hide()
                continue

            if os.path.isfile(uri):
                d = Gtk.MessageDialog(type=Gtk.MessageType.QUESTION)
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
                d.hide()

                if replaceRes == 1:
                    append = True
                elif replaceRes == Gtk.ResponseType.CANCEL:
                    continue
            else:
                print(repr(uri))

            try:
                game.save(uri, saver, append, position)
            except IOError as e:
                d = Gtk.MessageDialog(type=Gtk.MessageType.ERROR)
                d.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
                d.set_title(_("Could not save the file"))
                d.set_markup(_(
                    "<big><b>PyChess was not able to save the game</b></big>"))
                d.format_secondary_text(_("The error was: %s") % ", ".join(
                    str(a) for a in e.args))
                d.run()
                d.hide()
                continue

            break

        savedialog.destroy()
        return res

    ################################################################################
    # Closing                                                                      #
    ################################################################################
    def closeAllGames(self, gamewidgets):
        log.debug("ionest.closeAllGames")
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
                    if conf.get("autoSave", False):
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
                                    gamewidget.delGameWidget(cgmwidg)
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
                if gmwidg.notebookKey in gamewidget.key2gmwidg:
                    gamewidget.delGameWidget(gmwidg)

        return response

    def closeGame(self, gmwidg):
        log.debug("ionest.closeGame")
        response = None
        if not gmwidg.gamemodel.isChanged():
            response = Gtk.ResponseType.OK
        else:
            markup = "<b><big>" + _("Save the current game before you close it?") + "</big></b>"
            if conf.get("autoSave", False):
                x = self.saveGamePGN(gmwidg.gamemodel)
                if x:
                    response = Gtk.ResponseType.OK
                else:
                    markup = "<b><big>" + _("Unable to save to configured file. \
                                            Save the current game before you close it?") + "</big></b>"

            if response is None:
                d = Gtk.MessageDialog(type=Gtk.MessageType.WARNING)
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

            gamewidget.delGameWidget(gmwidg)
            self.gamewidgets.remove(gmwidg)
            gmwidg.gamemodel.terminate()

            if len(self.gamewidgets) == 0:
                for widget in MENU_ITEMS:
                    gamewidget.getWidgets()[widget].set_property('sensitive', False)

        return response

game_handler = GameHandler()


def get_save_dialog(export=False):
    mainwindow = gamewidget.getWidgets()["main_window"]
    savedialog = Gtk.FileChooserDialog(
        "", mainwindow, Gtk.FileChooserAction.SAVE,
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
    mainwindow = gamewidget.getWidgets()["main_window"]
    opendialog = Gtk.FileChooserDialog(
        _("Open chess file"), mainwindow, Gtk.FileChooserAction.OPEN,
        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN,
         Gtk.ResponseType.ACCEPT))
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
