
import re
from gobject import *
import threading

from pychess.System.Log import log
from pychess.Utils.const import *
from GameListManager import strToVariant, unsupportedWilds

from pychess.ic.VerboseTelnet import *

names = "(\w+)"
titles = "((?:\((?:GM|IM|FM|WGM|WIM|TM|SR|TD|SR|CA|C|U|D|B|T|\*)\))+)?"
ratedexp = "(rated|unrated)"
ratings = "\(([-0-9 +]+|UNR)\)"
sanmove = "([a-hxOoKQRBN0-8+#=-]{2,7})"

moveListNames = re.compile("%s %s vs. %s %s --- .*" %
        (names, ratings, names, ratings))

moveListOther = re.compile(
        "%s ([^ ]+) match, initial time: (\d+) minutes, increment: (\d+) seconds\." %
        ratedexp, re.IGNORECASE)

moveListMoves = re.compile("(\d+)\. +(?:%s|\.\.\.) +\(\d+:[\d\.]+\) *(?:%s +\(\d+:[\d\.]+\))?" %
        (sanmove, sanmove))

fileToEpcord = (("a3","b3","c3","d3","e3","f3","g3","h3"),
                ("a6","b6","c6","d6","e6","f6","g6","h6"))

relations = { "-4": IC_POS_INITIAL,
              "-3": IC_POS_ISOLATED,
              "-2": IC_POS_OBSERVING_EXAMINATION,
               "2": IC_POS_EXAMINATING,
              "-1": IC_POS_OP_TO_MOVE,
               "1": IC_POS_ME_TO_MOVE,
               "0": IC_POS_OBSERVING }

# TODO: Fischer and other wild
#Creating: Lobais (----) GuestGFDC (++++) unrated wild/fr 2 12
#{Game 155 (Lobais vs. GuestGFDC) Creating unrated wild/fr match.}

#<12> bqrknbnr pppppppp -------- -------- -------- -------- PPPPPPPP BQRKNBNR W -1 1 1 1 1 0 155 Lobais GuestGFDC 1 2 12 39 39 120 120 1 none (0:00) none 0 0 0

