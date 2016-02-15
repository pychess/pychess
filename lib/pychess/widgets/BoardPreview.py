# -*- coding: UTF-8 -*-
from __future__ import print_function

import os
from gi.repository import Gtk

from pychess.compat import unicode
from pychess.System import conf
from pychess.Utils.const import reprResult, FEN_EMPTY, NORMALCHESS
from pychess.Utils.Board import Board
from pychess.System.protoopen import protoopen, splitUri
from pychess.widgets.BoardView import BoardView
from pychess.Savers.ChessFile import LoadingError


def ellipsize(string, maxlen):
    """ Description: given a string and a length ellipsize will return the string
        if it is smaller than length or it will return the string truncated to length
        and append ... to it

        Return type : str
    """
    if len(string) <= maxlen or maxlen < 4:
        return string
    return string[:maxlen - 1] + unicode("…")


class BoardPreview:
    def __init__(self, widgets, fcbutton, opendialog, enddir):
        self.position = 0
        self.gameno = 0
        self.filename = None
        self.chessfile = None

        self.widgets = widgets
        self.fcbutton = fcbutton
        self.opendialog = opendialog
        self.enddir = enddir

        # Treeview
        self.list = self.widgets["gamesTree"]
        self.list.set_model(Gtk.ListStore(str, str, str, str))
        # GTK_SELECTION_BROWSE - exactly one item is always selected
        self.list.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.list.get_selection().connect_after('changed',
                                                self.onSelectionChanged)

        # Add columns
        renderer = Gtk.CellRendererText()
        renderer.set_property("xalign", 0)
        self.list.append_column(Gtk.TreeViewColumn(None, renderer, text=0))

        self.list.append_column(Gtk.TreeViewColumn(None, renderer, text=1))
        self.list.append_column(Gtk.TreeViewColumn(None, renderer, text=2))

        renderer = Gtk.CellRendererText()
        renderer.set_property("xalign", 1)
        self.list.append_column(Gtk.TreeViewColumn(None, renderer, text=3))

        # Connect buttons
        self.widgets["first_button"].connect("clicked", self.onFirstButton)
        self.widgets["back_button"].connect("clicked", self.onBackButton)
        self.widgets["forward_button"].connect("clicked",
                                               self.onForwardButton)
        self.widgets["last_button"].connect("clicked", self.onLastButton)

        # Add the board
        self.boardview = BoardView(preview=True)
        self.boardview.set_size_request(170, 170)
        self.widgets["boardPreviewDock"].add(self.boardview)
        self.boardview.show()
        self.gamemodel = self.boardview.model
        self.boardview.got_started = True

        # Connect label showing possition
        self.boardview.connect('shownChanged', self.shownChanged)
        self.boardview.auto_update_shown = False

        # Add the filechooserbutton
        self.widgets["fileChooserDock"].add(fcbutton)

        def onFileSet(*args):
            fcbutton = args[0]
            self.onFileActivated(fcbutton.get_filename())

        fcbutton.connect("file-set", onFileSet)
        # This is needed for game files specified on the command line to work
        fcbutton.connect("file-activated", onFileSet)

        def onResponse(fcdialog, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                self.onFileActivated(opendialog.get_filename())

        opendialog.connect("response", onResponse)

    def onFileActivated(self, filename):
        # filename is None if a non-existent file is passed as command line argument
        if filename is None:
            return
        self.set_filename(filename)
        if os.path.isdir(filename):
            return

        ending = filename[filename.rfind(".") + 1:]
        loader = self.enddir[ending]
        self.chessfile = chessfile = loader.load(protoopen(filename))

        self.list.get_model().clear()
        for gameno in range(len(chessfile)):
            names = chessfile.get_player_names(gameno)
            names = [ellipsize(name, 9) for name in names]
            result = reprResult[chessfile.get_result(gameno)]
            result = result.replace("1/2", "½")
            self.list.get_model().append(["%s." % (gameno + 1)] + names +
                                         [result])

        self.last_sel = -1  # The row that was last selected
        self.list.set_cursor((0, ))

        self.widgets["whitePlayerCombobox"].set_active(0)
        self.widgets["blackPlayerCombobox"].set_active(0)

    def onSelectionChanged(self, selection):
        iter = selection.get_selected()[1]
        if iter is None:
            self.gamemodel.boards = [Board(FEN_EMPTY)]
            del self.gamemodel.moves[:]
            self.boardview.shown = 0
            self.boardview.redrawCanvas()
            return

        path = self.list.get_model().get_path(iter)
        indices = path.get_indices()
        sel = indices[0]
        if sel == self.last_sel:
            return
        self.last_sel = sel

        self.boardview.animation_lock.acquire()
        try:
            try:
                self.chessfile.loadToModel(sel, -1, self.gamemodel)
            except LoadingError as err:
                dialogue = Gtk.MessageDialog(type=Gtk.MessageType.WARNING,
                                             buttons=Gtk.ButtonsType.OK,
                                             message_format=err.args[0])
                dialogue.format_secondary_text(err.args[1])
                dialogue.connect("response", lambda dialogue, a: dialogue.hide())
                dialogue.show()

            if self.gamemodel.variant.variant == NORMALCHESS:
                radiobutton = self.widgets["playNormalRadio"]
                radiobutton.set_active(True)
            else:
                radiobutton = self.widgets["playVariant1Radio"]
                radiobutton.set_active(True)
                conf.set("ngvariant1", self.gamemodel.variant.variant)
                radiobutton.set_label("%s" % self.gamemodel.variant.name)

            if self.gamemodel.tags.get("TimeControl"):
                radiobutton = self.widgets["blitzRadio"]
                radiobutton.set_active(True)
                conf.set("ngblitz min", self.gamemodel.timemodel.minutes)
                conf.set("ngblitz gain", self.gamemodel.timemodel.gain)
            else:
                radiobutton = self.widgets["notimeRadio"]
                radiobutton.set_active(True)

            self.boardview.lastMove = None
            self.boardview._shown = self.gamemodel.lowply
            last = self.gamemodel.ply
        finally:
            self.boardview.animation_lock.release()
        self.boardview.redrawCanvas()
        self.boardview.shown = last
        self.shownChanged(self.boardview, last)

    def onFirstButton(self, button):
        self.boardview.showFirst()

    def onBackButton(self, button):
        self.boardview.showPrev()

    def onForwardButton(self, button):
        self.boardview.showNext()

    def onLastButton(self, button):
        self.boardview.showLast()

    def shownChanged(self, board_view, shown):
        pos = "%d." % (shown / 2 + 1)
        if shown & 1:
            pos += ".."
        self.widgets["posLabel"].set_text(pos)

    def set_filename(self, filename):
        as_path = splitUri(filename)[-1]
        if os.path.isfile(as_path):
            self.fcbutton.show()
            # if filename != self._retrieve_filename():
            #    self.fcbutton.set_filename(os.path.abspath(as_path))
            self.fcbutton.set_filename(os.path.abspath(as_path))
        else:
            self.fcbutton.set_uri("")
            self.fcbutton.hide()
        self.filename = filename

    def get_filename(self):
        return self.filename

    def isEmpty(self):
        return not self.chessfile or not len(self.chessfile)

    def getPosition(self):
        return self.boardview.shown

    def getGameno(self):
        iter = self.list.get_selection().get_selected()[1]
        if iter is None:
            return -1
        path = self.list.get_model().get_path(iter)
        indices = path.get_indices()
        return indices[0]
