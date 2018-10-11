import asyncio
from io import StringIO

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.System.prefix import addDataPrefix
from pychess.Utils.const import WHITE, BLACK, LOCAL, RUNNING, LECTURE
from pychess.Utils.LearnModel import LearnModel
from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.Move import parseAny
from pychess.Players.Human import Human
from pychess.perspectives import perspective_manager
from pychess.Savers import fen as fen_loader
from pychess.System import conf

__title__ = _("Lectures")

__icon__ = addDataPrefix("glade/panel_book.svg")

__desc__ = _("Study FICS lectures offline")


LECTURES = (
    ("lec1.txt", "2...Qh4+ against the King's Gambit", "toddmf"),
    ("lec2.txt", "Tactics Training lesson 1# 'Back rank weakness'", "knackie"),
    ("lec3.txt", "Denker's Favorite Game", "toddmf"),
    ("lec4.txt", "Introduction to the 2.Nc3 Caro-Kann", "KayhiKing"),
    ("lec5.txt", "Tactics Training lesson 2# 'Discovered Attack'", "knackie"),
    ("lec6.txt", "King's Indian Attack vs. the French", "cissmjg"),
    ("lec7.txt", "Rook vs Pawn endgames", "toddmf"),
    ("lec8.txt", "The Stonewall Attack", "MBDil"),
    ("lec9.txt", "Tactics Training lesson 3# 'Enclosed Kings'", "knackie"),
    ("lec10.txt", "The Steinitz Variation of the French Defense", "Seipman"),
    ("lec11.txt", "A draw against a Grandmaster", "talpa"),
    ("lec12.txt", "Tactics Training lesson 4# 'King in the centre'", "knackie"),
    ("lec13.txt", "The Modern Defense", "GMDavies"),
    ("lec14.txt", "Tactics Training lesson 5# 'Pulling the king to the open'", "knackie"),
    ("lec15.txt", "King's Indian Attack vs. the Caro-Kann", "cissmjg"),
    ("lec16.txt", "Introduction to Bughouse", "Tecumseh"),
    ("lec17.txt", "Refuting the Milner-Barry Gambit in the French Defense", "Kabal"),
    ("lec18.txt", "Tactics Training lesson 6# 'Mating Attack'", "knackie"),
    ("lec19.txt", "Closed Sicilian Survey, part 1", "Oren"),
    ("lec20.txt", "Hypermodern Magic - A study of the central blockade", "Bahamut"),
    ("lec21.txt", "Tactics Training lesson 7# 'Opening / Closing Files'", "knackie"),
    ("lec22.txt", "Thoughts on the Refutation of the Milner-Barry", "knackie"),
    ("lec23.txt", "Tactics Training lesson 8# 'Opening / Closing Diagonals'", "knackie"),
    ("lec24.txt", "King's Indian Attack vs. Other Defenses", "cissmjg"),
    ("lec25.txt", "Basic Pawn Endings I", "DAV"),
    ("lec26.txt", "Giuoco Piano", "afw"),
    ("lec27.txt", "Tactics Training lesson 9# 'Long Diagonals'", "knackie"),
    ("lec28.txt", "Secrets of the Flank Attack", "Shidinov"),
    ("lec29.txt", "Mating Combinations", "Kabal"),
    ("lec30.txt", "Basic Pawn Endings II", "DAV"),
    ("lec31.txt", "Grandmaster Knezevic's first FICS lecture", "toddmf"),
)


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

        self.tv.connect("row-activated", self.row_activated)

        self.store = Gtk.ListStore(str, str, str)

        for file_name, title, author in LECTURES:
            self.store.append([file_name, title, author])

        self.tv.set_model(self.store)
        self.tv.get_selection().set_mode(Gtk.SelectionMode.BROWSE)
        self.tv.set_cursor(conf.get("learncombo%s" % LECTURE))

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
            filename = LECTURES[path[0]][0]
            conf.set("categorycombo", LECTURE)
            from pychess.widgets.TaskerManager import learn_tasker
            learn_tasker.learn_combo.set_active(path[0])
            start_lecture_from(filename)


def start_lecture_from(filename, index=None):
    if index is None:
        index = 0

    # connection.client.run_command("examine")
    timemodel = TimeModel(0, 0)
    gamemodel = LearnModel(timemodel)
    gamemodel.set_learn_data(LECTURE, filename, index)

    white_name = black_name = "PyChess"
    p0 = (LOCAL, Human, (WHITE, white_name), white_name)
    p1 = (LOCAL, Human, (BLACK, black_name), black_name)

    def on_game_started(gamemodel):
        perspective.activate_panel("chatPanel")
    gamemodel.connect("game_started", on_game_started)

    perspective = perspective_manager.get_perspective("games")
    create_task(perspective.generalStart(gamemodel, p0, p1))

    def lecture_steps(lecture_file):
        with open(lecture_file, "r") as f:
            for line in f:
                yield line
        return

    lecture_file = addDataPrefix("learn/lectures/%s" % filename)
    steps = lecture_steps(lecture_file)

    @asyncio.coroutine
    def coro(gamemodel, steps):
        exit_lecture = False
        inside_bsetup = False
        paused = False
        moves_played = 0

        KIBITZ, BACKWARD, BSETUP, BSETUP_DONE, FEN, TOMOVE, WCASTLE, BCASTLE, \
            WNAME, BNAME, REVERT, WAIT, MOVE = range(13)

        while True:
            try:
                step = next(steps)
                print(step)

                parts = step.strip().split()

                command = None
                param = ""

                if parts[0].lower() in ("k", "ki", "kib", "kibitz"):
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

    create_task(coro(gamemodel, steps))
