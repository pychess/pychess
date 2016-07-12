# -*- coding: UTF-8 -*-
from __future__ import print_function

from gi.repository import Gtk


class FilterPanel:
    def __init__(self, gamelist):
        self.gamelist = gamelist

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.playerlist = Gtk.ListStore(str)

        self.match = set()
        completion = Gtk.EntryCompletion()
        completion.set_model(self.playerlist)
        completion.set_text_column(0)

        for player in self.gamelist.chessfile.players:
            self.playerlist.append(player)

        entry = Gtk.Entry()
        entry.set_completion(completion)
        entry.connect('activate', self.activate_entry)

        self.box.pack_start(entry, False, False, 0)
        self.box.show_all()

    def activate_entry(self, entry):
        text = entry.get_text()
        self.gamelist.chessfile.build_where(text)
        self.offset = 0
        self.gamelist.chessfile.build_query()
        self.gamelist.load_games()
