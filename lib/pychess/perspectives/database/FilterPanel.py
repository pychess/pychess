# -*- coding: UTF-8 -*-
from __future__ import print_function

import ast

from gi.repository import Gtk

from pychess.System import uistuff


class FilterPanel:
    def __init__(self, gamelist):
        self.gamelist = gamelist

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.set_column_spacing(3)

        tag_label = Gtk.Label(_("Header data:"))
        self.tag_entry = Gtk.SearchEntry()
        self.tag_entry.connect('activate', self.activate_tag_entry)
        self.tag_entry.connect('search-changed', self.search_tag_changed)
        tag_button = Gtk.Button()
        ico = Gtk.Image.new_from_icon_name("gtk-properties", Gtk.IconSize.BUTTON)
        tag_button.set_image(ico)
        tag_button.connect("clicked", self.on_tag_clicked)
        tag_box = Gtk.Box()
        tag_box.pack_start(tag_button, False, False, 0)

        scout_label = Gtk.Label(_("Game data:"))
        self.scout_entry = Gtk.SearchEntry()
        self.scout_entry.connect('activate', self.activate_scout_entry)
        self.scout_entry.connect('search-changed', self.search_scout_changed)
        scout_button = Gtk.Button()
        ico = Gtk.Image.new_from_icon_name("gtk-properties", Gtk.IconSize.BUTTON)
        scout_button.set_image(ico)
        scout_button.connect("clicked", self.on_scout_clicked)
        scout_box = Gtk.Box()
        scout_box.pack_start(scout_button, False, False, 0)

        grid.attach(tag_label, 0, 0, 2, 1)
        grid.attach(self.tag_entry, 2, 0, 5, 1)
        grid.attach(tag_box, 7, 0, 1, 1)
        grid.attach_next_to(scout_label, tag_label, Gtk.PositionType.BOTTOM, 2, 1)
        grid.attach_next_to(self.scout_entry, scout_label, Gtk.PositionType.RIGHT, 5, 1)
        # grid.attach_next_to(scout_box, self.scout_entry, Gtk.PositionType.RIGHT, 1, 1)

        self.box.pack_start(grid, False, False, 0)
        self.box.show_all()

    def on_tag_clicked(self, button):
        widgets = uistuff.GladeWidgets("PyChess.glade")
        dialog = widgets["tag_filter_dialog"]

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            query = {}
            if widgets["white"].get_text():
                query["white"] = widgets["white"].get_text()
            if widgets["black"].get_text():
                query["black"] = widgets["black"].get_text()
            if widgets["ignore_colors"].get_active():
                query["ignore_colors"] = True

            if widgets["event"].get_text():
                query["event"] = widgets["event"].get_text()
            if widgets["site"].get_text():
                query["site"] = widgets["site"].get_text()

            if widgets["eco_from"].get_text():
                query["eco_from"] = widgets["eco_from"].get_text()
            if widgets["eco_to"].get_text():
                query["eco_to"] = widgets["eco_to"].get_text()

            if widgets["elo_from"].get_value_as_int():
                query["elo_from"] = widgets["elo_from"].get_value_as_int()
            if widgets["elo_to"].get_value_as_int():
                query["elo_to"] = widgets["elo_to"].get_value_as_int()

            if widgets["year_from"].get_value_as_int():
                query["year_from"] = widgets["year_from"].get_value_as_int()
            if widgets["year_to"].get_value_as_int():
                query["year_to"] = widgets["year_to"].get_value_as_int()

            if widgets["result_1_0"].get_active():
                query["result"] = "1-0"
            elif widgets["result_0_1"].get_active():
                query["result"] = "0-1"
            elif widgets["result_1_2"].get_active():
                query["result"] = "1/2-1/2"

            if widgets["annotator"].get_text():
                query["annotator"] = widgets["annotator"].get_text()

            self.tag_entry.set_text("%s" % query)

        elif response == Gtk.ResponseType.CANCEL:
            pass

        dialog.destroy()

    def on_scout_clicked(self, button):
        print("s CLICKED")

    def new_tag_filter(self, text):
        try:
            if text:
                q = ast.literal_eval(text)
            else:
                q = None
            self.gamelist.chessfile.set_tag_filter(q)
            self.gamelist.load_games()
        except (ValueError, SyntaxError):
            print("Malformed tag query (Python dict)")

    def activate_tag_entry(self, entry):
        text = entry.get_text()
        self.new_tag_filter(text)

    def search_tag_changed(self, entry):
        text = entry.get_text()
        if not text:
            self.new_tag_filter(None)

    def new_scout_filter(self, text):
        try:
            if text:
                q = ast.literal_eval(text)
            else:
                q = None
            self.gamelist.chessfile.set_scout_filter(q)
            self.gamelist.load_games()
        except (ValueError, SyntaxError):
            print("Malformed scoutfish query (Python dict)")

    def activate_scout_entry(self, entry):
        text = entry.get_text()
        self.new_scout_filter(text)

    def search_scout_changed(self, entry):
        text = entry.get_text()
        if not text:
            self.new_scout_filter(None)
