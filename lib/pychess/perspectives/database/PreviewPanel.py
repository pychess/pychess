# -*- coding: UTF-8 -*-

from gi.repository import Gtk

from pychess.Utils.const import EMPTY, FEN_EMPTY, FEN_START
from pychess.Utils.Board import Board
from pychess.Utils.Cord import Cord
from pychess.widgets.BoardControl import BoardControl
from pychess.Savers.ChessFile import LoadingError
from pychess.System.prefix import addDataPrefix
from pychess.widgets import mainwindow

__title__ = _("Preview")

__icon__ = addDataPrefix("glade/panel_games.svg")

__desc__ = _("Preview panel can filter game list by current game moves")


class PreviewPanel:
    def __init__(self, persp):
        self.persp = persp
        self.filtered = False

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # buttons
        toolbar = Gtk.Toolbar()

        firstButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_PREVIOUS)
        toolbar.insert(firstButton, -1)

        prevButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_REWIND)
        toolbar.insert(prevButton, -1)

        nextButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_FORWARD)
        toolbar.insert(nextButton, -1)

        lastButton = Gtk.ToolButton(stock_id=Gtk.STOCK_MEDIA_NEXT)
        toolbar.insert(lastButton, -1)

        self.filterButton = Gtk.ToggleToolButton(Gtk.STOCK_FIND)
        self.filterButton.set_tooltip_text(_("Filter game list by current game moves"))
        toolbar.insert(self.filterButton, -1)

        addButton = Gtk.ToolButton(stock_id=Gtk.STOCK_ADD)
        addButton.set_tooltip_text(_("Add sub-fen filter from position/circles"))
        toolbar.insert(addButton, -1)

        firstButton.connect("clicked", self.on_first_clicked)
        prevButton.connect("clicked", self.on_prev_clicked)
        nextButton.connect("clicked", self.on_next_clicked)
        lastButton.connect("clicked", self.on_last_clicked)

        addButton.connect("clicked", self.on_add_clicked)
        self.filterButton.connect("clicked", self.on_filter_clicked)

        tool_box = Gtk.Box()
        tool_box.pack_start(toolbar, False, False, 0)

        # board
        self.gamemodel = self.persp.gamelist.gamemodel
        self.boardcontrol = BoardControl(self.gamemodel, {}, game_preview=True)
        self.boardview = self.boardcontrol.view
        self.board = self.gamemodel.boards[self.boardview.shown].board
        self.boardview.set_size_request(170, 170)

        self.boardview.got_started = True
        self.boardview.auto_update_shown = False

        self.box.pack_start(self.boardcontrol, True, True, 0)
        self.box.pack_start(tool_box, False, True, 0)
        self.box.show_all()

        selection = self.persp.gamelist.get_selection()
        self.conid = selection.connect_after('changed', self.on_selection_changed)
        self.persp.gamelist.preview_cid = self.conid

        # force first game to show
        self.persp.gamelist.set_cursor(0)

    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()
        if iter is None:
            self.gamemodel.boards = [Board(FEN_EMPTY)]
            del self.gamemodel.moves[:]
            self.boardview.shown = 0
            self.boardview.redrawCanvas()
            return

        path = self.persp.gamelist.get_model().get_path(iter)

        rec, ply = self.persp.gamelist.get_record(path)
        if rec is None:
            return

        try:
            self.persp.chessfile.loadToModel(rec, -1, self.gamemodel)
        except LoadingError as err:
            dialogue = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.WARNING,
                                         buttons=Gtk.ButtonsType.OK,
                                         message_format=err.args[0])
            if len(err.args) > 1:
                dialogue.format_secondary_text(err.args[1])
            dialogue.connect("response", lambda dialogue, a: dialogue.hide())
            dialogue.show()
        self.boardview.noAnimation = True
        self.boardview.lastMove = None
        self.boardview._shown = self.gamemodel.lowply

        if ply > 0 or self.persp.gamelist.ply > 0:
            self.boardview.shown = ply if ply > 0 else self.persp.gamelist.ply
        else:
            self.boardview.shown = self.boardview.model.ply

    def on_first_clicked(self, button):
        self.boardview.showFirst()
        if self.filtered:
            self.update_gamelist()

    def on_prev_clicked(self, button):
        self.boardview.showPrev()
        if self.filtered:
            self.update_gamelist()

    def on_next_clicked(self, button):
        self.boardview.showNext()
        if self.filtered:
            self.update_gamelist()

    def on_last_clicked(self, button):
        self.boardview.showLast()
        if self.filtered:
            self.update_gamelist()

    def on_filter_clicked(self, button):
        self.filtered = button.get_active()
        if not self.filtered:
            self.persp.filter_panel.filterButton.set_sensitive(True)
            self.boardview.showFirst()
            self.filtered = True
            self.update_gamelist()
            self.filtered = False
        else:
            self.persp.filter_panel.filterButton.set_sensitive(False)
            self.update_gamelist()

    def on_add_clicked(self, button):
        """ Create sub-fen from current FEN removing pieces not marked with circles """

        self.board = self.gamemodel.boards[self.boardview.shown].board
        board = self.board.clone()
        fen = board.asFen()

        for cord in range(64):
            kord = Cord(cord)
            if kord not in self.boardview.circles:
                board.arBoard[cord] = EMPTY

        sub_fen = board.asFen().split()[0]

        # If all pieces removed (no circles at all) use the original FEN
        if sub_fen == "8/8/8/8/8/8/8/8":
            if fen == FEN_START:
                return
            else:
                sub_fen = fen.split()[0]

        self.persp.filter_panel.add_sub_fen(sub_fen)

    def update_gamelist(self):
        if not self.filtered:
            return

        self.board = self.gamemodel.boards[self.boardview.shown].board

        self.persp.gamelist.ply = self.board.plyCount
        self.persp.chessfile.set_fen_filter(self.board.asFen())
        self.persp.gamelist.load_games()
