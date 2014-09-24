import time
import threading

import gamewidget
from pychess.Utils.const import *
from pychess.System import conf, fident
from pychess.System import glock
from pychess.System import uistuff
from pychess.System.glock import glock_connect_after
from pychess.Players.engineNest import discoverer
from pychess.widgets.preferencesDialog import anal_combo_get_value, anal_combo_set_value

widgets = uistuff.GladeWidgets("analyze_game.glade")
stop_event = threading.Event()

firstRun = True
def run(gameDic):
    global firstRun
    if firstRun:
        initialize(gameDic)
        firstRun = False
    stop_event.clear()
    widgets["analyze_game"].show()
    widgets["analyze_game"].present()

def initialize(gameDic):
    
    uistuff.keep(widgets["showEval"], "showEval")
    uistuff.keep(widgets["showBlunder"], "showBlunder", first_value=True)
    uistuff.keep(widgets["max_analysis_spin"], "max_analysis_spin", first_value=3)
    uistuff.keep(widgets["variation_thresold_spin"], "variation_thresold_spin", first_value=50)

    # Analyzing engines
    uistuff.createCombo(widgets["ana_combobox"])

    from pychess.widgets import newGameDialog
    def update_analyzers_store(discoverer):
        data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
        uistuff.updateCombo(widgets["ana_combobox"], data)
    glock_connect_after(discoverer, "all_engines_discovered",
                        update_analyzers_store)
    update_analyzers_store(discoverer)

    uistuff.keep(widgets["ana_combobox"], "ana_combobox", anal_combo_get_value,
        lambda combobox, value: anal_combo_set_value(combobox, value, "hint_mode",
                                              "analyzer_check", HINT))
 
    def hide_window(button, *args):
        stop_event.set()
        widgets["analyze_game"].hide()
        widgets["analyze_ok_button"].set_sensitive(True)
        return True
    
    def run_analyze(button, *args):
        old_check_value = conf.get("analyzer_check", True)
        conf.set("analyzer_check", True)
        widgets["analyze_ok_button"].set_sensitive(False)
        gmwidg = gamewidget.cur_gmwidg()
        gamemodel = gameDic[gmwidg]
        analyzer = gamemodel.spectators[HINT]

        def analyse_moves():
            move_time = int(conf.get("max_analysis_spin", 3))
            thresold = int(conf.get("variation_thresold_spin", 50))
            for board in gamemodel.boards:
                if stop_event.is_set():
                    break
                glock.acquire()
                try:
                    gmwidg.board.view.setShownBoard(board)
                finally:
                    glock.release()
                analyzer.setBoard(board)
                time.sleep(move_time+0.1)

                ply = board.ply
                if ply-1 in gamemodel.scores: 
                    color = (ply-1) % 2
                    oldmoves, oldscore, olddepth = gamemodel.scores[ply-1]
                    oldscore = oldscore * -1 if color == BLACK else oldscore
                    moves, score, depth = gamemodel.scores[ply]
                    score = score * -1 if color == WHITE else score
                    diff = score-oldscore
                    if (diff > thresold and color==BLACK) or (diff < -1*thresold and color==WHITE):
                        gamemodel.add_variation(gamemodel.boards[ply-1], oldmoves)
            
            widgets["analyze_game"].hide()
            widgets["analyze_ok_button"].set_sensitive(True)
            conf.set("analyzer_check", old_check_value)
                        
        t = threading.Thread(target=analyse_moves, name=fident(analyse_moves))
        t.daemon = True
        t.start()
        return True
    
    widgets["analyze_game"].connect("delete-event", hide_window)
    widgets["analyze_cancel_button"].connect("clicked", hide_window)
    widgets["analyze_ok_button"].connect("clicked", run_analyze)
