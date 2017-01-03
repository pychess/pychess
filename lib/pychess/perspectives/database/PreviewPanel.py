# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk

from pychess.Utils.const import FEN_EMPTY
from pychess.Utils.Board import Board
from pychess.Utils.GameModel import GameModel
from pychess.widgets.BoardControl import BoardControl
from pychess.Savers.ChessFile import LoadingError


class PreviewPanel:
    def __init__(self, gamelist):
        self.gamelist = gamelist

        self.filtered = False

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

        filterButton = Gtk.ToggleToolButton(Gtk.STOCK_FIND)
        toolbar.insert(filterButton, -1)

        firstButton.connect("clicked", self.on_first_clicked)
        prevButton.connect("clicked", self.on_prev_clicked)
        nextButton.connect("clicked", self.on_next_clicked)
        lastButton.connect("clicked", self.on_last_clicked)
        filterButton.connect("clicked", self.on_filter_clicked)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, False, False, 0)

        # board
        self.gamemodel = GameModel()
        self.boardcontrol = BoardControl(self.gamemodel, {}, game_preview=True)
        self.boardview = self.boardcontrol.view
        self.boardview.set_size_request(170, 170)

        self.boardview.got_started = True
        self.boardview.auto_update_shown = False

        self.box.pack_start(self.boardcontrol, True, True, 0)
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

        rec = self.gamelist.get_record(path)

        self.boardview.animation_lock.acquire()
        try:
            try:
                self.gamelist.chessfile.loadToModel(rec, -1, self.gamemodel)
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
        self.update_gamelist()

    def on_prev_clicked(self, button):
        self.boardview.showPrev()
        self.update_gamelist()

    def on_next_clicked(self, button):
        self.boardview.showNext()
        self.update_gamelist()

    def on_last_clicked(self, button):
        self.boardview.showLast()
        self.update_gamelist()

    def on_filter_clicked(self, button):
        self.filtered = button.get_active()
        self.update_gamelist()

    def update_gamelist(self):
        if not self.filtered:
            return

        self.board = self.gamemodel.boards[self.boardview.shown].board

        self.gamelist.ply = self.board.plyCount
        self.gamelist.chessfile.set_fen_filter(self.board.asFen())
        self.gamelist.load_games()
