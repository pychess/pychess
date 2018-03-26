import asyncio

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, WAITING_TO_START, HINT
from pychess.Utils.LearnModel import LearnModel, LESSON
from pychess.Utils.TimeModel import TimeModel
from pychess.Players.Human import Human
from pychess.System import conf
from pychess.perspectives import perspective_manager
from pychess.perspectives.learn import SolvingProgress
from pychess.Savers.pgn import PGNFile
from pychess.System.protoopen import protoopen
from pychess.Players.engineNest import discoverer

__title__ = _("Lessons")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _('Guided interactive lessons in "guess the move" style')


LESSONS = (
    (1, "Charles_XII_At_Bender.pgn", "Charles XII at Bender", "gbtami", 3),
    (2, "Back_rank_threats.pgn", "Back rank threats", "gbtami", 1),
)


class Sidepanel():
    def load(self, persp):
        self.persp = persp
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tv = Gtk.TreeView()

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Id"), renderer, text=0)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), renderer, text=2)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Author"), renderer, text=3)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererProgress()
        column = Gtk.TreeViewColumn(_("Progress"), renderer, text=4, value=5)
        self.tv.append_column(column)

        self.tv.connect("row-activated", self.row_activated)

        self.store = Gtk.ListStore(int, str, str, str, str, int)

        for num, file_name, title, author, count in LESSONS:
            progress = solving_progress.get(file_name, [0] * count)
            solved = progress.count(1)
            progress = 0 if not solved else round((solved * 100.) / len(progress))
            self.store.append([num, file_name, title, author, "%s / %s" % (solved, count), progress])

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
            filename = LESSONS[path[0]][1]
            start_lesson_from(filename)


solving_progress = SolvingProgress("lessons.json")


def start_lesson_from(filename, index=None):
    chessfile = PGNFile(protoopen(addDataPrefix("learn/lessons/%s" % filename)))
    chessfile.limit = 1000
    chessfile.init_tag_database()
    records, plys = chessfile.get_records()

    progress = solving_progress.get(filename, [0] * chessfile.count)

    if index is None:
        index = progress.index(0)

    rec = records[index]

    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)
    gamemodel.set_learn_data(LESSON, filename, index, len(records))

    chessfile.loadToModel(rec, -1, gamemodel)

    color = gamemodel.boards[0].color
    player_name = conf.get("firstName", _("You"))

    w_name = player_name if color == WHITE else "PyChess"
    b_name = "PyChess" if color == WHITE else player_name

    p0 = (LOCAL, Human, (WHITE, w_name), w_name)
    p1 = (LOCAL, Human, (BLACK, b_name), b_name)

    def learn_success(gamemodel):
        progress = solving_progress[gamemodel.source]
        progress[gamemodel.current_index] = 1
        solving_progress[gamemodel.source] = progress
        asyncio.async(gamemodel.restart_analyzer(HINT))
    gamemodel.connect("learn_success", learn_success)

    def start_analyzer(gamemodel):
        asyncio.async(gamemodel.start_analyzer(HINT, force_engine=discoverer.getEngineLearn()))
    gamemodel.connect("game_started", start_analyzer)

    gamemodel.status = WAITING_TO_START
    perspective = perspective_manager.get_perspective("games")
    asyncio.async(perspective.generalStart(gamemodel, p0, p1))
