
import telnet
from gobject import *
from pychess.Utils.const import *

names = "(\w+)(?:\(([CUHIFWM])\))?"
types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
ratings = "\(([\d\+\-]{1,4})\)"
sanmove = "([a-hxOoKQRBN0-8+#=-]{2,7})"

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
        'playBoardCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'observeBoardCreated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,str,int,int)),
        'moveRecieved' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,str,str,int)),
        'clockUpdated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,int,int)),
        'gameEnded' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,int,int))
    }
    
    def __init__ (self):
        GObject.__init__(self)
        
        self.observeQueue = []
        self.currentBoard = None
        
        print >> telnet.client, "style 12"
        
        telnet.expect ( "<12>(.*?)\n", self.onStyle12 )
        
        telnet.expect ( "Creating: %s %s %s %s %s %s (\d+) (\d+)" % (names, ratings, names, ratings, rated, types), self.playBoardCreated)
        
        telnet.expect ( "Game (\d+): %s %s %s %s %s %s (\d+) (\d+)" % (names, ratings, names, ratings, rated, types), self.observeBoardCreated)
        
        telnet.expect ("\s*(\d+)\.\s*%s\s+\(\d+:\d+\)\s+?(?:%s\s+\(\d+:\d+\)\s*)?\n" % (sanmove, sanmove), self.moveLine)
        
        telnet.expect ( "      {Still in progress} *", self.moveListEnd)
        
        telnet.expect ( "{Game (\d+) \(\w+ vs\. \w+\) (.*?)} ([\d/]{1,3}\-[\d/]{1,3})\n", self.onGameEnd)
    
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
        
        if not relation in (IC_POS_OBSERVING, IC_POS_ME_TO_MOVE):
            return
        
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
        
        # Emit
        if sanmove != "none":
            if self.currentBoard and self.currentBoard["groups"][0] == gameno:
                ply = int(moveno)*2-2
                # We have to subtract 1, as the movenumber of style 12 descripes
                # the move to be played next and not the move just made
                ply -= 1 
                if curcol == BLACK: ply += 1
                self.currentBoard["moves"][ply] = sanmove
            self.emit("moveRecieved", fen, sanmove, gameno, 1-curcol)
        
        # Clock update
        whiteRemainSecs = int(groups[23])
        blackRemainSecs = int(groups[24])
        self.emit ("clockUpdated", gameno, whiteRemainSecs, blackRemainSecs)
    
    def playBoardCreated (self, client, groups):
        wname, wtit, wrat, bname, btit, brat, rated, type, mins, incr = groups
        board = {"wname": wname, "wtitle": wtit, "wrating": wrat,
                 "bname": bname, "btitle": btit, "brating": brat,
                 "rated": rated, "type": type, "mins": mins, "incr": incr}
        self.emit("playBoardCreated", board)
    
    def observeBoardCreated (self, client, groups):
        if not self.currentBoard:
            self.currentBoard = {"groups": groups, "moves": {}}
            print >> telnet.client, "moves", groups[0]
        else:
            self.observeQueue.append(groups)
    
    def moveLine (self, client, groups):
        moveno, wmove, bmove = groups
        ply = int(moveno)*2-2
        self.currentBoard["moves"][ply] = wmove
        if bmove: 
            self.currentBoard["moves"][ply+1] = bmove
    
    def moveListEnd (self, client, nothing):
        grps = self.currentBoard["groups"]
        gmno, wnam, wtit, wrat, bnam, btit, brat, rated, type, mins, incr = grps
        ficsHeaders = ( ("Event", "Ficsgame"), ("Site", "Internet"),
                ("White", wnam), ("Black", bnam),
                ("WhiteElo", wrat), ("BlackElo", brat) )
        pgn = "\n".join (['[%s "%s"]' % keyvalue for keyvalue in ficsHeaders])
        pgn += "\n"
        
        moves = self.currentBoard["moves"].items()
        moves.sort()
        for ply, move in moves:
            if ply % 2 == 0:
                pgn += "%d. " % (ply/2+1)
            pgn += move + " "
        pgn += "\n"
        
        self.emit ("observeBoardCreated", gmno, pgn, int(mins)*60, int(incr))
        
        self.currentBoard = None
        if self.observeQueue:
            self.currentBoard = {"groups": self.observeQueue.pop(), "moves": {}}
            print >> telnet.client, "moves", self.currentBoard["groups"][0]
    
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
            else:
                reason = UNKNOWN_REASON
        elif "adjourned" in parts:
            status = ADJOURNED
            if "connection" in parts:
                reason = ADJOURNED_LOST_CONNECTION
            elif "agreement" in parts:
                reason = ADJOURNED_AGREEMENT
            else:
                reason = UNKNOWN_REASON
        elif "aborted" in parts:
            status = ABORTED
            reason = REASON_ABORTED
        else:
            status = UNKNOWN_STATE
            reason = UNKNOWN_REASON
        
        self.emit("gameEnded", gameno, status, reason)
    
    ############################################################################
    #   Interacting                                                            #
    ############################################################################
    
    def sendMove (self, move):
        print >> telnet.client, move
    
    def resign (self):
        print >> telnet.client, "resign"
    
    def observe (self, gameno):
        print >> telnet.client, "observe", gameno
    
    def unobserve (self, gameno):
        print >> telnet.client, "unobserve", gameno
