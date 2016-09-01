# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk

from pychess.Utils.const import FEN_EMPTY
from pychess.Utils.Board import Board
from pychess.widgets.BoardView import BoardView
from pychess.Savers.ChessFile import LoadingError


class PreviewPanel:
    def __init__(self, gamelist):
        self.gamelist = gamelist

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        selection = self.gamelist.get_selection()
        self.conid = selection.connect_after('changed', self.on_selection_changed)
        self.gamelist.preview_cid = self.conid

        # buttons
        toolbar = Gtk.Toolbar()

        firstButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_PREVIOUS)
        toolbar.insert(firstButton, -1)

        prevButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_REWIND)
        toolbar.insert(prevButton, -1)

        nextButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_FORWARD)
        toolbar.insert(nextButton, -1)

        lastButton = Gtk.ToolButton(Gtk.STOCK_MEDIA_NEXT)
        toolbar.insert(lastButton, -1)

        firstButton.connect("clicked", self.on_first_clicked)
        prevButton.connect("clicked", self.on_prev_clicked)
        nextButton.connect("clicked", self.on_next_clicked)
        lastButton.connect("clicked", self.on_last_clicked)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, False, False, 0)

        # board
        self.boardview = BoardView(preview=True)
        self.boardview.set_size_request(170, 170)

        self.gamemodel = self.boardview.model
        self.boardview.got_started = True
        self.boardview.auto_update_shown = False

        self.box.pack_start(self.boardview, True, True, 0)
        self.box.pack_start(tool_box, False, True, 0)
        self.box.show_all()

        # force first game to show
        self.gamelist.set_cursor(0)

    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()
        if iter is None:
            self.gamemodel.boards = [Board(FEN_EMPTY)]
            del self.gamemodel.moves[:]
            self.boardview.shown = 0
            self.boardview.redrawCanvas()
            return

        path = self.gamelist.get_model().get_path(iter)

        gameno = self.gamelist.get_gameno(path)

        self.boardview.animation_lock.acquire()
        try:
            try:
                self.gamelist.chessfile.loadToModel(gameno, -1, self.gamemodel)
            except LoadingError as err:
                dialogue = Gtk.MessageDialog(type=Gtk.MessageType.WARNING,
                                             buttons=Gtk.ButtonsType.OK,
                                             message_format=err.args[0])
                if len(err.args) > 1:
                    dialogue.format_secondary_text(err.args[1])
                dialogue.connect("response", lambda dialogue, a: dialogue.hide())
                dialogue.show()

            self.boardview.lastMove = None
            self.boardview._shown = self.gamemodel.lowply
        finally:
            self.boardview.animation_lock.release()

        self.boardview.redrawCanvas()
        self.boardview.shown = self.gamelist.ply

    def on_first_clicked(self, button):
        self.boardview.showFirst()

    def on_prev_clicked(self, button):
        self.boardview.showPrev()

    def on_next_clicked(self, button):
        self.boardview.showNext()

    def on_last_clicked(self, button):
        self.boardview.showLast()
