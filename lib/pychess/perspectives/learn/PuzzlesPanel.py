import asyncio

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, NORMALCHESS, ARTIFICIAL, WAITING_TO_START, HINT
from pychess.Utils.LearnModel import LearnModel, PUZZLE
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
    (1, "lichess_study_lichess-practice-piece-checkmates-i_by_arex_2017.01.25.pgn", "Lichess: Piece Checkmates I", "arex"),
    (2, "lichess_study_lichess-practice-checkmate-patterns-i_by_arex_2017.01.22.pgn", "Lichess: Checkmate Patterns I", "arex"),
    (3, "lichess_study_lichess-practice-checkmate-patterns-ii_by_arex_2017.01.25.pgn", "Lichess: Checkmate Patterns II", "arex"),
    (4, "lichess_study_lichess-practice-checkmate-patterns-iii_by_arex_2017.01.27.pgn", "Lichess: Checkmate Patterns III", "arex"),
    (5, "lichess_study_lichess-practice-checkmate-patterns-iv_by_arex_2017.01.25.pgn", "Lichess: Checkmate Patterns IV", "arex"),
    (6, "lichess_study_lichess-practice-piece-checkmates-ii_by_arex_2017.01.25.pgn", "Lichess: Piece Checkmates II", "arex"),

    (7, "lichess_study_lichess-practice-the-pin_by_arex_2017.01.22.pgn", "Lichess: The Pin", "arex"),
    (8, "lichess_study_lichess-practice-the-skewer_by_arex_2017.01.29.pgn", "Lichess: The Skewer", "arex"),
    (9, "lichess_study_lichess-practice-the-fork_by_arex_2017.01.29.pgn", "Lichess: The Fork", "arex"),
    (10, "lichess_study_lichess-practice-discovered-attacks_by_arex_2017.01.30.pgn", "Lichess:  Discovered Attacks", "arex"),
    (11, "lichess_study_lichess-practice-double-check_by_arex_2017.02.12.pgn", "Lichess: Double Check", "arex"),
    (12, "lichess_study_lichess-practice-overloaded-pieces_by_arex_2017.01.31.pgn", "Lichess: Overloaded pieces", "arex"),
    (13, "lichess_study_lichess-practice-zwischenzug_by_arex_2017.02.02.pgn", "Lichess: Zwischenzug", "arex"),

    (14, "lichess_study_lichess-practice-zugzwang_by_arex_2017.02.01.pgn", "Lichess: Zugzwang", "arex"),
    (15, "lichess_study_lichess-practice-interference_by_arex_2017.02.11.pgn", "Lichess: Interference", "arex"),
    (16, "lichess_study_lichess-practice-greek-gift_by_arex_2017.02.11.pgn", "Lichess: Greek Gift", "arex"),

    (17, "lichess_study_lichess-practice-key-squares_by_arex_2017.01.21.pgn", "Lichess: Key Squares", "arex"),
    (18, "lichess_study_lichess-practice-opposition_by_arex_2017.01.22.pgn", "Lichess: Opposition", "arex"),
    (19, "lichess_study_lichess-practice-rook-endgames_by_TonyRo_2017.02.01.pgn", "Lichess: Rook Endgames", "arex"),

    (20, "mate_in_2.pgn", "Puzzles by GMs: Mate in 2", "wtharvey.com"),
    (21, "mate_in_3.pgn", "Puzzles by GMs: Mate in 3", "wtharvey.com"),
    (22, "mate_in_4.pgn", "Puzzles by GMs: Mate in 4", "wtharvey.com"),

    (23, "lasker.olv", "Puzzles by Emanuel Lasker", "yacpdb.org"),
    (24, "loyd.olv", "Puzzles by Samuel Loyd", "yacpdb.org"),
    (25, "reti.olv", "Puzzles by Richard Réti", "yacpdb.org"),
)


class Sidepanel():
    def load(self, persp):
        self.persp = persp
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tv = Gtk.TreeView()

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Id", renderer, text=0)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), renderer, text=2)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Author", renderer, text=3)
        self.tv.append_column(column)

        self.tv.connect("row-activated", self.row_activated)

        self.store = Gtk.ListStore(int, str, str, str)

        for num, file_name, title, author in PUZZLES:
            self.store.append([num, file_name, title, author])

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
            filename = PUZZLES[path[0]][1]
            # TODO: save/restore
            latest_index = 0
            start_puzzle_from(filename, latest_index)


def start_puzzle_from(filename, index):
    if filename.lower().endswith(".pgn"):
        chessfile = PGNFile(protoopen(addDataPrefix("learn/puzzles/%s" % filename)))
        chessfile.limit = 1000
        importer = PgnImport(chessfile)
        chessfile.init_tag_database(importer)
    elif filename.lower().endswith(".olv"):
        chessfile = OLVFile(protoopen(addDataPrefix("learn/puzzles/%s" % filename), encoding="utf-8"))

    records, plys = chessfile.get_records()

    rec = records[index]

    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)

    chessfile.loadToModel(rec, 0, gamemodel)
    gamemodel.set_learn_data(PUZZLE, filename, index, len(records))

    engine = discoverer.getEngineByName(discoverer.getEngineLearn())
    ponder_off = True

    color = gamemodel.boards[0].color

    w_name = "" if rec["White"] is None else rec["White"]
    b_name = "" if rec["Black"] is None else rec["Black"]

    player_name = conf.get("firstName", _("You"))
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

    def start_analyzer(gamemodel, name, color):
        asyncio.async(gamemodel.start_analyzer(HINT, force_engine=discoverer.getEngineLearn()))
        gamemodel.players[1 - color].name = name
        gamemodel.emit("players_changed")

    gamemodel.connect("game_started", start_analyzer, opp_name, color)

    gamemodel.variant.need_initial_board = True
    gamemodel.status = WAITING_TO_START

    perspective = perspective_manager.get_perspective("games")
    asyncio.async(perspective.generalStart(gamemodel, p0, p1))
