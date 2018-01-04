import asyncio
from io import StringIO

from gi.repository import Gtk

from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, RUNNING
from pychess.Utils.GameModel import GameModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.Move import parseAny
from pychess.Players.Human import Human
from pychess.perspectives import perspective_manager
from pychess.Savers import fen as fen_loader

__title__ = _("Lectures")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Study FICS lectures offline")


LECTURES = (
    (1, "2...Qh4+ against the King's Gambit", "toddmf"),
    (2, "Tactics Training lesson 1# 'Back rank weakness'", "knackie"),
    (3, "Denker's Favorite Game", "toddmf"),
    (4, "Introduction to the 2.Nc3 Caro-Kann", "KayhiKing"),
    (5, "Tactics Training lesson 2# 'Discovered Attack'", "knackie"),
    (6, "King's Indian Attack vs. the French", "cissmjg"),
    (7, "Rook vs Pawn endgames", "toddmf"),
    (8, "The Stonewall Attack", "MBDil"),
    (9, "Tactics Training lesson 3# 'Enclosed Kings'", "knackie"),
    (10, "The Steinitz Variation of the French Defense", "Seipman"),
    (11, "A draw against a Grandmaster", "talpa"),
    (12, "Tactics Training lesson 4# 'King in the centre'", "knackie"),
    (13, "The Modern Defense", "GMDavies"),
    (14, "Tactics Training lesson 5# 'Pulling the king to the open'", "knackie"),
    (15, "King's Indian Attack vs. the Caro-Kann", "cissmjg"),
    (16, "Introduction to Bughouse", "Tecumseh"),
    (17, "Refuting the Milner-Barry Gambit in the French Defense", "Kabal"),
    (18, "Tactics Training lesson 6# 'Mating Attack'", "knackie"),
    (19, "Closed Sicilian Survey, part 1", "Oren"),
    (20, "Hypermodern Magic - A study of the central blockade", "Bahamut"),
    (21, "Tactics Training lesson 7# 'Opening / Closing Files'", "knackie"),
    (22, "Thoughts on the Refutation of the Milner-Barry", "knackie"),
    (23, "Tactics Training lesson 8# 'Opening / Closing Diagonals'", "knackie"),
    (24, "King's Indian Attack vs. Other Defenses", "cissmjg"),
    (25, "Basic Pawn Endings I", "DAV"),
    (26, "Giuoco Piano", "afw"),
    (27, "Tactics Training lesson 9# 'Long Diagonals'", "knackie"),
    (28, "Secrets of the Flank Attack", "Shidinov"),
    (29, "Mating Combinations", "Kabal"),
    (30, "Basic Pawn Endings II", "DAV"),
    (31, "Grandmaster Knezevic's first FICS lecture", "toddmf"),
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
        column = Gtk.TreeViewColumn("Title", renderer, text=1)
        self.tv.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Author", renderer, text=2)
        self.tv.append_column(column)

        self.tv.connect("row-activated", self.row_activated)

        self.store = Gtk.ListStore(int, str, str)

        for num, title, author in LECTURES:
            self.store.append([num, title, author])

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
        lecnum = path[0] + 1
        self.lecture = addDataPrefix("lectures/lec%s.txt" % lecnum)

        # connection.client.run_command("examine")
        gamemodel = self.start_lecture_game()

        def lecture_steps():
            with open(self.lecture, "r") as f:
                for line in f:
                    yield line
            return

        self.steps = lecture_steps()

        @asyncio.coroutine
        def coro(gamemodel):
            exit_lecture = False
            inside_bsetup = False
            paused = False
            moves_played = 0

            KIBITZ, BACKWARD, BSETUP, BSETUP_DONE, FEN, TOMOVE, WCASTLE, BCASTLE, \
                WNAME, BNAME, REVERT, WAIT, MOVE = range(13)

            while True:
                try:
                    step = next(self.steps)
                    print(step)

                    parts = step.strip().split()

                    command = None
                    param = ""

                    if parts[0] == "k" or parts[0] == "kibitz":
                        command = KIBITZ
                        param = " ".join(parts[1:])
                    elif parts[0] == "back":
                        command = BACKWARD
                        param = int(parts[1]) if len(parts) > 1 else 1
                    elif parts[0] == "bsetup":
                        if len(parts) == 1:
                            command = BSETUP
                        else:
                            if parts[1] == "done":
                                command = BSETUP_DONE
                            elif parts[1] == "fen":
                                command = FEN
                                param = parts[2]
                            elif parts[1] == "tomove":
                                command = TOMOVE
                                param = "w" if parts[2].lower()[0] == "w" else "b"
                            elif parts[1] == "wcastle":
                                command = WCASTLE
                                param = parts[2]
                            elif parts[1] == "bcastle":
                                command = BCASTLE
                                param = parts[2]
                    elif parts[0] == "tomove":
                        command = TOMOVE
                        param = "w" if parts[1].lower()[0] == "w" else "b"
                    elif parts[0] == "wname":
                        command = WNAME
                        param = parts[1]
                    elif parts[0] == "bname":
                        command = BNAME
                        param = parts[1]
                    elif parts[0] == "revert":
                        command = REVERT
                    elif len(parts) == 1 and parts[0].isdigit():
                        command = WAIT
                        param = int(parts[0])
                    else:
                        command = MOVE
                        param = parts[0]

                    if not inside_bsetup and command == BSETUP:
                        inside_bsetup = True
                        pieces = ""
                        color = ""
                        castl = ""
                        ep = ""
                    elif inside_bsetup and command == BSETUP_DONE:
                        inside_bsetup = False

                    wait_sec = int(param) if command == WAIT else 2

                    if inside_bsetup:
                        wait_sec = -1

                    while wait_sec >= 0:
                        if gamemodel.lecture_exit_event.is_set():
                            gamemodel.lecture_exit_event.clear()
                            exit_lecture = True
                            break

                        if gamemodel.lecture_skip_event.is_set():
                            gamemodel.lecture_skip_event.clear()
                            paused = False
                            break

                        if gamemodel.lecture_pause_event.is_set():
                            gamemodel.lecture_pause_event.clear()
                            paused = True

                        yield from asyncio.sleep(0.1)
                        if not paused:
                            wait_sec = wait_sec - 0.1

                    if exit_lecture:
                        gamemodel.players[0].putMessage("Lecture exited.")
                        break

                    if command != WAIT:
                        if command == KIBITZ:
                            gamemodel.players[0].putMessage(param)
                        if command == BACKWARD:
                            gamemodel.undoMoves(param)
                            moves_played -= param
                        if command == MOVE:
                            board = gamemodel.getBoardAtPly(gamemodel.ply)
                            move = parseAny(board, param)
                            gamemodel.curplayer.move_queue.put_nowait(move)
                            moves_played += 1
                        elif command == REVERT:
                            gamemodel.undoMoves(moves_played)
                            moves_played = 0
                        elif command == BNAME:
                            gamemodel.players[BLACK].name = param
                            gamemodel.emit("players_changed")
                        elif command == WNAME:
                            gamemodel.players[WHITE].name = param
                            gamemodel.emit("players_changed")
                        elif command == FEN:
                            pieces = param
                        elif command == TOMOVE:
                            color = param
                        elif command == WCASTLE:
                            if param == "both":
                                castl += "KQ"
                            elif param == "kside":
                                castl += "K"
                            elif param == "qside":
                                castl += "Q"
                        elif command == BCASTLE:
                            if param == "both":
                                castl += "kq"
                            elif param == "kside":
                                castl += "k"
                            elif param == "qside":
                                castl += "q"
                        elif command == BSETUP_DONE:
                            if not castl:
                                castl = "-"
                            if not ep:
                                ep = "-"
                            fen = "%s %s %s %s 0 1" % (pieces, color, castl, ep)

                            curplayer = gamemodel.curplayer
                            gamemodel.status = RUNNING
                            gamemodel.loadAndStart(
                                StringIO(fen),
                                fen_loader,
                                0,
                                -1,
                                first_time=False)
                            curplayer.move_queue.put_nowait("int")
                            gamemodel.emit("game_started")
                            moves_played = 0

                except StopIteration:
                    # connection.client.run_command("kibitz That concludes this lecture.")
                    break

        asyncio.async(coro(gamemodel))

    def start_lecture_game(self):
        timemodel = TimeModel(0, 0)
        gamemodel = GameModel(timemodel)
        gamemodel.set_offline_lecture()
        white_name = black_name = "pychessbot"
        p0 = (LOCAL, Human, (WHITE, white_name), white_name)
        p1 = (LOCAL, Human, (BLACK, black_name), black_name)

        perspective = perspective_manager.get_perspective("games")
        asyncio.async(perspective.generalStart(gamemodel, p0, p1))

        return gamemodel
