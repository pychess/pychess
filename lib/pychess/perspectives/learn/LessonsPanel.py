import os
import asyncio

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, WAITING_TO_START, HINT, LESSON
from pychess.Utils.LearnModel import LearnModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.Human import Human
from pychess.System import conf
from pychess.perspectives import perspective_manager
from pychess.perspectives.learn import lessons_solving_progress
from pychess.perspectives.learn.PuzzlesPanel import start_puzzle_game
from pychess.Savers.pgn import PGNFile
from pychess.System.protoopen import protoopen
from pychess.Players.engineNest import discoverer

__title__ = _("Lessons")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _('Guided interactive lessons in "guess the move" style')


LESSONS = []
for elem in sorted(os.listdir(path=addDataPrefix("learn/lessons/"))):
    if elem.startswith("lichess_study") and elem.endswith(".pgn"):
        title = elem.replace("beta-lichess-practice-", "")
        title = title[14:title.find("_by_")].replace("-", " ").capitalize()
        LESSONS.append((elem, title, "lichess.org"))
    elif elem.endswith(".pgn"):
        LESSONS.append((elem, elem.replace("-", " ").capitalize(), "pychess.org"))


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
        lessons_solving_progress.connect("progress_updated", on_progress_updated)

        self.store = Gtk.ListStore(str, str, str, str, int)

        @asyncio.coroutine
        def coro():
            for file_name, title, author in LESSONS:
                progress = lessons_solving_progress.get(file_name)
                solved = progress.count(1)
                percent = 0 if not solved else round((solved * 100.) / len(progress))
                self.store.append([file_name, title, author, "%s / %s" % (solved, len(progress)), percent])
        create_task(coro())

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.tv.set_cursor(conf.get("learncombo%s" % LESSON))

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
            filename = LESSONS[path[0]][0]
            conf.set("categorycombo", LESSON)
            from pychess.widgets.TaskerManager import learn_tasker
            learn_tasker.learn_combo.set_active(path[0])
            start_lesson_from(filename)


def start_lesson_from(filename, index=None):
    chessfile = PGNFile(protoopen(addDataPrefix("learn/lessons/%s" % filename)))
    chessfile.limit = 1000
    chessfile.init_tag_database()
    records, plys = chessfile.get_records()

    progress = lessons_solving_progress.get(filename, [0] * chessfile.count)

    if index is None:
        try:
            index = progress.index(0)
        except ValueError:
            index = 0

    rec = records[index]

    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)

    chessfile.loadToModel(rec, -1, gamemodel)

    if len(gamemodel.moves) > 0:
        start_lesson_game(gamemodel, filename, chessfile, records, index, rec)
    else:
        start_puzzle_game(gamemodel, filename, records, index, rec, from_lesson=True)


def start_lesson_game(gamemodel, filename, chessfile, records, index, rec):
    gamemodel.set_learn_data(LESSON, filename, index, len(records))

    # Lichess doesn't export some study data to .pgn like
    # Orientation, Analysis mode, Chapter pinned comment, move hint comments, general fail comment
    if filename.startswith("lichess_study_beta-lichess-practice-checkmating-with-a-knight-and-bishop"):
        if index in (4, 6, 8, 9):
            gamemodel.tags["Orientation"] = "White"
            print(index, '[Orientation "White"]')

    color = gamemodel.boards[0].color
    player_name = conf.get("firstName")

    w_name = player_name if color == WHITE else "PyChess"
    b_name = "PyChess" if color == WHITE else player_name

    p0 = (LOCAL, Human, (WHITE, w_name), w_name)
    p1 = (LOCAL, Human, (BLACK, b_name), b_name)

    def learn_success(gamemodel):
        gamemodel.scores = {}
        chessfile.loadToModel(rec, -1, gamemodel)
        progress = lessons_solving_progress[gamemodel.source]
        progress[gamemodel.current_index] = 1
        lessons_solving_progress[gamemodel.source] = progress
        if "FEN" in gamemodel.tags:
            create_task(gamemodel.restart_analyzer(HINT))
    gamemodel.connect("learn_success", learn_success)

    def on_game_started(gamemodel):
        perspective.activate_panel("annotationPanel")
        if "FEN" in gamemodel.tags:
            create_task(gamemodel.start_analyzer(HINT, force_engine=discoverer.getEngineLearn()))
    gamemodel.connect("game_started", on_game_started)

    gamemodel.status = WAITING_TO_START
    perspective = perspective_manager.get_perspective("games")
    create_task(perspective.generalStart(gamemodel, p0, p1))
