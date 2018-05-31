import gc
import types

# from pychess.Utils.Board import Board
from pychess.Utils.GameModel import GameModel
# from pychess.Utils.lutils.LBoard import LBoard
from pychess.widgets.BoardView import BoardView
from pychess.widgets.BoardControl import BoardControl
from pychess.widgets.gamewidget import GameWidget
from pychess.widgets.pydock.PyDockTop import PyDockTop
from pychess.widgets.pydock.PyDockLeaf import PyDockLeaf
# from pychess.widgets.pydock.ArrowButton import ArrowButton
# from pychess.widgets.pydock.StarArrowButton import StarArrowButton
# from pychess.widgets.pydock.HighlightArea import HighlightArea
from pychess.Players.CECPEngine import CECPEngine
from pychess.Players.UCIEngine import UCIEngine
from pychess.Players.Human import Human
from pychess.Players.ICPlayer import ICPlayer
from pychess.ic.ICGameModel import ICGameModel
from pychess.ic import ICLogon
from pychess.perspectives import perspective_manager


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
    perspective = perspective_manager.get_perspective("games")
    if len(perspective.gamewidgets) > 0:
        return

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
        # TODO:
        # ArrowButton,
        # StarArrowButton,
        # HighlightArea,
        # Board,
        # LBoard,
    ):
        obj_referrers(klass)

    if ICLogon.dialog is None or not hasattr(ICLogon.dialog, "lounge"):
        for klass in (
            PyDockTop,
            PyDockLeaf,
        ):
            obj_referrers(klass)

    print("---------------------------------")


def print_muppy_sumary():
    # http://pythonhosted.org/Pympler/index.html
    try:
        from pympler import muppy, summary
    except ImportError:
        print("WARNING: pympler not installed")
        return
    # from pympler.classtracker import ClassTracker
    # from pympler.classtracker_stats import HtmlStats
    global all_objects, obj_summary, class_tracker
    if all_objects is None:
        all_objects = muppy.get_objects()
        obj_summary = summary.summarize(all_objects)
        summary.print_(obj_summary)

        # class_tracker = ClassTracker()
        # class_tracker.track_class(FICSPlayer, trace=1)
        # class_tracker.track_class(ICGameModel, resolution_level=2, trace=1)
    else:
        obj_summary2 = summary.summarize(muppy.get_objects())
        diff = summary.get_diff(obj_summary, obj_summary2)
        summary.print_(diff, limit=200)

        # class_tracker.create_snapshot('usage')
        # HtmlStats(tracker=class_tracker).create_html('profile.html')


all_objects = None
obj_summary = None
class_tracker = None
