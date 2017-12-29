import asyncio

from gi.repository import Gtk

from pychess.Utils.const import HINT, SPY, BLACK, WHITE
from pychess.System import conf
from pychess.System import uistuff
from pychess.System.Log import log
from pychess.Utils import prettyPrintScore
from pychess.Utils.Move import listToMoves, parseAny
from pychess.Utils.lutils.lmove import ParsingError
from pychess.Players.engineNest import discoverer
from pychess.widgets.preferencesDialog import anal_combo_get_value, anal_combo_set_value
from pychess.widgets.InfoBar import InfoBarMessage, InfoBarMessageButton
from pychess.widgets import mainwindow
from pychess.widgets import InfoBar
from pychess.perspectives import perspective_manager


class AnalyzeGameDialog():
    def __init__(self):
        self.widgets = uistuff.GladeWidgets("analyze_game.glade")
        self.widgets["analyze_game"].set_transient_for(mainwindow())
        self.stop_event = asyncio.Event()

        uistuff.keep(self.widgets["fromCurrent"], "fromCurrent", first_value=True)
        uistuff.keep(self.widgets["shouldBlack"], "shouldBlack", first_value=True)
        uistuff.keep(self.widgets["shouldWhite"], "shouldWhite", first_value=True)
        uistuff.keep(self.widgets["threatPV"], "threatPV")
        uistuff.keep(self.widgets["showEval"], "showEval")
        uistuff.keep(self.widgets["showBlunder"], "showBlunder", first_value=True)
        uistuff.keep(self.widgets["max_analysis_spin"], "max_analysis_spin", first_value=3)
        uistuff.keep(self.widgets["variation_threshold_spin"], "variation_threshold_spin", first_value=50)

        # Analyzing engines
        uistuff.createCombo(self.widgets["ana_combobox"], name="ana_combobox")

        from pychess.widgets import newGameDialog

        def update_analyzers_store(discoverer):
            data = [(item[0], item[1]) for item in newGameDialog.analyzerItems]
            uistuff.updateCombo(self.widgets["ana_combobox"], data)
        discoverer.connect_after("all_engines_discovered", update_analyzers_store)
        update_analyzers_store(discoverer)

        uistuff.keep(self.widgets["ana_combobox"], "ana_combobox", anal_combo_get_value,
                     lambda combobox, value: anal_combo_set_value(combobox, value, "hint_mode",
                                                                  "analyzer_check", HINT))

        def hide_window(button, *args):
            self.widgets["analyze_game"].destroy()

        def abort():
            self.stop_event.set()
            self.widgets["analyze_game"].destroy()

        def run_analyze(button, *args):
            persp = perspective_manager.get_perspective("games")
            gmwidg = persp.cur_gmwidg()
            gamemodel = gmwidg.gamemodel

            old_check_value = conf.get("analyzer_check", True)
            conf.set("analyzer_check", True)
            if HINT not in gamemodel.spectators:
                asyncio.async(gamemodel.start_analyzer(HINT))
            analyzer = gamemodel.spectators[HINT]
            gmwidg.menuitems["hint_mode"].active = True
            threat_PV = conf.get("ThreatPV", False)
            if threat_PV:
                old_inv_check_value = conf.get("inv_analyzer_check", False)
                conf.set("inv_analyzer_check", True)
                if SPY not in gamemodel.spectators:
                    asyncio.async(gamemodel.start_analyzer(SPY))
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

            @asyncio.coroutine
            def analyse_moves():
                should_black = conf.get("shouldBlack", True)
                should_white = conf.get("shouldWhite", True)
                from_current = conf.get("fromCurrent", True)
                start_ply = gmwidg.board.view.shown if from_current else 0
                move_time = int(conf.get("max_analysis_spin", 3))
                threshold = int(conf.get("variation_threshold_spin", 50))
                for board in gamemodel.boards[start_ply:]:
                    if self.stop_event.is_set():
                        break

                    gmwidg.board.view.setShownBoard(board)
                    analyzer.setBoard(board)
                    if threat_PV:
                        inv_analyzer.setBoard(board)
                    yield from asyncio.sleep(move_time + 0.1)

                    ply = board.ply
                    color = (ply - 1) % 2
                    if ply - 1 in gamemodel.scores and ply in gamemodel.scores and (
                            (color == BLACK and should_black) or (color == WHITE and should_white)):
                        oldmoves, oldscore, olddepth = gamemodel.scores[ply - 1]
                        oldscore = oldscore * -1 if color == BLACK else oldscore
                        score_str = prettyPrintScore(oldscore, olddepth, False)
                        moves, score, depth = gamemodel.scores[ply]
                        score = score * -1 if color == WHITE else score
                        diff = score - oldscore
                        if ((diff > threshold and color == BLACK) or (diff < -1 * threshold and color == WHITE)) and (
                           gamemodel.moves[ply - 1] != parseAny(gamemodel.boards[ply - 1], oldmoves[0])):
                            if threat_PV:
                                try:
                                    if ply - 1 in gamemodel.spy_scores:
                                        oldmoves0, oldscore0, olddepth0 = gamemodel.spy_scores[ply - 1]
                                        score_str0 = prettyPrintScore(oldscore0, olddepth0, False)
                                        pv0 = listToMoves(gamemodel.boards[ply - 1], ["--"] + oldmoves0, validate=True)
                                        if len(pv0) > 2:
                                            gamemodel.add_variation(gamemodel.boards[ply - 1], pv0,
                                                                    comment="Threatening", score=score_str0, emit=False)
                                except ParsingError as e:
                                    # ParsingErrors may happen when parsing "old" lines from
                                    # analyzing engines, which haven't yet noticed their new tasks
                                    log.debug("__parseLine: Ignored (%s) from analyzer: ParsingError%s" %
                                              (' '.join(oldmoves), e))
                            try:
                                pv = listToMoves(gamemodel.boards[ply - 1], oldmoves, validate=True)
                                gamemodel.add_variation(gamemodel.boards[ply - 1], pv,
                                                        comment="Better is", score=score_str, emit=False)
                            except ParsingError as e:
                                # ParsingErrors may happen when parsing "old" lines from
                                # analyzing engines, which haven't yet noticed their new tasks
                                log.debug("__parseLine: Ignored (%s) from analyzer: ParsingError%s" %
                                          (' '.join(oldmoves), e))

                self.widgets["analyze_game"].hide()
                self.widgets["analyze_ok_button"].set_sensitive(True)
                conf.set("analyzer_check", old_check_value)
                if threat_PV:
                    conf.set("inv_analyzer_check", old_inv_check_value)
                message.dismiss()

                gamemodel.emit("analysis_finished")

            asyncio.async(analyse_moves())
            hide_window(None)

            return True

        self.widgets["analyze_game"].connect("delete-event", hide_window)
        self.widgets["analyze_cancel_button"].connect("clicked", hide_window)
        self.widgets["analyze_ok_button"].connect("clicked", run_analyze)

    def run(self):
        self.stop_event.clear()
        self.widgets["analyze_game"].show()
        self.widgets["analyze_game"].present()
