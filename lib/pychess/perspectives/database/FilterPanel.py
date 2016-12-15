# -*- coding: UTF-8 -*-
from __future__ import print_function

import re

from gi.repository import Gtk

SUB_FEN_REGEX = re.compile(r'\"sub-fen\": \"(.*)\"')
# "sub-fen": "1nbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R"


class FilterPanel:
    def __init__(self, gamelist):
        self.gamelist = gamelist

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        entry = Gtk.SearchEntry()
        entry.connect('activate', self.activate_entry)
        entry.connect('search-changed', self.search_changed)

        self.box.pack_start(entry, False, False, 0)
        self.box.show_all()

    def new_filter(self, text):
        if text.find('"sub-fen"') >= 0:
            sub_fen_match = SUB_FEN_REGEX.search(text)
            if sub_fen_match:
                sub_fen = sub_fen_match.group(1)
                self.gamelist.chessfile.build_where_bitboards(1, 0, fen=sub_fen)
        else:
            self.gamelist.chessfile.build_where_tags(text)
        self.gamelist.offset = 0
        self.gamelist.chessfile.build_query()
        self.gamelist.load_games()
        self.gamelist.update_counter(with_select=True)

    def activate_entry(self, entry):
        text = entry.get_text()
        self.new_filter(text)

    def search_changed(self, entry):
        text = entry.get_text()
        if not text:
            self.new_filter("")
