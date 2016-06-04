from __future__ import absolute_import
import time
import threading

from gi.repository import Gtk

from . import gamewidget
from pychess.Utils.const import HINT, SPY, BLACK, WHITE
from pychess.System import conf, fident
from pychess.System import uistuff
from pychess.System.idle_add import idle_add
from pychess.System.Log import log
from pychess.Utils import prettyPrintScore
from pychess.Utils.Move import listToMoves
from pychess.Utils.lutils.lmove import ParsingError
from pychess.Players.engineNest import discoverer
from pychess.widgets.preferencesDialog import anal_combo_get_value, anal_combo_set_value
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarMessageButton
from pychess.widgets import InfoBar

widgets = uistuff.GladeWidgets("analyze_game.glade")
stop_event = threading.Event()

firstRun = True


def run():
    global firstRun
    if firstRun:
        initialize()
        firstRun = False
    stop_event.clear()
    widgets["analyze_game"].show()
    widgets["analyze_game"].present()


def initialize():

    uistuff.keep(widgets["fromCurrent"], "fromCurrent", first_value=True)
    uistuff.keep(widgets["shouldBlack"], "shouldBlack", first_value=True)
    uistuff.keep(widgets["shouldWhite"], "shouldWhite", first_value=True)
    uistuff.keep(widgets["threatPV"], "threatPV")
    uistuff.keep(widgets["showEval"], "showEval")
    uistuff.keep(widgets["showBlunder"], "showBlunder", first_value=True)
    uistuff.keep(widgets["max_analysis_spin"], "max_analysis_spin", first_value=3)
    uistuff.keep(widgets["variation_threshold_spin"], "variation_threshold_spin", first_value=50)

    # Analyzing engines
    uistuff.createCombo(widgets["ana_combobox"], name="ana_combobox")

    from pychess.widgets import newGameDialog

    @idle_add
    def update_analyzers_store(discoverer):
        data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
        uistuff.updateCombo(widgets["ana_combobox"], data)
    discoverer.connect_after("all_engines_discovered", update_analyzers_store)
    update_analyzers_store(discoverer)

    uistuff.keep(widgets["ana_combobox"], "ana_combobox", anal_combo_get_value,
                 lambda combobox, value: anal_combo_set_value(combobox, value, "hint_mode",
                                                              "analyzer_check", HINT))

    def hide_window(button, *args):
        widgets["analyze_game"].hide()
        return True

    def abort():
        stop_event.set()
        widgets["analyze_game"].hide()

    def run_analyze(button, *args):
        gmwidg = gamewidget.cur_gmwidg()
        gamemodel = gmwidg.gamemodel

        old_check_value = conf.get("analyzer_check", True)
        conf.set("analyzer_check", True)
        if HINT not in gamemodel.spectators:
            gamemodel.start_analyzer(HINT)
        analyzer = gamemodel.spectators[HINT]
        gmwidg.menuitems["hint_mode"].active = True
        threat_PV = conf.get("ThreatPV", False)
        if threat_PV:
            old_inv_check_value = conf.get("inv_analyzer_check", True)
            conf.set("inv_analyzer_check", True)
            if SPY not in gamemodel.spectators:
                gamemodel.start_analyzer(SPY)
            inv_analyzer = gamemodel.spectators[SPY]
            gmwidg.menuitems["spy_mode"].active = True

        title = _("Game analyzing in progress...")
        text = _("Do you want to abort it?")
        content = InfoBar.get_message_content(title, text, Gtk.STOCK_DIALOG_QUESTION)

        def response_cb(infobar, response, message):
            conf.set("analyzer_check", old_check_value)
            if threat_PV:
                conf.set("inv_analyzer_check", old_inv_check_value)
            message.dismiss()
            abort()
        message = InfoBarMessage(Gtk.MessageType.QUESTION, content, response_cb)
        message.add_button(InfoBarMessageButton(_("Abort"), Gtk.ResponseType.CANCEL))
        gmwidg.replaceMessages(message)

        def analyse_moves():
            should_black = conf.get("shouldBlack", True)
            should_white = conf.get("shouldWhite", True)
            from_current = conf.get("fromCurrent", True)
            start_ply = gmwidg.board.view.shown if from_current else 0
            move_time = int(conf.get("max_analysis_spin", 3))
            threshold = int(conf.get("variation_threshold_spin", 50))
            for board in gamemodel.boards[start_ply:]:
                if stop_event.is_set():
                    break

                @idle_add
                def do():
                    gmwidg.board.view.setShownBoard(board)
                do()
                analyzer.setBoard(board)
                if threat_PV:
                    inv_analyzer.setBoard(board)
                time.sleep(move_time + 0.1)

                ply = board.ply
                color = (ply - 1) % 2
                if ply - 1 in gamemodel.scores and ply in gamemodel.scores and (
                        (color == BLACK and should_black) or (color == WHITE and should_white)):
                    oldmoves, oldscore, olddepth = gamemodel.scores[ply - 1]
                    oldscore = oldscore * -1 if color == BLACK else oldscore
                    score_str = prettyPrintScore(oldscore, olddepth)
                    moves, score, depth = gamemodel.scores[ply]
                    score = score * -1 if color == WHITE else score
                    diff = score - oldscore
                    if (diff > threshold and color == BLACK) or (diff < -1 * threshold and color == WHITE):
                        if threat_PV:
                            try:
                                if ply - 1 in gamemodel.spy_scores:
                                    oldmoves0, oldscore0, olddepth0 = gamemodel.spy_scores[ply - 1]
                                    score_str0 = prettyPrintScore(oldscore0, olddepth0)
                                    pv0 = listToMoves(gamemodel.boards[ply - 1], ["--"] + oldmoves0, validate=True)
                                    if len(pv0) > 2:
                                        gamemodel.add_variation(gamemodel.boards[ply - 1], pv0,
                                                                comment="Treatening", score=score_str0)
                            except ParsingError as e:
                                # ParsingErrors may happen when parsing "old" lines from
                                # analyzing engines, which haven't yet noticed their new tasks
                                log.debug("__parseLine: Ignored (%s) from analyzer: ParsingError%s" %
                                          (' '.join(oldmoves), e))
                        try:
                            pv = listToMoves(gamemodel.boards[ply - 1], oldmoves, validate=True)
                            gamemodel.add_variation(gamemodel.boards[ply - 1], pv, comment="Better is", score=score_str)
                        except ParsingError as e:
                            # ParsingErrors may happen when parsing "old" lines from
                            # analyzing engines, which haven't yet noticed their new tasks
                            log.debug("__parseLine: Ignored (%s) from analyzer: ParsingError%s" %
                                      (' '.join(oldmoves), e))

            widgets["analyze_game"].hide()
            widgets["analyze_ok_button"].set_sensitive(True)
            conf.set("analyzer_check", old_check_value)
            if threat_PV:
                conf.set("inv_analyzer_check", old_inv_check_value)
            message.dismiss()

        t = threading.Thread(target=analyse_moves, name=fident(analyse_moves))
        t.daemon = True
        t.start()
        hide_window(None)

        return True

    widgets["analyze_game"].connect("delete-event", hide_window)
    widgets["analyze_cancel_button"].connect("clicked", hide_window)
    widgets["analyze_ok_button"].connect("clicked", run_analyze)
