
import re
from gobject import *

from pychess.System.Log import log
from pychess.Utils.const import *

from pychess.ic.VerboseTelnet import *

names = "(\w+)(?:\(([CUHIFWM])\))?"
# FIXME: What about names like: Nemisis(SR)(CA)(TM) and Rebecca(*)(SR)(TD) ?
types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
ratings = "\(([0-9\ \-\+]{4}|UNR)\)"
sanmove = "([a-hxOoKQRBN0-8+#=-]{2,7})"

moveListNames = re.compile("%s %s vs. %s %s --- .*" %
        (names, ratings, names, ratings))

moveListOther = re.compile(
        "%s %s match, initial time: (\d+) minutes, increment: (\d+) seconds\." %
        (rated, types), re.IGNORECASE)

moveListMoves = re.compile("(\d+)\. +%s +\(\d+:\d+\) *(?:%s +\(\d+:\d+\))?" %
        (sanmove, sanmove))

fileToEpcord = (("a3","b3","c3","d3","e3","f3","g3","h3"),
                ("a6","b6","c6","d6","e6","f6","g6","h6"))

relations = { "-3": IC_POS_ISOLATED,
              "-2": IC_POS_OBSERVING_EXAMINATION,
               "2": IC_POS_EXAMINATING,
              "-1": IC_POS_OP_TO_MOVE,
               "1": IC_POS_ME_TO_MOVE,
               "0": IC_POS_OBSERVING }

