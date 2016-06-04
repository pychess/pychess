from __future__ import absolute_import
from . import gamewidget
from pychess.Utils.const import BLACK, WHITE

firstRun = True


def run(widgets):
    gamemodel = gamewidget.cur_gmwidg().gamemodel
    widgets["event_entry"].set_text(gamemodel.tags["Event"])
    widgets["site_entry"].set_text(gamemodel.tags["Site"])
    widgets["round_spinbutton"].set_value(float(gamemodel.tags["Round"]))
    widgets["white_entry"].set_text(gamemodel.tags["White"])
    widgets["black_entry"].set_text(gamemodel.tags["Black"])

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
        gamemodel = gamewidget.cur_gmwidg().gamemodel
        gamemodel.tags["Event"] = widgets["event_entry"].get_text()
        gamemodel.tags["Site"] = widgets["site_entry"].get_text()
        gamemodel.tags["Round"] = int(widgets["round_spinbutton"].get_value())
        gamemodel.tags["White"] = widgets["white_entry"].get_text()
        gamemodel.tags["Black"] = widgets["black_entry"].get_text()
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
