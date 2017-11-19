from gi.repository import Gtk, Gdk

from pychess.Utils.const import BLACK, WHITE
from pychess.perspectives import perspective_manager
from pychess.Utils.elo import get_elo_rating_change_str

firstRun = True


def run(widgets):
    persp = perspective_manager.get_perspective("games")
    gamemodel = persp.cur_gmwidg().gamemodel

    widgets["event_entry"].set_text(str(gamemodel.getTag("Event", "")))
    widgets["site_entry"].set_text(str(gamemodel.getTag("Site", "")))
    widgets["round_entry"].set_text(str(gamemodel.getTag("Round", "")))
    widgets["white_entry"].set_text(str(gamemodel.getTag("White", "")))
    widgets["black_entry"].set_text(str(gamemodel.getTag("Black", "")))
    widgets["white_elo_entry"].set_text(str(gamemodel.getTag("WhiteElo", "")))
    widgets["black_elo_entry"].set_text(str(gamemodel.getTag("BlackElo", "")))
    refresh_elo_rating_change(widgets)
    widgets["annotator_entry"].set_text(str(gamemodel.getTag("Annotator", "")))

    # Notice: GtkCalender month goes from 0 to 11, but gamemodel goes from
    # 1 to 12
    widgets["game_info_calendar"].clear_marks()
    widgets["game_info_calendar"].select_month(
        int(gamemodel.tags["Month"]) - 1, int(gamemodel.tags["Year"]))
    widgets["game_info_calendar"].select_day(int(gamemodel.tags["Day"]))

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
        gamemodel.tags["Event"] = widgets["event_entry"].get_text()
        gamemodel.tags["Site"] = widgets["site_entry"].get_text()
        gamemodel.tags["Round"] = widgets["round_entry"].get_text()
        gamemodel.tags["White"] = widgets["white_entry"].get_text()
        gamemodel.tags["Black"] = widgets["black_entry"].get_text()
        gamemodel.tags["WhiteElo"] = widgets["white_elo_entry"].get_text()
        gamemodel.tags["BlackElo"] = widgets["black_elo_entry"].get_text()
        gamemodel.tags["Annotator"] = widgets["annotator_entry"].get_text()
        gamemodel.tags["Year"] = widgets["game_info_calendar"].get_date()[0]
        gamemodel.tags["Month"] = widgets["game_info_calendar"].get_date()[
            1] + 1
        gamemodel.tags["Day"] = widgets["game_info_calendar"].get_date()[2]
        widgets["game_info"].hide()

        gamemodel.players[BLACK].setName(gamemodel.tags["Black"])
        gamemodel.players[WHITE].setName(gamemodel.tags["White"])
        gamemodel.emit("players_changed")
        return True

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
