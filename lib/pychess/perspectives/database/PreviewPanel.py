# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk

from pychess.Utils.const import FEN_EMPTY
from pychess.Utils.Board import Board
from pychess.Utils.IconLoader import load_icon
from pychess.widgets.BoardView import BoardView
from pychess.Savers.ChessFile import LoadingError


def createImage(pixbuf):
    image = Gtk.Image()
    image.set_from_pixbuf(pixbuf)
    return image

media_previous = load_icon(16, "gtk-media-previous-ltr", "media-skip-backward")
media_rewind = load_icon(16, "gtk-media-rewind-ltr", "media-seek-backward")
media_forward = load_icon(16, "gtk-media-forward-ltr", "media-seek-forward")
media_next = load_icon(16, "gtk-media-next-ltr", "media-skip-forward")


class PreviewPanel:
    def __init__(self, gamelist):
        self.gamelist = gamelist

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        selection = self.gamelist.get_selection()
        self.conid = selection.connect_after('changed', self.on_selection_changed)
        self.gamelist.preview_cid = self.conid

        startbut = Gtk.Button()
        startbut.add(createImage(media_previous))

        backbut = Gtk.Button()
        backbut.add(createImage(media_rewind))

        forwbut = Gtk.Button()
        forwbut.add(createImage(media_forward))

        endbut = Gtk.Button()
        endbut.add(createImage(media_next))

        button_hbox = Gtk.Box()

        button_hbox.pack_start(startbut, True, True, 0)
        button_hbox.pack_start(backbut, True, True, 0)
        button_hbox.pack_start(forwbut, True, True, 0)
        button_hbox.pack_start(endbut, True, True, 0)

        startbut.connect("clicked", self.on_start_button)
        backbut.connect("clicked", self.on_back_button)
        forwbut.connect("clicked", self.on_forward_button)
        endbut.connect("clicked", self.on_end_button)

        # Add the board
        self.boardview = BoardView(preview=True)
        self.boardview.set_size_request(170, 170)

        self.gamemodel = self.boardview.model
        self.boardview.got_started = True
        self.boardview.auto_update_shown = False

        self.box.pack_start(self.boardview, True, True, 0)
        self.box.pack_start(button_hbox, False, False, 0)
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
        indices = path.get_indices()
        sel = indices[0]

        self.boardview.animation_lock.acquire()
        try:
            try:
                self.gamelist.chessfile.loadToModel(sel, -1, self.gamemodel)
            except LoadingError as err:
                dialogue = Gtk.MessageDialog(type=Gtk.MessageType.WARNING,
                                             buttons=Gtk.ButtonsType.OK,
                                             message_format=err.args[0])
                dialogue.format_secondary_text(err.args[1])
                dialogue.connect("response", lambda dialogue, a: dialogue.hide())
                dialogue.show()

            self.boardview.lastMove = None
            self.boardview._shown = self.gamemodel.lowply
            last = self.gamemodel.ply
        finally:
            self.boardview.animation_lock.release()

        self.boardview.redrawCanvas()
        self.boardview.shown = self.gamelist.ply

    def on_start_button(self, button):
        self.boardview.showFirst()

    def on_back_button(self, button):
        self.boardview.showPrev()

    def on_forward_button(self, button):
        self.boardview.showNext()

    def on_end_button(self, button):
        self.boardview.showLast()
