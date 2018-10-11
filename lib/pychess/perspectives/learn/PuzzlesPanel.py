import os
import asyncio

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, NORMALCHESS, ARTIFICIAL, WAITING_TO_START, HINT, PRACTICE_GOAL_REACHED, PUZZLE
from pychess.Utils.LearnModel import LearnModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Variants import variants
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.perspectives import perspective_manager
from pychess.perspectives.learn import lessons_solving_progress
from pychess.perspectives.learn import puzzles_solving_progress
from pychess.Savers.olv import OLVFile
from pychess.Savers.pgn import PGNFile
from pychess.System import conf
from pychess.System.protoopen import protoopen

__title__ = _("Puzzles")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Lichess practice studies Puzzles from GM games and Chess compositions")


# https://lichess.org/practice, http://wtharvey.com, http://www.yacpdb.org

puzzles0 = []
puzzles1 = []
puzzles2 = []
puzzles3 = []
for elem in sorted(os.listdir(path=addDataPrefix("learn/puzzles/"))):
    if elem.startswith("lichess_study") and elem.endswith(".pgn"):
        if elem[14:31] == "lichess-practice-":
            puzzles0.append((elem, elem[31:elem.find("_by_")].replace("-", " ").capitalize(), "lichess.org"))
        else:
            puzzles0.append((elem, elem[14:elem.find("_by_").replace("-", " ").capitalize()], "lichess.org"))
    elif elem.startswith("mate_in_") and elem.endswith(".pgn"):
        puzzles1.append((elem, "Puzzles by GMs: Mate in %s" % elem[8], "wtharvey.com"))
    elif elem.endswith(".olv"):
        puzzles2.append((elem, "Puzzles by %s" % elem.split(".olv")[0].capitalize(), "yacpdb.org"))
    elif elem.endswith(".pgn"):
        puzzles3.append((elem, elem.split(".pgn")[0].capitalize(), _("others")))

PUZZLES = puzzles0 + puzzles1 + puzzles2 + puzzles3


class Sidepanel():
    def load(self, persp):
        self.persp = persp
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tv = Gtk.TreeView()

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), renderer, text=1)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Source"), renderer, text=2)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn(_("Progress"), renderer, text=3, value=4)
        self.tv.append_column(column)

        self.tv.connect("row-activated", self.row_activated)

        def on_progress_updated(solving_progress, key, progress):
            for i, row in enumerate(self.store):
                if row[0] == key:
                    solved = progress.count(1)
                    percent = 0 if not solved else round((solved * 100.) / len(progress))
                    treeiter = self.store.get_iter(Gtk.TreePath(i))
                    self.store[treeiter][3] = "%s / %s" % (solved, len(progress))
                    self.store[treeiter][4] = percent
        puzzles_solving_progress.connect("progress_updated", on_progress_updated)

        self.store = Gtk.ListStore(str, str, str, str, int)

        @asyncio.coroutine
        def coro():
            for file_name, title, author in PUZZLES:
                progress = puzzles_solving_progress.get(file_name)
                solved = progress.count(1)
                percent = 0 if not solved else round((solved * 100.) / len(progress))
                self.store.append([file_name, title, author, "%s / %s" % (solved, len(progress)), percent])
                yield from asyncio.sleep(0)
        create_task(coro())

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.tv.set_cursor(conf.get("learncombo%s" % PUZZLE))

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.add(self.tv)
        scrollwin.show_all()

        self.box.pack_start(scrollwin, True, True, 0)
        self.box.show_all()

        return self.box

    def row_activated(self, widget, path, col):
        if path is None:
            return
        else:
            filename = PUZZLES[path[0]][0]
            conf.set("categorycombo", PUZZLE)
            from pychess.widgets.TaskerManager import learn_tasker
            learn_tasker.learn_combo.set_active(path[0])
            start_puzzle_from(filename)


def start_puzzle_from(filename, index=None):
    if filename.lower().endswith(".pgn"):
        chessfile = PGNFile(protoopen(addDataPrefix("learn/puzzles/%s" % filename)))
        chessfile.limit = 1000
        chessfile.init_tag_database()
    elif filename.lower().endswith(".olv"):
        chessfile = OLVFile(protoopen(addDataPrefix("learn/puzzles/%s" % filename), encoding="utf-8"))

    records, plys = chessfile.get_records()

    progress = puzzles_solving_progress.get(filename, [0] * chessfile.count)

    if index is None:
        try:
            index = progress.index(0)
        except ValueError:
            index = 0

    rec = records[index]

    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)

    chessfile.loadToModel(rec, 0, gamemodel)

    start_puzzle_game(gamemodel, filename, records, index, rec)


def start_puzzle_game(gamemodel, filename, records, index, rec, from_lesson=False):
    gamemodel.set_learn_data(PUZZLE, filename, index, len(records), from_lesson=from_lesson)

    engine = discoverer.getEngineByName(discoverer.getEngineLearn())
    ponder_off = True

    color = gamemodel.boards[0].color

    w_name = "" if rec["White"] is None else rec["White"]
    b_name = "" if rec["Black"] is None else rec["Black"]

    player_name = conf.get("firstName")
    engine_name = discoverer.getName(engine)

    if rec["Event"].startswith("Lichess Practice"):
        w_name = player_name if color == WHITE else engine_name
        b_name = engine_name if color == WHITE else player_name

    opp_name = engine_name if rec["Event"].startswith("Lichess Practice") else b_name

    if color == WHITE:
        p0 = (LOCAL, Human, (WHITE, w_name), w_name)
        p1 = (ARTIFICIAL, discoverer.initPlayerEngine,
              (engine, BLACK, 20, variants[NORMALCHESS], 20, 0, 0, ponder_off), b_name)
    else:
        p0 = (ARTIFICIAL, discoverer.initPlayerEngine,
              (engine, WHITE, 20, variants[NORMALCHESS], 20, 0, 0, ponder_off), w_name)
        p1 = (LOCAL, Human, (BLACK, b_name), b_name)

    def on_game_started(gamemodel, name, color):
        perspective.activate_panel("annotationPanel")
        create_task(gamemodel.start_analyzer(HINT, force_engine=discoverer.getEngineLearn()))
        gamemodel.players[1 - color].name = name
        gamemodel.emit("players_changed")
    gamemodel.connect("game_started", on_game_started, opp_name, color)

    def goal_checked(gamemodle):
        if gamemodel.reason == PRACTICE_GOAL_REACHED:
            if from_lesson:
                progress = lessons_solving_progress[gamemodel.source]
            else:
                progress = puzzles_solving_progress[gamemodel.source]

            progress[gamemodel.current_index] = 1

            if from_lesson:
                lessons_solving_progress[gamemodel.source] = progress
            else:
                puzzles_solving_progress[gamemodel.source] = progress
    gamemodel.connect("goal_checked", goal_checked)

    gamemodel.variant.need_initial_board = True
    gamemodel.status = WAITING_TO_START

    perspective = perspective_manager.get_perspective("games")
    create_task(perspective.generalStart(gamemodel, p0, p1))
