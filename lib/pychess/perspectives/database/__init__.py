from gi.repository import Gtk

from pychess.perspectives import Perspective, perspective_manager
from pychess.Database.gamelist import GameList


class Database(Perspective):
    def __init__(self):
        Perspective.__init__(self, "database", _("Database"))

    def create_toolbuttons(self):
        self.import_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CONVERT)
        self.import_button.set_tooltip_text(_("Import PGN file"))
        self.import_button.connect("clicked", self.on_import_clicked)

        self.close_button = Gtk.ToolButton.new_from_stock(Gtk.STOCK_CLOSE)
        self.close_button.set_tooltip_text(_("Close"))
        self.close_button.connect("clicked", self.close)

    def open_chessfile(self, filename):
        print(filename)
        self.game_list = GameList(filename)
        perspective_manager.set_perspective_widget("database", self.game_list.vbox)

        if filename.endswith(".pdb"):
            perspective_manager.set_perspective_toobuttons("database", [self.import_button, self.close_button])
        else:
            perspective_manager.set_perspective_toobuttons("database", [self.close_button])

        perspective_manager.activate_perspective("database")

    def close(self, widget):
        self.game_list.chessfile.close()
        perspective_manager.disable_perspective("database")

    def on_import_clicked(self, widget):
        print("import")