class BoardManager (GObject):
    
    __gsignals__ = {
        'playBoardCreated'    : (SIGNAL_RUN_FIRST, None, (object,)),
        'observeBoardCreated' : (SIGNAL_RUN_FIRST, None, (str, str, int, int, str, str)),
        'moveRecieved'        : (SIGNAL_RUN_FIRST, None, (str, str, str, int)),
        'boardRecieved'       : (SIGNAL_RUN_FIRST, None, (str, int, str, int, int)),
        'clockUpdatedMs'      : (SIGNAL_RUN_FIRST, None, (str, int, int)),
        'obsGameEnded'        : (SIGNAL_RUN_FIRST, None, (str, int, int)),
        'curGameEnded'        : (SIGNAL_RUN_FIRST, None, (str, int, int)),
        'obsGameUnobserved'   : (SIGNAL_RUN_FIRST, None, (str,)),
        'gamePaused'          : (SIGNAL_RUN_FIRST, None, (str, bool))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect_line (self.onStyle12, "<12>\s*(.+)")
        self.connection.expect_line (self.onMove, "<d1>\s*(.+)")
        
        self.connection.expect_fromto (self.playBoardCreated,
                "Creating: %s %s %s %s %s %s (\d+) (\d+)" %
                    (names, ratings, names, ratings, rated, types),
                "{Game (\d+)\s")
        
        self.connection.expect_fromto (self.onObservedGame,
            "Movelist for game (\d+):", "{Still in progress} \*")
        
        self.connection.glm.connect("removeGame", self.onGameEnd)
        
        self.connection.expect_line (self.onGamePause,
                "Game (\d+): Game clock (paused|resumed).")
        
        self.queuedMoves = {}
        self.queuedCalls = {}
        self.ourGameno = ""
        
        self.connection.lvm.setVariable("style", "12")
        self.connection.lvm.setVariable("startpos", True)
        # gameinfo <g1> doesn't really have any interesting info, at least not
        # until we implement crasyhouse and stuff
        # self.connection.lvm.setVariable("gameinfo", True)
        self.connection.lvm.setVariable("compressmove", True)
    
    def _style12ToFenRow (self, row):
        fenrow = []
        spaceCounter = 0
        for c in row:
            if c == "-":
                spaceCounter += 1
            else:
                if spaceCounter:
                    fenrow.append(str(spaceCounter))
                    spaceCounter = 0
                fenrow.append(c)
        return "".join(fenrow)
    
    def onStyle12 (self, match):
        groups = match.groups()[0].split()
        
        curcol = groups[8] == "B" and BLACK or WHITE
        gameno = groups[15]
        relation = relations[groups[18]]
        
        # Board data
        fen = "/".join(map(self._style12ToFenRow, groups[:8]))
        fen += " "
        
        # Current color
        fen += groups[8].lower()
        fen += " "
        
        # Castling
        if groups[10:14] == ["0","0","0","0"]:
            fen += "-"
        else:
            if groups[10] == "1":
                fen += "K"
            if groups[11] == "1":
                fen += "Q"
            if groups[12] == "1":
                fen += "k"
            if groups[13] == "1":
                fen += "q"
        fen += " "
        
        # En passant
        if groups[9] == "-1":
            fen += "-"
        else:
            fen += fileToEpcord [1-curcol] [int(groups[9])]
        fen += " "
        
        # Half move clock
        fen += str(int(groups[14])-1)
        fen += " "
        
        # Standard chess numbering
        moveno = groups[25]
        fen += moveno
        
        # San move
        sanmove = groups[28]
        
        # Names
        wname = groups[16]
        bname = groups[17]
        
        # Clock update
        wsec = int(groups[23])
        bsec = int(groups[24])
        
        # Ply
        ply = int(moveno)*2-2
        if curcol == BLACK: ply += 1
        
        # Emit
        f = lambda: self.emit("boardRecieved", gameno, ply, fen, wsec, bsec)
        if gameno in self.queuedMoves:
            for moveply in self.queuedMoves[gameno].keys():
                if moveply > ply+1:
                    del self.queuedMoves[gameno][moveply]
            self.queuedCalls[gameno].append(f)
        else:
            f()
    
    def onMove (self, match):
        gameno, curply, sanmove, _, _, remainingMs = match.groups()[0].split()[:6]
        moveply = int(curply)-1
        
        if gameno in self.queuedMoves:
            self.queuedMoves[moveply] = sanmove
        else:
            movecolor = moveply % 2 == 1 and BLACK or WHITE
            self.emit("moveRecieved", moveply, sanmove, gameno, movecolor)
            self.emit("clockUpdatedMs", gameno, int(remainingMs), movecolor)
    
    def playBoardCreated (self, matchlist):
        gameno = matchlist[1].groups()[0]
        wname, wtit, wrat, bname, btit, brat, rt, type, min, incr = \
                matchlist[0].groups()
        board = {"wname": wname, "wtitle": wtit, "wrating": wrat,
                 "bname": bname, "btitle": btit, "brating": brat,
                 "rated": rt, "type": type, "mins": min, "incr": incr,
                 "gameno": gameno}
        self.ourGameno = gameno
        self.emit("playBoardCreated", board)
    
    def onObservedGame (self, matchlist):
        
        # Get info from match
        gameno = matchlist[0].groups()[0]
        
        whitename, whitetitle, whiterating, blackname, blacktitle, blackrating = \
                moveListNames.match(matchlist[2]).groups()
        
        rated, type, minutes, increment = \
                moveListOther.match(matchlist[3]).groups()
        
        moves = self.queuedMoves[gameno]
        for moveline in matchlist[7:-1]:
            if not moveListMoves.match(moveline):
                log.error("Line %s could not be mathed by regexp" % moveline)
            moveno, wmove, bmove = moveListMoves.match(moveline).groups()
            ply = int(moveno)*2-2
            moves[ply] = wmove
            if bmove:
                moves[ply+1] = bmove
        
        # Create game
        pgnHead = [
            ("Event", "Ficsgame"),
            ("Site", "Internet"),
            ("White", whitename),
            ("Black", blackname)
        ]
        if whiterating not in ("0", "UNR"):
            pgnHead.append(("WhiteElo", whiterating))
        if blackrating not in ("0", "UNR"):
            pgnHead.append(("BlackElo", blackrating))
        
        pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n"
        
        moves = moves.items()
        moves.sort()
        for ply, move in moves:
            if ply % 2 == 0:
                pgn += "%d. " % (ply/2+1)
            pgn += move + " "
        pgn += "\n"
        
        self.emit ("observeBoardCreated", gameno, pgn,
                   int(minutes)*60, int(increment), whitename, blackname)
        
        for function in self.queuedCalls[gameno]:
            function()
        
        del self.queuedMoves[gameno]
        del self.queuedCalls[gameno]
    
    def onGameEnd (self, glm, gameno, result, comment):
        parts = set(re.findall("\w+",comment))
        if result in (WHITEWON, BLACKWON):
            if "resigns" in parts:
                reason = WON_RESIGN
            elif "disconnection" in parts:
                reason = WON_DISCONNECTION
            elif "time" in parts:
                reason = WON_CALLFLAG
            elif "checkmated" in parts:
                reason = WON_MATE
            elif "adjudication" in parts:
                reason = WON_ADJUDICATION
            else:
                reason = UNKNOWN_REASON
        elif result == DRAW:
            if "repetition" in parts:
                reason = DRAW_REPITITION
            if "material" in parts:
                reason = DRAW_INSUFFICIENT
            elif "time" in parts:
                reason = DRAW_CALLFLAG
            elif "agreement" in parts:
                reason = DRAW_AGREE
            elif "stalemate" in parts:
                reason = DRAW_STALEMATE
            elif "50" in parts:
                reason = DRAW_50MOVES
            elif "length" in parts:
                # FICS has a max game length on 800 moves
                reason = DRAW_LENGTH
            elif "adjudication" in parts:
                reason = DRAW_ADJUDICATION
            else:
                reason = UNKNOWN_REASON
        elif "adjourned" in parts:
            result = ADJOURNED
            if "connection" in parts:
                reason = ADJOURNED_LOST_CONNECTION
            elif "agreement" in parts:
                reason = ADJOURNED_AGREEMENT
            elif "shutdown" in parts:
                reason = ADJOURNED_SERVER_SHUTDOWN
            else:
                reason = UNKNOWN_REASON
        elif "aborted" in parts:
            result = ABORTED
            if "agreement" in parts:
                reason = ABORTED_AGREEMENT
            elif "moves" in parts:
                # lost connection and too few moves; game aborted *
                reason = ABORTED_EARLY
            elif "move" in parts:
                # Game aborted on move 1 *
                reason = ABORTED_EARLY
            elif "shutdown" in parts:
                reason = ABORTED_SERVER_SHUTDOWN
            elif "adjudication" in parts:
                reason = ABORTED_ADJUDICATION
            else:
                reason = UNKNOWN_REASON
        elif "courtesyaborted" in parts:
            result = ABORTED
            reason = ABORTED_COURTESY
        else:
            result = UNKNOWN_STATE
            reason = UNKNOWN_REASON
        
        if gameno == self.ourGameno:
            self.emit("curGameEnded", gameno, result, reason)
        else:
            f = lambda: self.emit("obsGameEnded", gameno, result, reason)
            if gameno in self.queuedCalls:
                log.debug("added observed game ended to queue")
                self.queuedCalls[gameno].append(f)
            else:
                f()
    
    def onGamePause (self, match):
        gameno, state = match.groups()
        f = lambda: self.emit("gamePaused", gameno, state=="paused")
        if gameno in self.queuedCalls:
            self.queuedCalls[gameno].append(f)
        else:
            f()
    
    ############################################################################
    #   Interacting                                                            #
    ############################################################################
    
    def sendMove (self, move):
        print >> self.connection.client, move
    
    def resign (self):
        print >> self.connection.client, "resign"
    
    def callflag (self):
        print >> self.connection.client, "flag"
    
    def observe (self, gameno):
        print >> self.connection.client, "observe %s" % gameno
        print >> self.connection.client, "moves %s" % gameno
        self.queuedMoves[gameno] = {}
        self.queuedCalls[gameno] = []
    
    def unobserve (self, gameno):
        print >> self.connection.client, "unobserve %s" % gameno
        self.emit("obsGameUnobserved", gameno)
    
    def play (self, seekno):
        print >> self.connection.client, "play %s" % seekno
    
    def accept (self, offerno):
        print >> self.connection.client, "accept %s" % offerno
    
    def decline (self, offerno):
        print >> self.connection.client, "decline %s" % offerno