class BoardManager (GObject):
    
    __gsignals__ = {
        'playBoardCreated'    : (SIGNAL_RUN_FIRST, None, (object,)),
        'observeBoardCreated' : (SIGNAL_RUN_FIRST, None, (object,)),
        'wasPrivate'          : (SIGNAL_RUN_FIRST, None, (str,)),
        'boardUpdate'         : (SIGNAL_RUN_FIRST, None, (str, int, int, str, str, str, str, int, int)),
        'obsGameEnded'        : (SIGNAL_RUN_FIRST, None, (str, str, str, int, int)),
        'curGameEnded'        : (SIGNAL_RUN_FIRST, None, (str, str, str, int, int)),
        'obsGameUnobserved'   : (SIGNAL_RUN_FIRST, None, (str,)),
        'gamePaused'          : (SIGNAL_RUN_FIRST, None, (str, bool))
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect_line (self.onStyle12, "<12> (.+)")
        
        self.connection.expect_line (self.onWasPrivate,
                "Sorry, game (\d+) is a private game\.")
        
        self.connection.expect_n_lines (self.playBoardCreated,
            "Creating: %s %s %s %s %s ([^ ]+) (\d+) (\d+)(?: \(adjourned\))?"
            % (names, ratings, names, ratings, ratedexp),
            "{Game (\d+) \(%s vs\. %s\) (?:Creating|Continuing) %s ([^ ]+) match\."
            % (names, names, ratedexp),
            "", "<12> (.+)")
        
        self.connection.expect_fromto (self.onObservedGame,
            "Movelist for game (\d+):", "{Still in progress} \*")
        
        self.connection.glm.connect("removeGame", self.onGameEnd)
        
        self.connection.expect_line (self.onGamePause,
                "Game (\d+): Game clock (paused|resumed)\.")
        
        self.connection.expect_line (self.onUnobserveGame,
                "Removing game (\d+) from observation list\.")
        
        self.queuedStyle12s = {}
        self.queuedEmits = {}
        self.gamemodelStartedEvents = {}
        self.ourGameno = ""
        self.castleSigns = {}
        
        # The ms ivar makes the remaining second fields in style12 use ms
        self.connection.lvm.setVariable("ms", True)
        # Style12 is a must, when you don't want to parse visualoptimized stuff
        self.connection.lvm.setVariable("style", "12")
        # When we observe fischer games, this puts a startpos in the movelist
        self.connection.lvm.setVariable("startpos", True)
        # movecase ensures that bc3 will never be a bishop move
        self.connection.lvm.setVariable("movecase", True)
        # don't unobserve games when we start a new game
        self.connection.lvm.setVariable("unobserve", "3")
        self.connection.lvm.setVariable("formula", "")
        
        # gameinfo <g1> doesn't really have any interesting info, at least not
        # until we implement crasyhouse and stuff
        # self.connection.lvm.setVariable("gameinfo", True)
        
        # We don't use deltamoves as fisc won't send them with variants
        #self.connection.lvm.setVariable("compressmove", True)
    
    def __parseStyle12 (self, line, castleSigns=None):
        fields = line.split()
        
        curcol = fields[8] == "B" and BLACK or WHITE
        gameno = fields[15]
        relation = relations[fields[18]]
        ply = int(fields[25])*2 - (curcol == WHITE and 2 or 1)
        lastmove = fields[28] != "none" and fields[28] or None
        wname = fields[16]
        bname = fields[17]
        wms = int(fields[23])
        bms = int(fields[24])
        gain = int(fields[20])
        
        # Board data
        fenrows = []
        for row in fields[:8]:
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
            if spaceCounter:
                fenrow.append(str(spaceCounter))
            fenrows.append("".join(fenrow))
        
        fen = "/".join(fenrows)
        fen += " "
        
        # Current color
        fen += fields[8].lower()
        fen += " "
        
        # Castling
        if fields[10:14] == ["0","0","0","0"]:
            fen += "-"
        else:
            if fields[10] == "1":
                fen += castleSigns[0].upper()
            if fields[11] == "1":
                fen += castleSigns[1].upper()
            if fields[12] == "1":
                fen += castleSigns[0].lower()
            if fields[13] == "1":
                fen += castleSigns[1].lower()
        fen += " "
        # 1 0 1 1 when short castling k1 last possibility
        
        # En passant
        if fields[9] == "-1":
            fen += "-"
        else:
            fen += fileToEpcord [1-curcol] [int(fields[9])]
        fen += " "
        
        # Half move clock
        fen += str(max(int(fields[14]),0))
        fen += " "
        
        # Standard chess numbering
        fen += fields[25]
        
        return gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen
    
    def onStyle12 (self, match):
        style12 = match.groups()[0]
        gameno = style12.split()[15]
        
        if gameno in self.queuedStyle12s:
            self.queuedStyle12s[gameno].append(style12)
            return
        
        if self.gamemodelStartedEvents.has_key(gameno):
            self.gamemodelStartedEvents[gameno].wait()
        
        castleSigns = self.castleSigns[gameno]
        gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
                self.__parseStyle12(style12, castleSigns)
        self.emit("boardUpdate", gameno, ply, curcol, lastmove, fen, wname, bname, wms, bms)
    
    def onGameModelStarted (self, gameno):
        self.gamemodelStartedEvents[gameno].set()
    
    def onWasPrivate (self, match):
        gameno, = match.groups()
        self.emit("wasPrivate", gameno)
    
    def __parseType (self, type):
        if type in strToVariant.keys():
            variant = strToVariant[type]
        elif type in unsupportedWilds.keys():
            raise RuntimeError, "We don't support %s yet :X" % type
        else:
            variant = NORMALCHESS
        return variant
    
    def __generateCastleSigns (self, style12, variant):
        if variant == FISCHERRANDOMCHESS:
            backrow = style12.split()[0]
            leftside = backrow.find("r")
            rightside = backrow.find("r", leftside+1)
            return (reprFile[rightside], reprFile[leftside])
        else:
            return ("k", "q")
    
    def parseDigits(self, rating):
        if rating:
            m = re.match("[0-9]+", rating)
            if m: return m.group(0)
            else: return None
        else: return None
    
    def playBoardCreated (self, matchlist):
        
        wname, wrating, bname, brating, rated, type, min, inc = matchlist[0].groups()
        gameno, wname, bname, rated, type = matchlist[1].groups()
        style12 = matchlist[-1].groups()[0]
        
        rated = rated == "rated"
        variant = self.__parseType(type)
        castleSigns = self.__generateCastleSigns(style12, variant)
        
        self.castleSigns[gameno] = castleSigns
        gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
                self.__parseStyle12(style12, castleSigns)
        
        board = {"wname": wname, "wrating": self.parseDigits(wrating),
                 "bname": bname, "brating": self.parseDigits(brating),
                 "rated": rated, "wms": wms, "bms":bms, "gain": gain,
                 "gameno": gameno, "variant":variant, "fen": fen}
        self.ourGameno = gameno
        self.gamemodelStartedEvents[gameno] = threading.Event()
        self.gamemodelStartedEvents[gameno].clear()
        self.emit("playBoardCreated", board)
    
    def onObservedGame (self, matchlist):
        
        # Get info from match
        gameno = matchlist[0].groups()[0]
        
        wname, wrating, bname, brating = \
                moveListNames.match(matchlist[2]).groups()
        
        rated, type, minutes, increment = \
                moveListOther.match(matchlist[3]).groups()
        
        variant = self.__parseType(type)
        
        if matchlist[5].startswith("<12>"):
            style12 = matchlist[5][5:]
            castleSigns = self.__generateCastleSigns(style12, variant)
            gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
                    self.__parseStyle12(style12, castleSigns)
            initialfen = fen
            movesstart = 9
        else:
            castleSigns = ("k", "q")
            initialfen = None
            movesstart = 7
        
        self.castleSigns[gameno] = castleSigns
        
        moves = {}
        for moveline in matchlist[movesstart:-1]:
            match = moveListMoves.match(moveline)
            if not match:
                log.error("Line %s could not be macthed by regexp" % moveline)
                continue
            moveno, wmove, bmove = match.groups()
            ply = int(moveno)*2-2
            if wmove:
                moves[ply] = wmove
            if bmove:
                moves[ply+1] = bmove
        
        # Apply queued board updates
        for style12 in self.queuedStyle12s[gameno]:
            gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
                    self.__parseStyle12(style12, castleSigns)
            if lastmove == None:
                continue
            moves[ply-1] = lastmove
            # Updated the queuedMoves in case there has been a takeback
            for moveply in moves.keys():
                if moveply > ply-1:
                    del moves[moveply]
                
        # Create game
        pgnHead = [
            ("Event", "Ficsgame"),
            ("Site", "Internet"),
            ("White", wname),
            ("Black", bname)
        ]
        if initialfen:
            pgnHead += [
                ("SetUp", "1"),
                ("FEN", initialfen)
            ]
            if variant == FISCHERRANDOMCHESS:
                pgnHead += [("Variant", "Fischerandom")]
        
        if wrating not in ("0", "UNR", "----"):
            pgnHead.append(("WhiteElo", wrating))
        if brating not in ("0", "UNR", "----"):
            pgnHead.append(("BlackElo", brating))
        
        pgn = "\n".join(['[%s "%s"]' % line for line in pgnHead]) + "\n"
        
        moves = moves.items()
        moves.sort()
        for ply, move in moves:
            if ply % 2 == 0:
                pgn += "%d. " % (ply/2+1)
            pgn += move + " "
        pgn += "\n"
        
        if gameno in self.queuedStyle12s:
            style12 = self.queuedStyle12s[gameno][-1]
            gameno, relation, curcol, ply, wname, bname, wms, bms, gain, lastmove, fen = \
                    self.__parseStyle12(style12, castleSigns)
        else:
            wms = bms = int(minutes)*60*1000
            gain = int(increment)
        del self.queuedStyle12s[gameno]
        
        board = {"wname": wname, "wrating": self.parseDigits(wrating),
                 "bname": bname, "brating": self.parseDigits(brating),
                 "rated": rated.lower()=="rated",
                 "wms": wms, "bms":bms, "gain": gain,
                 "gameno": gameno, "variant":variant, "pgn": pgn}
        
        self.emit ("observeBoardCreated", board)
        
        if gameno in self.gamemodelStartedEvents:
            self.gamemodelStartedEvents[gameno].wait()
        for emit in self.queuedEmits[gameno]:
            emit()        
        del self.queuedEmits[gameno]
        
    def onGameEnd (self, glm, gameno, wname, bname, result, comment):
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
            elif "material" in parts and "time" in parts:
                if re.search(wname + " ran out of time", comment, re.IGNORECASE):
                    reason = DRAW_BLACKINSUFFICIENTANDWHITETIME
                else:
                    reason = DRAW_WHITEINSUFFICIENTANDBLACKTIME
            elif "material" in parts:
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
        elif "courtesyadjourned" in parts:
            result = ADJOURNED
            reason = ADJOURNED_COURTESY
        elif "courtesyaborted" in parts:
            result = ABORTED
            reason = ABORTED_COURTESY
        else:
            result = UNKNOWN_STATE
            reason = UNKNOWN_REASON
        
        if gameno == self.ourGameno:
            if gameno in self.gamemodelStartedEvents:
                self.gamemodelStartedEvents[gameno].wait()
            self.emit("curGameEnded", gameno, wname, bname, result, reason)
            self.ourGameno = ""
            del self.gamemodelStartedEvents[gameno]
        else:
            if gameno in self.queuedEmits:
                self.queuedEmits[gameno].append(lambda:self.emit("obsGameEnded", gameno, wname, bname, result, reason))
            elif gameno in self.gamemodelStartedEvents:
                self.gamemodelStartedEvents[gameno].wait()
                self.emit("obsGameEnded", gameno, wname, bname, result, reason)
    
    def onGamePause (self, match):
        gameno, state = match.groups()
        if gameno in self.queuedEmits:
            self.queuedEmits[gameno].append(lambda:self.emit("gamePaused", gameno, state=="paused"))
        else:
            if gameno in self.gamemodelStartedEvents:
                self.gamemodelStartedEvents[gameno].wait()
            self.emit("gamePaused", gameno, state=="paused")
    
    def onUnobserveGame (self, match):
        gameno, = match.groups()
        del self.gamemodelStartedEvents[gameno]
        self.emit("obsGameUnobserved", gameno)
    
    ############################################################################
    #   Interacting                                                            #
    ############################################################################
    
    def isPlaying (self):
        return bool(self.ourGameno)
    
    def sendMove (self, move):
        print >> self.connection.client, move
    
    def resign (self):
        print >> self.connection.client, "resign"
    
    def callflag (self):
        print >> self.connection.client, "flag"
    
    def observe (self, gameno):
        if not gameno in self.gamemodelStartedEvents:
            self.queuedStyle12s[gameno] = []
            self.queuedEmits[gameno] = []
            self.gamemodelStartedEvents[gameno] = threading.Event()
            self.gamemodelStartedEvents[gameno].clear()
            print >> self.connection.client, "observe %s" % gameno
            print >> self.connection.client, "moves %s" % gameno
    
    def unobserve (self, gameno):
        print >> self.connection.client, "unobserve %s" % gameno
    
    def play (self, seekno):
        print >> self.connection.client, "play %s" % seekno
    
    def accept (self, offerno):
        print >> self.connection.client, "accept %s" % offerno
    
    def decline (self, offerno):
        print >> self.connection.client, "decline %s" % offerno

if __name__ == "__main__":
    from pychess.ic.FICSConnection import Connection
    con = Connection("","","","")
    bm = BoardManager(con)
    
    print bm._BoardManager__parseStyle12("rkbrnqnb pppppppp -------- -------- -------- -------- PPPPPPPP RKBRNQNB W -1 1 1 1 1 0 161 GuestNPFS GuestMZZK -1 2 12 39 39 120 120 1 none (0:00) none 1 0 0",
                                         ("d","a"))
    
    print bm._BoardManager__parseStyle12("rnbqkbnr pppp-ppp -------- ----p--- ----PP-- -------- PPPP--PP RNBQKBNR B 5 1 1 1 1 0 241 GuestGFFC GuestNXMP -4 2 12 39 39 120000 120000 1 none (0:00.000) none 0 0 0",
                                         ("k","q"))
    
    