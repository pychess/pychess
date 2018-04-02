import os
import asyncio

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, WAITING_TO_START, HINT
from pychess.Utils.LearnModel import LearnModel, LESSON
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.Human import Human
from pychess.System import conf
from pychess.perspectives import perspective_manager
from pychess.perspectives.learn import lessons_solving_progress
from pychess.Savers.pgn import PGNFile
from pychess.System.protoopen import protoopen
from pychess.Players.engineNest import discoverer

__title__ = _("Lessons")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _('Guided interactive lessons in "guess the move" style')


LESSONS = []
for elem in sorted(os.listdir(path=addDataPrefix("learn/lessons/"))):
    if elem.startswith("lichess_study") and elem.endswith(".pgn"):
        LESSONS.append((elem, elem[14:elem.find("_by_")].replace("-", " ").capitalize(), "lichess.org"))
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
        column = Gtk.TreeViewColumn(_("Author"), renderer, text=2)
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

        for file_name, title, author in LESSONS:
            progress = lessons_solving_progress.get(file_name)
            solved = progress.count(1)
            percent = 0 if not solved else round((solved * 100.) / len(progress))
            self.store.append([file_name, title, author, "%s / %s" % (solved, len(progress)), percent])

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.tv.set_cursor(0)

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
            start_lesson_from(filename)


def start_lesson_from(filename, index=None):
    if filename.startswith("lichess_study"):
        chessfile = PGNFile(protoopen(addDataPrefix("learn/lessons/%s" % filename), encoding="utf-8"))
    else:
        chessfile = PGNFile(protoopen(addDataPrefix("learn/lessons/%s" % filename)))
    chessfile.limit = 1000
    chessfile.init_tag_database()
    records, plys = chessfile.get_records()

    progress = lessons_solving_progress.get(filename, [0] * chessfile.count)

    if index is None:
        index = progress.index(0)

    rec = records[index]

    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)

    chessfile.loadToModel(rec, -1, gamemodel)
    gamemodel.set_learn_data(LESSON, filename, index, len(records))

    color = gamemodel.boards[0].color
    player_name = conf.get("firstName", _("You"))

    w_name = player_name if color == WHITE else "PyChess"
    b_name = "PyChess" if color == WHITE else player_name

    p0 = (LOCAL, Human, (WHITE, w_name), w_name)
    p1 = (LOCAL, Human, (BLACK, b_name), b_name)

    def learn_success(gamemodel):
        chessfile.loadToModel(rec, -1, gamemodel)
        progress = lessons_solving_progress[gamemodel.source]
        progress[gamemodel.current_index] = 1
        lessons_solving_progress[gamemodel.source] = progress
        asyncio.async(gamemodel.restart_analyzer(HINT))
    gamemodel.connect("learn_success", learn_success)

    def on_game_started(gamemodel):
        perspective.activate_panel("annotationPanel")
        asyncio.async(gamemodel.start_analyzer(HINT, force_engine=discoverer.getEngineLearn()))
    gamemodel.connect("game_started", on_game_started)

    gamemodel.status = WAITING_TO_START
    perspective = perspective_manager.get_perspective("games")
    asyncio.async(perspective.generalStart(gamemodel, p0, p1))
