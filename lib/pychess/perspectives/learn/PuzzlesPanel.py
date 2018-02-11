import asyncio
import random

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, NORMALCHESS, ARTIFICIAL, WAITING_TO_START, HINT
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Variants import variants
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer, stockfish_name
from pychess.perspectives import perspective_manager
from pychess.Savers.olv import OLVFile
from pychess.Savers.pgn import PGNFile
from pychess.System.protoopen import protoopen
from pychess.Database.PgnImport import PgnImport

__title__ = _("Puzzles")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Puzzles from GM games and Chess compositions")


# http://wtharvey.com/
PUZZLES = (
    ("mate_in_2.pgn", "Mate in two"),
    ("mate_in_3.pgn", "Mate in three"),
    ("mate_in_4.pgn", "Mate in four"),
    ("lasker.olv", "Lasker Emanuel"),
    ("loyd.olv", "Loyd Samuel"),
    ("reti.olv", "Réti Richard"),
)


class Sidepanel():
    def load(self, persp):
        self.persp = persp
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tv = Gtk.TreeView()

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), renderer, text=1)
        self.tv.append_column(column)

        self.tv.connect("row-activated", self.row_activated)

        self.store = Gtk.ListStore(str, str)

        for file_name, title in PUZZLES:
            self.store.append([file_name, title])

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
            filename = PUZZLES[path[0]][0]
            start_puzzle_from(filename)


def start_puzzle_from(filename):
    if filename.lower().endswith(".pgn"):
        chessfile = PGNFile(protoopen(addDataPrefix("lectures/%s" % filename)))
        chessfile.limit = 1000
        importer = PgnImport(chessfile)
        chessfile.init_tag_database(importer)
    elif filename.lower().endswith(".olv"):
        chessfile = OLVFile(protoopen(addDataPrefix("lectures/%s" % filename), encoding="utf-8"))

    records, plys = chessfile.get_records()

    rec = records[random.randrange(0, len(records))]

    timemodel = TimeModel(0, 0)
    gamemodel = GameModel(timemodel)
    gamemodel.set_practice_game()
    gamemodel.practice = ("puzzle", filename)

    chessfile.loadToModel(rec, 0, gamemodel)

    engine = discoverer.getEngineByName(stockfish_name)

    color = gamemodel.boards[0].color
    if color == WHITE:
        name = rec["White"]
        p0 = (LOCAL, Human, (WHITE, name), name)

        oppname = rec["Black"]
        ponder_off = True
        p1 = (ARTIFICIAL, discoverer.initPlayerEngine,
              (engine, BLACK, 20, variants[NORMALCHESS], 60, 0, 0, ponder_off), oppname)
    else:
        oppname = rec["White"]
        ponder_off = True
        p0 = (ARTIFICIAL, discoverer.initPlayerEngine,
              (engine, WHITE, 20, variants[NORMALCHESS], 60, 0, 0, ponder_off), oppname)

        name = rec["Black"]
        p1 = (LOCAL, Human, (BLACK, name), name)

    def fix_name(gamemodel, name, color):
        asyncio.async(gamemodel.start_analyzer(HINT, force_engine=stockfish_name))
        gamemodel.players[1 - color].name = oppname
        gamemodel.emit("players_changed")

    gamemodel.connect("game_started", fix_name, name, color)

    gamemodel.variant.need_initial_board = True
    gamemodel.status = WAITING_TO_START

    perspective = perspective_manager.get_perspective("games")
    asyncio.async(perspective.generalStart(gamemodel, p0, p1))
