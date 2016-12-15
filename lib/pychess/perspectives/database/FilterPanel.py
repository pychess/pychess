# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk


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
