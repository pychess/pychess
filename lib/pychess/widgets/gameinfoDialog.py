import re

from gi.repository import Gtk, Gdk, GObject

from pychess.Utils.const import BLACK, WHITE
from pychess.perspectives import perspective_manager
from pychess.Utils.elo import get_elo_rating_change_str

firstRun = True


def run(widgets):
    persp = perspective_manager.get_perspective("games")
    gamemodel = persp.cur_gmwidg().gamemodel

    widgets["site_entry"].set_text(str(gamemodel.getTag("Site", "")))
    widgets["event_entry"].set_text(str(gamemodel.getTag("Event", "")))
    widgets["date_entry"].set_text(str(gamemodel.getTag("Date", "")))
    widgets["round_entry"].set_text(str(gamemodel.getTag("Round", "")))
    widgets["annotator_entry"].set_text(str(gamemodel.getTag("Annotator", "")))
    widgets["white_entry"].set_text(str(gamemodel.getTag("White", "")))
    widgets["black_entry"].set_text(str(gamemodel.getTag("Black", "")))
    widgets["white_elo_entry"].set_text(str(gamemodel.getTag("WhiteElo", "")))
    widgets["black_elo_entry"].set_text(str(gamemodel.getTag("BlackElo", "")))
    refresh_elo_rating_change(widgets)

    global firstRun
    if firstRun:
        initialize(widgets)
        firstRun = False
    widgets["game_info"].show()


def initialize(widgets):
    def hide_window(button, *args):
        widgets["game_info"].hide()
        return True

    def accept_new_properties(button, *args):
        persp = perspective_manager.get_perspective("games")
        gamemodel = persp.cur_gmwidg().gamemodel

        gamemodel.tags["Site"] = widgets["site_entry"].get_text()
        gamemodel.tags["Event"] = widgets["event_entry"].get_text()
        gamemodel.tags["Date"] = widgets["date_entry"].get_text()
        match = re.match("^([0-9\?]{4})\.([0-9\?]{2})\.([0-9\?]{2})$", gamemodel.tags["Date"])
        if match is not None:
            gamemodel.tags["Year"], gamemodel.tags["Month"], gamemodel.tags["Day"] = match.groups()
        else:
            gamemodel.tags["Year"], gamemodel.tags["Month"], gamemodel.tags["Day"] = "0", "0", "0"
        for tag in ["Year", "Month", "Day"]:
            try:
                gamemodel.tags[tag] = int(gamemodel.tags[tag])
            except ValueError:
                gamemodel.tags[tag] = 0
        gamemodel.tags["Round"] = widgets["round_entry"].get_text()
        gamemodel.tags["Annotator"] = widgets["annotator_entry"].get_text()
        gamemodel.tags["White"] = widgets["white_entry"].get_text()
        gamemodel.tags["Black"] = widgets["black_entry"].get_text()
        gamemodel.tags["WhiteElo"] = widgets["white_elo_entry"].get_text()
        gamemodel.tags["BlackElo"] = widgets["black_elo_entry"].get_text()

        widgets["game_info"].hide()

        gamemodel.players[BLACK].setName(gamemodel.tags["Black"])
        gamemodel.players[WHITE].setName(gamemodel.tags["White"])
        gamemodel.emit("players_changed")
        return True

    tags_store = Gtk.ListStore(str, GObject.TYPE_PYOBJECT)
    tagstv = widgets["tags_treeview"]
    tagstv.set_model(tags_store)
    tagstv.append_column(Gtk.TreeViewColumn("Tag", Gtk.CellRendererText()))
    tagstv.append_column(Gtk.TreeViewColumn("Value", Gtk.CellRendererText()))

    widgets["white_elo_entry"].connect("changed", lambda p: refresh_elo_rating_change(widgets))
    widgets["black_elo_entry"].connect("changed", lambda p: refresh_elo_rating_change(widgets))

    widgets["game_info"].connect("delete-event", hide_window)
    widgets["game_info_cancel_button"].connect("clicked", hide_window)
    widgets["game_info_ok_button"].connect("clicked", accept_new_properties)


red = Gdk.RGBA(.643, 0, 0, 1)
green = Gdk.RGBA(.306, .604, .024, 1)
black = Gdk.RGBA(0.0, 0.0, 0.0, 1.0)


def refresh_elo_rating_change(widgets):
    persp = perspective_manager.get_perspective("games")
    gamemodel = persp.cur_gmwidg().gamemodel

    site = gamemodel.tags["Site"]
    if "lichess.org" in site or "chessclub.com" in site or "freechess.org" in site:
        # TODO : lichess takes 3 parameters per player
        widgets["w_elo_change"].set_text("")
        widgets["b_elo_change"].set_text("")
        return

    welo = widgets["white_elo_entry"].get_text()
    belo = widgets["black_elo_entry"].get_text()

    wchange = get_elo_rating_change_str(gamemodel, WHITE, welo, belo)
    widgets["w_elo_change"].set_text(wchange)
    if wchange.startswith("+") or wchange.startswith("-"):
        widgets["w_elo_change"].override_color(Gtk.StateFlags.NORMAL, red if wchange.startswith("-") else green)
    else:
        widgets["w_elo_change"].override_color(Gtk.StateFlags.NORMAL, black)

    bchange = get_elo_rating_change_str(gamemodel, BLACK, welo, belo)
    widgets["b_elo_change"].set_text(bchange)
    if bchange.startswith("+") or bchange.startswith("-"):
        widgets["b_elo_change"].override_color(Gtk.StateFlags.NORMAL, red if bchange.startswith("-") else green)
    else:
        widgets["b_elo_change"].override_color(Gtk.StateFlags.NORMAL, black)
