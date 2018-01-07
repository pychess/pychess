from urllib.request import urlopen
from urllib.parse import unquote

from gi.repository import Gtk

from pychess.perspectives import perspective_manager


class RecentChooserMenu(Gtk.RecentChooserMenu):
    def __init__(self):
        Gtk.RecentChooserMenu.__init__(self)

        def recent_item_activated(self):
            uri = self.get_current_uri()
            try:
                urlopen(unquote(uri)).close()
                perspective = perspective_manager.get_perspective("database")
                perspective.open_chessfile(self.get_current_uri())
            except (IOError, OSError):
                # shomething wrong whit the uri
                recent_manager.remove_item(uri)

        self.set_show_tips(True)
        self.set_sort_type(Gtk.RecentSortType.MRU)
        self.set_limit(10)
        self.set_name("recent_menu")

        file_filter = Gtk.RecentFilter()
        file_filter.add_mime_type("application/x-chess-pgn")
        file_filter.add_mime_type("application/x-chess-epd")
        file_filter.add_mime_type("application/x-chess-fen")
        file_filter.add_pattern("*.pgn")
        file_filter.add_pattern("*.epd")
        file_filter.add_pattern("*.fen")
        self.set_filter(file_filter)

        self.connect("item-activated", recent_item_activated)


recent_manager = Gtk.RecentManager.get_default()
recent_menu = RecentChooserMenu()
