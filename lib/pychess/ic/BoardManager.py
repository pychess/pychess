
import re
from gobject import *

from pychess.Utils.const import *
import telnet
from ICManager import ICManager

names = "(\w+)(?:\(([CUHIFWM])\))?"
# FIXME: What about names like: Nemisis(SR)(CA)(TM) and Rebecca(*)(SR)(TD) ?
types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
ratings = "\(([0-9\ \-\+]{4})\)"
sanmove = "([a-hxOoKQRBN0-8+#=-]{2,7})"

fileToEpcord = (("a3","b3","c3","d3","e3","f3","g3","h3"),
                ("a6","b6","c6","d6","e6","f6","g6","h6"))

relations = { "-3": IC_POS_ISOLATED,
              "-2": IC_POS_OBSERVING_EXAMINATION,
               "2": IC_POS_EXAMINATING,
              "-1": IC_POS_OP_TO_MOVE,
               "1": IC_POS_ME_TO_MOVE,
               "0": IC_POS_OBSERVING }

class BoardManager (ICManager):
    
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
    
    def start (self):
        self.observeQueue = {}
        # activeItem is the gameno of the observed game of which we are
        # currently parsing the history
        self.activeItem = None
        # playedItem is the gameno of the game in which we are currenly taking
        # part
        self.playedItem = None
        
        print >> telnet.client, "style 12"
        print >> telnet.client, "iset startpos 1"
        print >> telnet.client, "iset gameinfo 1"
        print >> telnet.client, "iset compressmove 1"
    
    def __init__ (self):
        ICManager.__init__(self)
        
        telnet.expect ( "<12>(.*?)\n", self.onStyle12 )
        telnet.expect ( "<d1>(.*?)\n", self.onMove )
        
        telnet.expect (
            "Creating: %s %s %s %s %s %s (\d+) (\d+)\n\r{Game (\d+)\s" % \
            (names, ratings, names, ratings, rated, types),
            self.playBoardCreated)
        
        telnet.expect (
            "Game (\d+): %s %s %s %s %s %s (\d+) (\d+)" % \
            (names, ratings, names, ratings, rated, types),
            self.observeBoardCreated)
        
        telnet.expect (
            "\s*(\d+)\.\s*%s\s+\(\d+:\d+\)\s+?(?:%s\s+\(\d+:\d+\)\s*)?\n" % \
            (sanmove, sanmove), self.moveLine)
        
        telnet.expect ( "      {Still in progress} *", self.moveListEnd)
        
        telnet.expect (
            "{Game (\d+) \(\w+ vs\. \w+\) (.*?)} ([\d/]{1,3}\-[\d/]{1,3}|\*)\n",
            self.onGameEnd)
        
        telnet.expect (
            "\rGame (\d+): Game clock (paused|resumed).\n", self.onGamePause)
    
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
    
    def onStyle12 (self, client, groups):
        groups = groups[0].split()
        
        curcol = groups[8] == "B" and BLACK or WHITE
        gameno = groups[15]
        relation = relations[groups[18]]
        
        # Board data
        fen = "".join(map(self._style12ToFenRow, groups[:8]))
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
        if self.activeItem == gameno:
            for key in self.observeQueue[self.activeItem]["moves"]:
                if key > ply+1:
                    del self.observeQueue[self.activeItem]["moves"][key]
            self.observeQueue[self.activeItem]["queue"].append(f)
        else:
            f()
    
    def onMove (self, client, groups):
        gameno, curply, sanmove, _, _, remainingMs = groups[0].split()[:6]
        moveply = int(curply)-1
        
        if self.activeItem == gameno:
            self.observeQueue[self.activeItem]["moves"][moveply] = sanmove
        else:
            movecolor = moveply % 2 == 1 and BLACK or WHITE
            self.emit("moveRecieved", moveply, sanmove, gameno, movecolor)
            self.emit("clockUpdatedMs", gameno, int(remainingMs), movecolor)
    
    def playBoardCreated (self, client, groups):
        wname, wtit, wrat, bname, btit, brat, rt, type, min, incr, gmno = groups
        board = {"wname": wname, "wtitle": wtit, "wrating": wrat,
                 "bname": bname, "btitle": btit, "brating": brat,
                 "rated": rt, "type": type, "mins": min, "incr": incr,
                 "gameno": gmno}
        self.playedItem = gmno
        self.emit("playBoardCreated", board)
    
    def observeBoardCreated (self, client, groups):
        gameno = groups[0]
        item = {"general": groups, "moves": {}, "queue":[]}
        self.observeQueue[gameno] = item
        if not self.activeItem:
            self.activeItem = gameno
            print >> telnet.client, "moves", gameno
    
    def moveLine (self, client, groups):
        if not self.activeItem: return
        moveno, wmove, bmove = groups
        ply = int(moveno)*2-2
        self.observeQueue[self.activeItem]["moves"][ply] = wmove
        if bmove:
            self.observeQueue[self.activeItem]["moves"][ply+1] = bmove
    
    def moveListEnd (self, client, nothing):
        if not self.activeItem: return
        stuf = self.observeQueue[self.activeItem]["general"]
        gmno, wnam, wtit, wrat, bnam, btit, brat, rated, type, mins, incr = stuf
        ficsHeaders = ( ("Event", "Ficsgame"), ("Site", "Internet"),
                ("White", wnam), ("Black", bnam),
                ("WhiteElo", wrat), ("BlackElo", brat) )
        pgn = "\n".join (['[%s "%s"]' % keyvalue for keyvalue in ficsHeaders])
        pgn += "\n"
        
        moves = self.observeQueue[self.activeItem]["moves"].items()
        moves.sort()
        for ply, move in moves:
            if ply % 2 == 0:
                pgn += "%d. " % (ply/2+1)
            pgn += move + " "
        pgn += "\n"
        
        if wtit:           wnam += "(%s)" % wtit
        if wrat.isdigit(): wnam += " %s" % wrat
        if btit:           bnam += "(%s)" % btit
        if brat.isdigit(): bnam += " %s" % brat

        self.emit ("observeBoardCreated", gmno, pgn,
                   int(mins)*60, int(incr), wnam, bnam)
        
        for function in self.observeQueue[self.activeItem]["queue"]:
            function()
        
        del self.observeQueue[self.activeItem]
        self.activeItem = None
        
        if self.observeQueue:
            self.activeItem = self.observeQueue.keys()[0]
            print >> telnet.client, "moves", self.activeItem
    
    def onGameEnd (self, client, groups):
        gameno, comment, state = groups
        
        parts = comment.split()
        if parts[0] in ("Creating", "Continuing"):
            return
        
        if state in ("1-0", "0-1"):
            if state == "1-0":
                status = WHITEWON
            else:
                status = BLACKWON
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
        elif state == "1/2-1/2":
            status = DRAW
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
            status = ADJOURNED
            if "connection" in parts:
                reason = ADJOURNED_LOST_CONNECTION
            elif "agreement" in parts:
                reason = ADJOURNED_AGREEMENT
            elif "shutdown" in parts:
                reason = ADJOURNED_SERVER_SHUTDOWN
            else:
                reason = UNKNOWN_REASON
        elif "aborted" in parts:
            status = ABORTED
            if "agreement" in parts:
                reason = ABORTED_AGREEMENT
            elif "move" in parts:
                # Game aborted on move 1 *
                reason = ABORTED_EARLY
            elif "moves" in parts:
                # lost connection and too few moves; game aborted *
                reason = ABORTED_EARLY
            elif "shutdown" in parts:
                reason = ABORTED_SERVER_SHUTDOWN
            elif "adjudication" in parts:
                reason = ABORTED_ADJUDICATION
            else:
                reason = UNKNOWN_REASON
        elif "courtesyaborted" in parts:
            status = ABORTED
            reason = ABORTED_COURTESY
        else:
            status = UNKNOWN_STATE
            reason = UNKNOWN_REASON
        
        if gameno == self.playedItem:
            self.emit("curGameEnded", gameno, status, reason)
        else:
            f = lambda: self.emit("obsGameEnded", gameno, status, reason)
            if self.activeItem == gameno:
                self.observeQueue[self.activeItem]["queue"].append(f)
            else:
                f()
    
    def onGamePause (self, client, groups):
        gameno, state = groups
        f = lambda: self.emit("gamePaused", gameno, state=="paused")
        if self.activeItem == gameno:
            self.observeQueue[self.activeItem]["queue"].append(f)
        else:
            f()
    
    ############################################################################
    #   Interacting                                                            #
    ############################################################################
    
    def sendMove (self, move):
        print >> telnet.client, move
    
    def resign (self):
        print >> telnet.client, "resign"
    
    def callflag (self):
        print >> telnet.client, "flag"
    
    def observe (self, gameno):
        print >> telnet.client, "observe", gameno
    
    def unobserve (self, gameno):
        print >> telnet.client, "unobserve", gameno
        self.emit("obsGameUnobserved", gameno)
    
    def play (self, seekno):
        print >> telnet.client, "play", seekno
    
    def accept (self, offerno):
        print >> telnet.client, "accept", offerno
    
    def decline (self, offerno):
        print >> telnet.client, "decline", offerno


bm = BoardManager()
