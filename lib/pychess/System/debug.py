import gc
import sys
import time
import types
import traceback
import threading
from threading import Thread

from pychess.System import fident
from pychess.System.Log import log

from pychess.Utils.Board import Board
from pychess.Utils.GameModel import GameModel
from pychess.Utils.lutils.LBoard import LBoard
from pychess.widgets.BoardView import BoardView
from pychess.widgets.BoardControl import BoardControl
from pychess.widgets.gamewidget import GameWidget
from pychess.Players.CECPEngine import CECPEngine
from pychess.Players.UCIEngine import UCIEngine
from pychess.Players.Human import Human
from pychess.Players.ICPlayer import ICPlayer
from pychess.ic.ICGameModel import ICGameModel


def dump_threads():
    # This may cause random crashes
    # https://github.com/pychess/pychess/issues/1023
    stacks = []
    for thread in threading.enumerate():
        frame = sys._current_frames()[thread.ident]
        stack = traceback.format_list(traceback.extract_stack(frame))
        stacks.append("Thread: %s (%d)" % (thread.name, thread.ident))
        stacks.append("".join(stack))

    log.debug("\n" + "\n".join(stacks))


def start_thread_dump():
    def thread_dumper():
        while True:
            dump_threads()
            time.sleep(10)

    thread = Thread(target=thread_dumper, name=fident(thread_dumper))
    thread.daemon = True
    thread.start()


def obj_referrers(klass):
    find_obj = False
    for obj in gc.get_objects():
        # closures are evil !
        if isinstance(obj, types.FunctionType) and obj.__closure__ is not None:
            for c in obj.__closure__:
                try:
                    if isinstance(c.cell_contents, klass):
                        print('!!!', obj, c.cell_contents)
                except ValueError:
                    print("Cell is empty...")
        if isinstance(obj, klass):
            find_obj = True
            rs = gc.get_referrers(obj)
            print("---------------------------referrers of %s" % klass.__name__)
            for ob in rs:
                print(type(ob), ob.__name__ if type(ob) is type else repr(ob)[:140])
                rs1 = gc.get_referrers(ob)
                for ob1 in rs1:
                    print('    ', type(ob1), ob1.__name__ if type(ob1) is type else repr(ob1)[:140])
            print("---------------------------")
    if not find_obj:
        print("Nothing refrences %s" % klass.__name__)


def print_obj_referrers():
    for klass in (
        ICGameModel,
        GameModel,
        GameWidget,
        BoardView,
        BoardControl,
        CECPEngine,
        UCIEngine,
        Human,
        ICPlayer,
        # Board,
        # LBoard,
    ):
        obj_referrers(klass)
