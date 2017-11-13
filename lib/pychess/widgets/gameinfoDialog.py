from pychess.Utils.const import BLACK, WHITE
from pychess.perspectives import perspective_manager

firstRun = True


def run(widgets):
    persp = perspective_manager.get_perspective("games")
    gamemodel = persp.cur_gmwidg().gamemodel

    def set_field_value(name, tag):
        widgets[name].set_text(str(gamemodel.tags[tag] if tag in gamemodel.tags else ""))

    set_field_value("event_entry", "Event")
    set_field_value("site_entry", "Site")
    set_field_value("round_entry", "Round")
    set_field_value("white_entry", "White")
    set_field_value("black_entry", "Black")
    set_field_value("white_elo_entry", "WhiteElo")
    set_field_value("black_elo_entry", "BlackElo")
    set_field_value("annotator_entry", "Annotator")

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

    widgets["game_info"].connect("delete-event", hide_window)
    widgets["game_info_cancel_button"].connect("clicked", hide_window)
    widgets["game_info_ok_button"].connect("clicked", accept_new_properties)
