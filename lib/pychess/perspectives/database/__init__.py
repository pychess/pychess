from gi.repository import Gtk

from pychess.perspectives import Perspective, perspective_manager
from pychess.Database.gamelist import GameList


class Database(Perspective):
    def __init__(self):
        Perspective.__init__(self, "database", _("Database"))

    def create_toolbuttons(self):
        import_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CONVERT)
        import_button.set_tooltip_text(_("Import PGN file"))
        import_button.connect("clicked", self.on_import_clicked)
        perspective_manager.set_perspective_toobuttons("database", [import_button, ])

    def open_chessfile(self, filename):
        print(filename)
        self.game_list = GameList(filename)
        perspective_manager.set_perspective_widget("database", self.game_list.vbox)
        perspective_manager.activate_perspective("database")

    def close(self):
        self.game_list.chessfile.close()
        perspective_manager.disable_perspective("database")
        if perspective_manager.get_perspective("games").sensitive:
            perspective_manager.activate_perspective("games")
        elif perspective_manager.get_perspective("fics").sensitive:
            perspective_manager.activate_perspective("fics")
        else:
            perspective_manager.activate_perspective("welcome")

    def on_import_clicked(self, widget):
        print("import")
