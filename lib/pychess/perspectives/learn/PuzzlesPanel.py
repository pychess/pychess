import asyncio
import random

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, NORMALCHESS, ARTIFICIAL, WAITING_TO_START, HINT
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Variants import variants
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.perspectives import perspective_manager
from pychess.Savers.olv import OLVFile
from pychess.Savers.pgn import PGNFile
from pychess.System import conf
from pychess.System.protoopen import protoopen
from pychess.Database.PgnImport import PgnImport

__title__ = _("Puzzles")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Puzzles from GM games and Chess compositions")


# https://lichess.org/practice, http://wtharvey.com, http://www.yacpdb.org
PUZZLES = (
    ("lichess_study_lichess-practice-checkmate-patterns-i_by_arex_2017.01.22.pgn", "checkmate-patterns-i"),
    ("lichess_study_lichess-practice-checkmate-patterns-ii_by_arex_2017.01.25.pgn", "checkmate-patterns-ii"),
    ("lichess_study_lichess-practice-checkmate-patterns-iii_by_arex_2017.01.27.pgn", "checkmate-patterns-iii"),
    ("lichess_study_lichess-practice-checkmate-patterns-iv_by_arex_2017.01.25.pgn", "checkmate-patterns-iv"),
    ("lichess_study_lichess-practice-discovered-attacks_by_arex_2017.01.30.pgn", "discovered-attacks"),
    ("lichess_study_lichess-practice-double-check_by_arex_2017.02.12.pgn", "double-check"),
    ("lichess_study_lichess-practice-greek-gift_by_arex_2017.02.11.pgn", "greek-gift"),
    ("lichess_study_lichess-practice-interference_by_arex_2017.02.11.pgn", "interference"),
    ("lichess_study_lichess-practice-key-squares_by_arex_2017.01.21.pgn", "key-squares"),
    ("lichess_study_lichess-practice-opposition_by_arex_2017.01.22.pgn", "opposition"),
    ("lichess_study_lichess-practice-overloaded-pieces_by_arex_2017.01.31.pgn", "overloaded-pieces"),
    ("lichess_study_lichess-practice-piece-checkmates-i_by_arex_2017.01.25.pgn", "piece-checkmates-i"),
    ("lichess_study_lichess-practice-piece-checkmates-ii_by_arex_2017.01.25.pgn", "piece-checkmates-ii"),
    ("lichess_study_lichess-practice-rook-endgames_by_TonyRo_2017.02.01.pgn", "rook-endgames"),
    ("lichess_study_lichess-practice-the-fork_by_arex_2017.01.29.pgn", "the-fork"),
    ("lichess_study_lichess-practice-the-pin_by_arex_2017.01.22.pgn", "the-pin"),
    ("lichess_study_lichess-practice-the-skewer_by_arex_2017.01.29.pgn", "the-skewer"),
    ("lichess_study_lichess-practice-zugzwang_by_arex_2017.02.01.pgn", "zugzwang"),
    ("lichess_study_lichess-practice-zwischenzug_by_arex_2017.02.02.pgn", "zwischenzug"),
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
        chessfile = PGNFile(protoopen(addDataPrefix("learn/puzzles/%s" % filename)))
        chessfile.limit = 1000
        importer = PgnImport(chessfile)
        chessfile.init_tag_database(importer)
    elif filename.lower().endswith(".olv"):
        chessfile = OLVFile(protoopen(addDataPrefix("learn/puzzles/%s" % filename), encoding="utf-8"))

    records, plys = chessfile.get_records()

    rec = records[random.randrange(0, len(records))]

    timemodel = TimeModel(0, 0)
    gamemodel = GameModel(timemodel)
    gamemodel.set_practice_game()
    gamemodel.practice = ("puzzle", filename)

    chessfile.loadToModel(rec, 0, gamemodel)
    print(gamemodel.tags["Termination"])

    engine = discoverer.getEngineByName(discoverer.getEngineLearn())
    ponder_off = True

    color = gamemodel.boards[0].color
    player_name = conf.get("firstName", _("You"))
    engine_name = discoverer.getName(engine)

    w_name = player_name if color == WHITE else engine_name
    b_name = engine_name if color == WHITE else player_name

    if color == WHITE:
        p0 = (LOCAL, Human, (WHITE, w_name), w_name)
        p1 = (ARTIFICIAL, discoverer.initPlayerEngine,
              (engine, BLACK, 20, variants[NORMALCHESS], 60, 0, 0, ponder_off), b_name)
    else:
        p0 = (ARTIFICIAL, discoverer.initPlayerEngine,
              (engine, WHITE, 20, variants[NORMALCHESS], 60, 0, 0, ponder_off), w_name)
        p1 = (LOCAL, Human, (BLACK, b_name), b_name)

    def fix_name(gamemodel, name, color):
        asyncio.async(gamemodel.start_analyzer(HINT, force_engine=discoverer.getEngineLearn()))
        gamemodel.players[1 - color].name = name
        gamemodel.emit("players_changed")

    gamemodel.connect("game_started", fix_name, engine_name, color)

    gamemodel.variant.need_initial_board = True
    gamemodel.status = WAITING_TO_START

    perspective = perspective_manager.get_perspective("games")
    asyncio.async(perspective.generalStart(gamemodel, p0, p1))
