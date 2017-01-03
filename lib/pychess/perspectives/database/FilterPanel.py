# -*- coding: UTF-8 -*-
from __future__ import print_function

import ast

from gi.repository import Gtk


class FilterPanel:
    def __init__(self, gamelist):
        self.gamelist = gamelist

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.set_row_spacing(3)

        tag_label = Gtk.Label(_("Tag prefix:"))
        tag_entry = Gtk.SearchEntry()
        tag_entry.connect('activate', self.activate_tag_entry)
        tag_entry.connect('search-changed', self.search_tag_changed)

        scout_label = Gtk.Label(_("Scoutfish:"))
        scout_entry = Gtk.SearchEntry()
        scout_entry.connect('activate', self.activate_scout_entry)
        scout_entry.connect('search-changed', self.search_scout_changed)

        grid.add(tag_label)
        grid.attach(tag_entry, 1, 0, 2, 1)
        grid.attach_next_to(scout_label, tag_label, Gtk.PositionType.BOTTOM, 1, 2)
        grid.attach_next_to(scout_entry, scout_label, Gtk.PositionType.RIGHT, 2, 1)

        self.box.pack_start(grid, False, False, 0)
        self.box.show_all()

    def new_tag_filter(self, text):
        self.gamelist.chessfile.set_tags_filter(text)
        self.gamelist.load_games()

    def activate_tag_entry(self, entry):
        text = entry.get_text()
        self.new_tag_filter(text)

    def search_tag_changed(self, entry):
        text = entry.get_text()
        if not text:
            self.new_tag_filter("")

    def new_scout_filter(self, text):
        try:
            if text:
                q = ast.literal_eval(text)
            else:
                q = ""
            self.gamelist.chessfile.set_scout_filter(q)
            self.gamelist.load_games()
        except ValueError:
            print("Malformed scoutfish query (Python dict)")

    def activate_scout_entry(self, entry):
        text = entry.get_text()
        self.new_scout_filter(text)

    def search_scout_changed(self, entry):
        text = entry.get_text()
        if not text:
            self.new_scout_filter("")
