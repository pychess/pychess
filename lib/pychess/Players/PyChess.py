
import os
import random
import sys
from time import time

this_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.join(this_dir, "../..") not in sys.path:
    sys.path = [os.path.join(this_dir, "../..")] + sys.path

from pychess.Utils.book import getOpenings  # nopep8
from pychess.Utils.const import WHITE, ASEANCHESS, SITTUYINCHESS, ATOMICCHESS, reprResult, \
    CAMBODIANCHESS, LOSERSCHESS, KINGOFTHEHILLCHESS, DRAW, BLACKWON, WHITEWON, MAKRUKCHESS, \
    SUICIDECHESS, THREECHECKCHESS  # nopep8
from pychess.Utils.lutils import lsearch  # nopep8
from pychess.Utils.lutils.ldata import MAXPLY  # nopep8
from pychess.Utils.lutils.lsearch import alphaBeta  # nopep8
from pychess.Utils.lutils.lmove import listToSan, toSAN, toAN  # nopep8
from pychess.System.Log import log  # nopep8


# Make print() unbuffered and logged
class Unbuffered(object):
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        try:
            self.stream.write(data)
            self.stream.flush()
        except BrokenPipeError:
            log.debug("BrokenPipeError in Unbuffered print() !!!", extra={"task": "stdout"})
        log.debug(data, extra={"task": "stdout"})

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)


class PyChess(object):

    def __init__(self):
        self.sd = MAXPLY
        self.skipPruneChance = 0

        self.clock = [0, 0]
        self.increment = [0, 0]
        self.movestogo = 0
        self.searchtime = 0
        self.scr = 0  # The current predicted score. Used when accepting draw offers
        self.playingAs = WHITE
        self.ponder = False  # Currently unused
        self.post = False
        self.debug = True
        self.outOfBook = False

    # Play related

    def __remainingMovesA(self):
        # Based on regression of a 180k games pgn
        ply_count = self.board.plyCount
        return -1.71086e-12 * ply_count**6 \
            + 1.69103e-9 * ply_count**5 \
            - 6.00801e-7 * ply_count**4 \
            + 8.17741e-5 * ply_count**3 \
            + 2.91858e-4 * ply_count**2 \
            - 0.94497 * ply_count \
            + 78.8979

    def __remainingMovesB(self):
        # Classical timecontrol
        ply = self.board.plyCount % (self.movestogo * 2)
        remaining = self.movestogo - ply // 2
        print("# remaining moves=%s" % remaining)
        return remaining

    def __getBestOpening(self):
        totalWeight = 0
        choice = None
        if self.board.variant not in (ASEANCHESS, CAMBODIANCHESS, MAKRUKCHESS,
                                      SITTUYINCHESS, LOSERSCHESS, SUICIDECHESS,
                                      ATOMICCHESS, KINGOFTHEHILLCHESS, THREECHECKCHESS):
            for move, weight, learn in getOpenings(self.board):
                totalWeight += weight
                if totalWeight == 0:
                    break
                if not move or random.randrange(totalWeight) < weight:
                    choice = move
        if choice is None:
            self.outOfBook = True
        return choice

    def __go(self, ondone=None):
        """ Finds and prints the best move from the current position """

        # Don't allow openings (since it might prevent a capture)
        self.outOfBook = True
        
        mv = False if self.outOfBook else self.__getBestOpening()
        if mv:
            mvs = [mv]

        if not mv:

            lsearch.skipPruneChance = self.skipPruneChance
            lsearch.searching = True

            timed = self.basetime > 0

            if self.searchtime > 0:
                usetime = self.searchtime
            else:
                if self.movestogo > 0:
                    remaining_moves = self.__remainingMovesB()
                    usetime = self.clock[self.playingAs] / remaining_moves
                    if remaining_moves == 1:
                        usetime -= 0.05
                else:
                    usetime = self.clock[self.playingAs] / self.__remainingMovesA()
                    if self.clock[self.playingAs] > 10:
                        # If we have time, we assume 40 moves rather than 80
                        usetime *= 2
                    # The increment is a constant. We'll use this always
                    usetime += self.increment[self.playingAs]

            prevtime = 0
            starttime = time()
            lsearch.endtime = starttime + usetime if timed else sys.maxsize
            if self.debug:
                if timed:
                    print("# Time left: %3.2f s; Planing to think for %3.2f s" %
                          (self.clock[self.playingAs], usetime))
                else:
                    print("# Searching to depth %d without timelimit" % self.sd)

            for depth in range(1, self.sd + 1):
                # Heuristic time saving
                # Don't waste time, if the estimated isn't enough to complete
                # next depth
                if timed and usetime <= prevtime * 4 and usetime > 1:
                    break
                lsearch.timecheck_counter = lsearch.TIMECHECK_FREQ
                search_result = alphaBeta(self.board, depth)
                if lsearch.searching:
                    mvs, self.scr = search_result
                    if time() > lsearch.endtime:
                        break
                    if self.post:
                        pv1 = " ".join(listToSan(self.board, mvs))
                        time_cs = int(100 * (time() - starttime))
                        print("%s %s %s %s %s" % (
                            depth, self.scr, time_cs, lsearch.nodes, pv1))
                else:
                    # We were interrupted
                    if depth == 1:
                        mvs, self.scr = search_result
                    break
                prevtime = time() - starttime - prevtime

                self.clock[self.playingAs] -= time(
                ) - starttime - self.increment[self.playingAs]

            if not mvs:
                if not lsearch.searching:
                    # We were interupted
                    lsearch.nodes = 0
                    return

                # This should only happen in terminal mode

                if self.scr == 0:
                    print("result %s" % reprResult[DRAW])
                elif self.scr < 0:
                    if self.board.color == WHITE:
                        print("result %s" % reprResult[BLACKWON])
                    else:
                        print("result %s" % reprResult[WHITEWON])
                else:
                    if self.board.color == WHITE:
                        print("result %s" % reprResult[WHITEWON])
                    else:
                        print("result %s" % reprResult[BLACKWON])
                return

            lsearch.nodes = 0
            lsearch.searching = False

        move = mvs[0]
        sanmove = toSAN(self.board, move)
        if ondone:
            ondone(toAN(self.board, move))
        return sanmove

    def __analyze(self):
        """ Searches, and prints info from, the position as stated in the cecp
            protocol """

        start = time()
        lsearch.endtime = sys.maxsize
        lsearch.searching = True

        for depth in range(1, self.sd):
            if not lsearch.searching:
                break
            board = self.board.clone()
            mvs, scr = alphaBeta(board, depth)

            pv1 = " ".join(listToSan(board, mvs))
            time_cs = int(100 * (time() - start))
            print("%s %s %s %s %s" % (depth, scr, time_cs, lsearch.nodes, pv1))

            lsearch.nodes = 0


if __name__ == "__main__":
    import logging
    from pychess.Players.PyChessCECP import PyChessCECP
    if len(sys.argv) == 1 or sys.argv[1:] == ["debug"]:
        if "debug" in sys.argv[1:]:
            log.logger.setLevel(logging.DEBUG)
        else:
            log.logger.setLevel(logging.WARNING)

        pychess = PyChessCECP()
    else:
        print("Unknown argument(s):", repr(sys.argv))
        sys.exit(0)

    pychess.makeReady()
    pychess.run()
