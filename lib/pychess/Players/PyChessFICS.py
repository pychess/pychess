from __future__ import print_function

import sys
import email.utils
import math
import random
import signal
import subprocess
from threading import Thread

from gi.repository import Gtk, Gdk
import pychess
from pychess.compat import urlopen, urlencode
from pychess.Players.PyChess import PyChess
from pychess.System.repeat import repeat_sleep
from pychess.System import fident
from pychess.System.Log import log
from pychess.Utils.const import WHITE, PAUSE_OFFER, DRAW_OFFER, BLACK, RESUME_OFFER, \
    TAKEBACK_OFFER, ABORT_OFFER, ADJOURN_OFFER, SWITCH_OFFER, NORMALCHESS, SAN
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import determineAlgebraicNotation, toLAN, parseSAN
from pychess.Utils.lutils import lsearch
from pychess.Utils.repr import reprResult_long, reprReason_long
from pychess.ic.FICSConnection import FICSMainConnection


class PyChessFICS(PyChess):
    def __init__(self, password, from_address, to_address):
        PyChess.__init__(self)

        self.ports = (23, 5000)
        if not password:
            self.username = "guest"
        else:
            self.username = "PyChess"
        self.owner = "Lobais"
        self.password = password
        self.from_address = "The PyChess Bot <%s>" % from_address
        self.to_address = "Thomas Dybdahl Ahle <%s>" % to_address

        # Possible start times
        self.minutes = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        self.gains = (0, 5, 10, 15, 20)
        # Possible colors. None == random
        self.colors = (WHITE, BLACK, None)
        # The amount of random challenges, that PyChess sends with each seek
        self.challenges = 10
        # enableEGTB()

        self.sudos = set()
        self.ownerOnline = False
        self.waitingForPassword = None
        self.log = []
        self.acceptedTimesettings = []

        self.worker = None

        repeat_sleep(self.sendChallenges, 60 * 1)

    def __triangular(self, low, high, mode):
        """Triangular distribution.
        Continuous distribution bounded by given lower and upper limits,
        and having a given mode value in-between.
        http://en.wikipedia.org/wiki/Triangular_distribution
        """
        random_num = random.random()
        mid = (mode - low) / (high - low)
        if random_num > mid:
            random_num = 1 - random_num
            mid = 1 - mid
            low, high = high, low
        tri = low + (high - low) * (random_num * mid)**0.5
        if tri < mode:
            return int(tri)
        elif tri > mode:
            return int(math.ceil(tri))
        return int(round(tri))

    def sendChallenges(self):
        if self.connection.bm.isPlaying():
            return True

        statsbased = ((0.39197722779282, 3, 0), (0.59341408108783, 5, 0),
                      (0.77320877377846, 1, 0), (0.8246379941394, 10, 0),
                      (0.87388717406441, 2, 12), (0.91443760169489, 15, 0),
                      (0.9286423058163, 4, 0), (0.93891977227793, 2, 0),
                      (0.94674539138335, 20, 0), (0.95321476842423, 2, 2),
                      (0.9594588808257, 5, 2), (0.96564528079889, 3, 2),
                      (0.97173859621034, 7, 0), (0.97774906636184, 3, 1),
                      (0.98357243654425, 5, 12), (0.98881309737017, 5, 5),
                      (0.99319644938247, 6, 0), (0.99675879556023, 3, 12),
                      (1, 5, 3))

        # n = random.random()
        # for culminativeChance, minute, gain in statsbased:
        #    if n < culminativeChance:
        #        break

        culminativeChance, minute, gain = random.choice(statsbased)

        # type = random.choice((TYPE_LIGHTNING, TYPE_BLITZ, TYPE_STANDARD))
        # if type == TYPE_LIGHTNING:
        #    minute = self.__triangular(0,2+1,1)
        #    mingain = not minute and 1 or 0
        #    maxgain = int((3-minute)*3/2)
        #    gain = random.randint(mingain, maxgain)
        # elif type == TYPE_BLITZ:
        #    minute = self.__triangular(0,14+1,5)
        #    mingain = max(int((3-minute)*3/2+1), 0)
        #    maxgain = int((15-minute)*3/2)
        #    gain = random.randint(mingain, maxgain)
        # elif type == TYPE_STANDARD:
        #    minute = self.__triangular(0,20+1,12)
        #    mingain = max(int((15-minute)*3/2+1), 0)
        #    maxgain = int((20-minute)*3/2)
        #    gain = self.__triangular(mingain, maxgain, mingain)

        # color = random.choice(self.colors)
        self.extendlog(["Seeking %d %d" % (minute, gain)])
        self.connection.glm.seek(minute, gain, True)
        opps = random.sample(self.connection.players.get_online_playernames(),
                             self.challenges)
        self.extendlog("Challenging %s" % op for op in opps)
        for player in opps:
            self.connection.om.challenge(player, minute, gain, True)

        return True

    def makeReady(self):
        signal.signal(signal.SIGINT, Gtk.main_quit)

        PyChess.makeReady(self)

        self.connection = FICSMainConnection("freechess.org", self.ports,
                                             self.username, self.password)
        self.connection.connect("connectingMsg", self.__showConnectLog)
        self.connection._connect()

        self.connection.glm.connect("addPlayer", self.__onAddPlayer)
        self.connection.glm.connect("removePlayer", self.__onRemovePlayer)
        self.connection.cm.connect("privateMessage", self.__onTell)
        self.connection.alm.connect("logOut", self.__onLogOut)
        self.connection.bm.connect("playGameCreated", self.__onGameCreated)
        self.connection.bm.connect("curGameEnded", self.__onGameEnded)
        self.connection.bm.connect("boardUpdate", self.__onBoardUpdate)
        self.connection.om.connect("onChallengeAdd", self.__onChallengeAdd)
        self.connection.om.connect("onOfferAdd", self.__onOfferAdd)
        self.connection.adm.connect("onAdjournmentsList",
                                    self.__onAdjournmentsList)
        self.connection.em.connect("onAmbiguousMove", self.__onAmbiguousMove)
        self.connection.em.connect("onIllegalMove", self.__onAmbiguousMove)

        self.connection.adm.queryAdjournments()
        self.connection.lvm.setVariable("autoflag", 1)

        self.connection.fm.setFingerNote(
            1, "PyChess is the chess engine bundled with the PyChess %s " %
            pychess.VERSION +
            "chess client. This instance is owned by %s, but acts " %
            self.owner + "quite autonomously.")

        self.connection.fm.setFingerNote(
            2,
            "PyChess is 100% Python code and is released under the terms of " +
            "the GPL. The evalution function is largely equal to the one of" +
            "GnuChess, but it plays quite differently.")

        self.connection.fm.setFingerNote(
            3,
            "PyChess runs on an elderly AMD Sempron(tm) Processor 3200+, 512 " +
            "MB DDR2 Ram, but is built to take use of 64bit calculating when " +
            "accessible, through the gpm library.")

        self.connection.fm.setFingerNote(
            4,
            "PyChess uses a small 500 KB openingbook based solely on Kasparov " +
            "games. The engine doesn't have much endgame knowledge, but might " +
            "in some cases access an online endgamedatabase.")

        self.connection.fm.setFingerNote(
            5,
            "PyChess will allow any pause/resume and adjourn wishes, but will " +
            "deny takebacks. Draw, abort and switch offers are accepted, " +
            "if they are found to be an advance. Flag is auto called, but " +
            "PyChess never resigns. We don't want you to forget your basic " +
            "mating skills.")

    def main(self):
        self.connection.run()
        self.extendlog([str(self.acceptedTimesettings)])
        self.phoneHome("Session ended\n" + "\n".join(self.log))
        print("Session ended")

    def run(self):
        t = Thread(target=self.main, name=fident(self.main))
        t.daemon = True
        t.start()
        Gdk.threads_init()
        Gtk.main()

    # General

    def __showConnectLog(self, connection, message):
        print(message)

    def __onLogOut(self, autoLogoutManager):
        self.connection.close()
        # sys.exit()

    def __onAddPlayer(self, gameListManager, player):
        if player["name"] in self.sudos:
            self.sudos.remove(player["name"])
        if player["name"] == self.owner:
            self.connection.cm.tellPlayer(self.owner, "Greetings")
            self.ownerOnline = True

    def __onRemovePlayer(self, gameListManager, playername):
        if playername == self.owner:
            self.ownerOnline = False

    def __onAdjournmentsList(self, adjournManager, adjournments):
        for adjournment in adjournments:
            if adjournment["online"]:
                adjournManager.challenge(adjournment["opponent"])

    def __usage(self):
        return "|| PyChess bot help file || " +\
               "# help 'Displays this help file' " +\
               "# sudo <password> <command> 'Lets PyChess execute the given command' " +\
               "# sendlog 'Makes PyChess send you its current log'"

    def __onTell(self, chatManager, name, title, isadmin, text):

        if self.waitingForPassword:
            if text.strip() == self.password or (not self.password and
                                                 text == "none"):
                self.sudos.add(name)
                self.tellHome("%s gained sudo access" % name)
                self.connection.client.run_command(self.waitingForPassword)
            else:
                chatManager.tellPlayer(name, "Wrong password")
                self.tellHome("%s failed sudo access" % name)
            self.waitingForPassword = None
            return

        args = text.split()

        # if args == ["help"]:
        #    chatManager.tellPlayer(name, self.__usage())

        if args[0] == "sudo":
            command = " ".join(args[1:])
            if name in self.sudos or name == self.owner:
                # Notice: This can be used to make nasty loops
                print(command, file=self.connection.client)
            else:
                print(repr(name), self.sudos)
                chatManager.tellPlayer(name, "Please send me the password")
                self.waitingForPassword = command

        elif args == ["sendlog"]:
            if self.log:
                # TODO: Consider email
                chatManager.tellPlayer(name, "\\n".join(self.log))
            else:
                chatManager.tellPlayer(name, "The log is currently empty")

        else:
            if self.ownerOnline:
                self.tellHome("%s told me '%s'" % (name, text))
            else:

                def onlineanswer(message):
                    data = urlopen(
                        "http://www.pandorabots.com/pandora/talk?botid=8d034368fe360895",
                        urlencode({"message": message,
                                   "botcust2": "x"}).encode("utf-8")).read().decode('utf-8')
                    bold_ss = "<b>DMPGirl:</b>"
                    break_es = "<br>"
                    answer = data[data.find(bold_ss) + len(bold_ss):data.find(
                        break_es, data.find(bold_ss))]
                    chatManager.tellPlayer(name, answer)

                thread = Thread(target=onlineanswer,
                                name=fident(onlineanswer),
                                args=(text, ))
                thread.daemon = True
                thread.start()
            # chatManager.tellPlayer(name, "Sorry, your request was nonsense.\n"+\
            # "Please read my help file for more info")

            # Challenges and other offers

    def __onChallengeAdd(self, offerManager, index, match):
        # match = {"tp": type, "w": fname, "rt": rating, "color": color,
        #         "r": rated, "t": mins, "i": incr}
        offerManager.acceptIndex(index)

    def __onOfferAdd(self, offerManager, offer):
        if offer.type in (PAUSE_OFFER, RESUME_OFFER, ADJOURN_OFFER):
            offerManager.accept(offer)
        elif offer.type in (TAKEBACK_OFFER, ):
            offerManager.decline(offer)
        elif offer.type in (DRAW_OFFER, ABORT_OFFER, SWITCH_OFFER):
            if self.__willingToDraw():
                offerManager.accept(offer)
            else:
                offerManager.decline(offer)

    # Playing

    def __onGameCreated(self, boardManager, ficsgame):

        base = int(ficsgame.minutes) * 60
        inc = int(ficsgame.inc)
        self.clock[:] = base, base
        self.increment[:] = inc, inc
        self.gameno = ficsgame.gameno
        self.lastPly = -1

        self.acceptedTimesettings.append((base, inc))

        self.tellHome(
            "Starting a game (%s, %s) gameno: %s" %
            (ficsgame.wplayer.name, ficsgame.bplayer.name, ficsgame.gameno))

        if ficsgame.bplayer.name.lower() == self.connection.getUsername(
        ).lower():
            self.playingAs = BLACK
        else:
            self.playingAs = WHITE

        self.board = LBoard(NORMALCHESS)
        # Now we wait until we receive the board.

    def __go(self):
        if self.worker:
            self.worker.cancel()
        # TODO: fix it
        # self.worker = GtkWorker(
        #     lambda worker: PyChess._PyChess__go(self, worker))
        # self.worker.connect("published", lambda w, msg: self.extendlog(msg))
        # self.worker.connect("done", self.__onMoveCalculated)
        # self.worker.execute()

    def __willingToDraw(self):
        return self.scr <= 0  # FIXME: this misbehaves in all but the simplest use cases

    def __onGameEnded(self, boardManager, ficsgame):
        self.tellHome(reprResult_long[ficsgame.result] + " " + reprReason_long[
            ficsgame.reason])
        lsearch.searching = False
        if self.worker:
            self.worker.cancel()
            self.worker = None

    def __onMoveCalculated(self, worker, sanmove):
        if worker.isCancelled() or not sanmove:
            return
        self.board.applyMove(parseSAN(self.board, sanmove))
        self.connection.bm.sendMove(sanmove)
        self.extendlog(["Move sent %s" % sanmove])

    def __onBoardUpdate(self, boardManager, gameno, ply, curcol, lastmove, fen,
                        wname, bname, wms, bms):
        self.extendlog(["", "I got move %d %s for gameno %s" % (ply, lastmove,
                                                                gameno)])

        if self.gameno != gameno:
            return

        self.board.applyFen(fen)

        self.clock[:] = wms / 1000., bms / 1000.

        if curcol == self.playingAs:
            self.__go()

    def __onAmbiguousMove(self, errorManager, move):
        # This is really a fix for fics, but sometimes it is necessary
        if determineAlgebraicNotation(move) == SAN:
            self.board.popMove()
            move_ = parseSAN(self.board, move)
            lanmove = toLAN(self.board, move_)
            self.board.applyMove(move_)
            self.connection.bm.sendMove(lanmove)
        else:
            self.connection.cm.tellOpponent(
                "I'm sorry, I wanted to move %s, but FICS called " % move +
                "it 'Ambigious'. I can't find another way to express it, " +
                "so you can win")
            self.connection.bm.resign()

    # Utils

    def extendlog(self, messages):
        [log.info(m + "\n") for m in messages]
        self.log.extend(messages)
        del self.log[:-10]

    def tellHome(self, message):
        print(message)
        if self.ownerOnline:
            self.connection.cm.tellPlayer(self.owner, message)

    def phoneHome(self, message):

        SENDMAIL = '/usr/sbin/sendmail'
        SUBJECT = "Besked fra botten"

        pipe = subprocess.Popen(
            [SENDMAIL, '-f', email.utils.parseaddr(self.from_address)[1],
             email.utils.parseaddr(self.to_address)[1]],
            stdin=subprocess.PIPE)

        print("MIME-Version: 1.0", file=pipe.stdin)
        print("Content-Type: text/plain; charset=UTF-8", file=pipe.stdin)
        print("Content-Disposition: inline", file=pipe.stdin)
        print("From: %s" % self.from_address, file=pipe.stdin)
        print("To: %s" % self.to_address, file=pipe.stdin)
        print("Subject: %s" % SUBJECT, file=pipe.stdin)
        print(file=pipe.stdin)
        print(message, file=pipe.stdin)
        print("Cheers", file=pipe.stdin)

        pipe.stdin.close()
        pipe.wait()


if __name__ == "__main__":

    if len(sys.argv) == 5 and sys.argv[1] == "fics":
        pychess_fics = PyChessFICS(*sys.argv[2:])
    else:
        print("Unknown argument(s):", repr(sys.argv))
        sys.exit(0)

    pychess_fics.makeReady()
    pychess_fics.run()
