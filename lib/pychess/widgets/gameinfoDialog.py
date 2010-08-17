import gamewidget

firstRun = True
def run(widgets, gameDic):
    global firstRun
    if firstRun:
        initialize(widgets, gameDic)
        firstRun = False
    widgets["game_info"].show()

def initialize(widgets, gameDic):
    gamemodel = gameDic[gamewidget.cur_gmwidg()]
    widgets["event_entry"].set_text(gamemodel.tags["Event"])
    widgets["site_entry"].set_text(gamemodel.tags["Site"])
    widgets["round_spinbutton"].set_value(float(gamemodel.tags["Round"]))
    
    # Notice: GtkCalender month goes from 0 to 11, but gamemodel goes from
    # 1 to 12
    widgets["game_info_calendar"].clear_marks()
    widgets["game_info_calendar"].select_month(
            gamemodel.tags["Month"]-1, gamemodel.tags["Year"])
    widgets["game_info_calendar"].select_day(gamemodel.tags["Day"])
    
    def hide_window(button, *args):
        widgets["game_info"].hide()
        return True
    
    def accept_new_properties(button, *args):
        gamemodel = gameDic[gamewidget.cur_gmwidg()]
        gamemodel.tags["Event"] = widgets["event_entry"].get_text()
        gamemodel.tags["Site"] = widgets["site_entry"].get_text()
        gamemodel.tags["Round"] = int(widgets["round_spinbutton"].get_value())
        x= gamemodel.tags["Round"]
        print x, type(x)
        gamemodel.tags["Year"] = widgets["game_info_calendar"].get_date()[0]
        gamemodel.tags["Month"] = widgets["game_info_calendar"].get_date()[1] + 1
        gamemodel.tags["Day"] = widgets["game_info_calendar"].get_date()[2]
        widgets["game_info"].hide()
        return True
    
    widgets["game_info"].connect("delete-event", hide_window)
    widgets["game_info_cancel_button"].connect("clicked", hide_window)
    widgets["game_info_ok_button"].connect("clicked", accept_new_properties)
