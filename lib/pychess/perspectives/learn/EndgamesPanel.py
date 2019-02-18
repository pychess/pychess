import random
from io import StringIO

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, NORMALCHESS, ARTIFICIAL, chr2Sign, chrU2Sign, FAN_PIECES, HINT, ENDGAME
from pychess.Utils.LearnModel import LearnModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.lutils.attack import isAttacked
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import FILE, RANK
from pychess.Variants import variants
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.System import conf
from pychess.perspectives import perspective_manager
from pychess.Savers import fen as fen_loader

__title__ = _("Endgames")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Practice endgames with computer")


# TODO: get it from a text file
ENDGAMES = (
    ("kpk", "King and Pawn vs King"),
    ("kbnk", "King, Bishop and Knight vs King"),
    ("kbbk", "King and 2 Bishops vs King"),
    ("krk", "King and Rook vs King"),
    ("kqk", "King and Queen vs King"),
    ("kqkr", "King and Queen vs King and Rook"),
    ("krpkr", "King, Rook and Pawn vs King and Rook"),
    ("kppkp", "King and 2 Pawns vs King and Pawn"),
    ("kpkp", "King and Pawn vs King and Pawn"),
    ("kqpkq", "King, Queen and Pawn vs King and Queen"),
    ("knnkp", "King and Two Knights and vs King and Pawn"),
    ("kppkpp", "King and two pawns vs King and two pawns"),
    ("kqqkqr", "King and two queens vs King and Queen"),
)


class Sidepanel():
    def load(self, persp):
        self.persp = persp
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tv = Gtk.TreeView()

        renderer = Gtk.CellRendererText()
        renderer.props.font = "Times 14"
        column = Gtk.TreeViewColumn(_("White"), renderer, text=0)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.props.font = "Times 14"
        column = Gtk.TreeViewColumn(_("Black"), renderer, text=1)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Title"), renderer, text=2)
        self.tv.append_column(column)

        self.tv.connect("row-activated", self.row_activated)

        self.store = Gtk.ListStore(str, str, str)

        for pieces, title in ENDGAMES:
            if pieces.count("k") != 2:
                print("Game needs exactly 2 kings! %s" % pieces)
                continue
            elif len(pieces) > 6:
                print("Max 6 pieces, please! %s" % pieces)
                continue
            else:
                for piece in pieces:
                    if piece not in ("kqrbnp"):
                        print("Invalid piece %s in %s" % (piece, pieces))
                        continue

                pos = pieces.rfind("k")
                white_pieces, black_pieces = pieces[:pos], pieces[pos:]
                wfan = []
                for piece in white_pieces:
                    wfan.append(FAN_PIECES[0][chr2Sign[piece]])
                bfan = []
                for piece in black_pieces:
                    bfan.append(FAN_PIECES[1][chr2Sign[piece]])
                self.store.append(["".join(wfan), "".join(bfan), title])

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.tv.set_cursor(conf.get("learncombo%s" % ENDGAME))

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
            pieces = ENDGAMES[path[0]][0].lower()
            conf.set("categorycombo", ENDGAME)
            from pychess.widgets.TaskerManager import learn_tasker
            learn_tasker.learn_combo.set_active(path[0])
            start_endgame_from(pieces)


def start_endgame_from(pieces):
    fen = create_fen(pieces)

    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)
    gamemodel.set_learn_data(ENDGAME, pieces)

    player_name = conf.get("firstName")
    p0 = (LOCAL, Human, (WHITE, player_name), player_name)

    engine = discoverer.getEngineByName(discoverer.getEngineLearn())
    ponder_off = True
    engine_name = discoverer.getName(engine)
    p1 = (ARTIFICIAL, discoverer.initPlayerEngine,
          (engine, BLACK, 20, variants[NORMALCHESS], 60, 0, 0, ponder_off), engine_name)

    def restart_analyzer(gamemodel):
        create_task(gamemodel.restart_analyzer(HINT))
    gamemodel.connect("learn_success", restart_analyzer)

    def on_game_started(gamemodel):
        perspective.activate_panel("annotationPanel")
        create_task(gamemodel.start_analyzer(HINT, force_engine=discoverer.getEngineLearn()))
    gamemodel.connect("game_started", on_game_started)

    perspective = perspective_manager.get_perspective("games")
    create_task(perspective.generalStart(gamemodel, p0, p1, loaddata=(StringIO(fen), fen_loader, 0, -1)))


def create_fen(pieces):
    """ Create a random FEN position using given pieces """

    pos = pieces.rfind("k")
    pieces = pieces[:pos], pieces[pos:]

    ok = False
    while not ok:
        lboard = LBoard()
        lboard.applyFen("8/8/8/8/8/8/8/8 w - - 0 1")
        bishop_cords = [[], []]
        bishop_colors_ok = True

        cords = list(range(0, 64))
        pawn_cords = list(range(0 + 8, 64 - 8))

        # Order of color is important here to prevent offering
        # positions with trivial captures in first move
        for color in (WHITE, BLACK):
            for char in pieces[color]:
                piece = chrU2Sign[char.upper()]
                attacked = True
                limit = 100
                while attacked and limit > 0:
                    cord = random.choice(pawn_cords if char == "p" else cords)
                    attacked = isAttacked(lboard, cord, 1 - color)
                    limit -= 1
                lboard._addPiece(cord, piece, color)
                cords.remove(cord)
                if cord in pawn_cords:
                    pawn_cords.remove(cord)
                if char == "b":
                    bishop_cords[color].append(cord)

            # 2 same color bishop is not ok
            if len(bishop_cords[color]) == 2 and bishop_colors_ok:
                b0, b1 = bishop_cords[color]
                b0_color = BLACK if RANK(b0) % 2 == FILE(b0) % 2 else WHITE
                b1_color = BLACK if RANK(b1) % 2 == FILE(b1) % 2 else WHITE
                if b0_color == b1_color:
                    bishop_colors_ok = False
                    break

        ok = (not lboard.isChecked()) and (not lboard.opIsChecked()) and bishop_colors_ok

    fen = lboard.asFen()
    return fen
