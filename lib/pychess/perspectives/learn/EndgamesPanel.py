import asyncio
import random
from io import StringIO

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, NORMALCHESS, ARTIFICIAL, chrU2Sign
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Variants import variants
from pychess.Players.Human import Human
from pychess.Players.engineNest import discoverer
from pychess.System import conf
from pychess.perspectives import perspective_manager
from pychess.Savers import fen as fen_loader

__title__ = _("Endgames")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Practice endgames")


# TODO: get it from a text file
ENDGAMES = (
    ("kpk", "Play King and Pawn against King"),
    ("kbnk", "Play King, Bishop and Knight against King"),
    ("kbbk", "Play King and 2 Bishops against King"),
    ("kqk", "Play King and Queen against King"),
    ("krpkr", "Play King, Rook and Pawn against King and Rook"),
    ("krk", "Play King and Rook against King"),
    ("kqkr", "Play King and Queen against King and Rook"),
    ("kppkp", "Play King and 2 Pawns against King and Pawn"),
    ("kpkp", "Play King and Pawn against King and Pawn"),
    ("kqpkq", "Play King, Queen and Pawn against King and Queen"),
    ("knnkp", "Play King and Two Knights and against King and Pawn"),
    ("kppkpp", "Play King and two pawns against King and two pawns"),
    ("kqqkqr", "Play King and two qeens against King and Queen"),
)


class Sidepanel():
    def load(self, persp):
        self.persp = persp
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tv = Gtk.TreeView()

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("White"), renderer, text=0)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
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
                self.store.append([pieces[:pos], pieces[pos:], title])

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.add(self.tv)
        scrollwin.show_all()

        self.box.pack_start(scrollwin, True, True, 0)
        self.box.show_all()

        return self.box

    def row_activated(self, widget, path, col):
        if path is None:
            return
        pieces = ENDGAMES[path[0]][0]

        fen = self.create_fen(pieces)

        timemodel = TimeModel(0, 0)
        gamemodel = GameModel(timemodel)
        gamemodel.set_practice_game()

        name = conf.get("firstName", _("You"))
        p0 = (LOCAL, Human, (WHITE, name), name)

        engine = discoverer.getEngineByName("stockfish")
        name = discoverer.getName(engine)
        p1 = (ARTIFICIAL, discoverer.initPlayerEngine,
              (engine, BLACK, 20, variants[NORMALCHESS], 60, 0, 0, True), name)

        perspective = perspective_manager.get_perspective("games")
        asyncio.async(perspective.generalStart(
            gamemodel, p0, p1, loaddata=(StringIO(fen), fen_loader, 0, -1)))

    def create_fen(self, pieces):
        """ Create a random FEN position using given pieces """

        pos = pieces.rfind("k")
        pieces = pieces[:pos], pieces[pos:]

        ok = False
        while not ok:
            lboard = LBoard()
            lboard.applyFen("8/8/8/8/8/8/8/8 w - - 0 1")

            cords = list(range(0, 64))
            pawn_cords = list(range(0 + 8, 64 - 8))
            for color in (BLACK, WHITE):
                for char in pieces[color]:
                    piece = chrU2Sign[char.upper()]
                    cord = random.choice(pawn_cords if char == "p" else cords)
                    lboard._addPiece(cord, piece, color)
                    if char == "p":
                        pawn_cords.remove(cord)
                    else:
                        cords.remove(cord)

            ok = (not lboard.isChecked()) and (not lboard.opIsChecked())

        fen = lboard.asFen()
        return fen
