import re

from pychess.Utils.Move import *
from pychess.Utils.const import *
from pychess.System.Log import log
from pychess.Utils.logic import getStatus
from pychess.Utils.Board import Board
from pychess.Variants.fischerandom import FischerRandomChess

from ChessFile import ChessFile, LoadingError

__label__ = _("Chess Game")
__endings__ = "pgn",
__append__ = True

def wrap (string, length):
    lines = []
    last = 0
    while True:
        if len(string)-last <= length:
            lines.append(string[last:])
            break
        i = string[last:length+last].rfind(" ")
        lines.append(string[last:i+last])
        last += i + 1
    return "\n".join(lines)

def save (file, model):
    
    status = reprResult[model.status]
    
    print >> file, '[Event "%s"]' % model.tags["Event"]
    print >> file, '[Site "%s"]' % model.tags["Site"]
    print >> file, '[Round "%d"]' % model.tags["Round"]
    print >> file, '[Date "%04d.%02d.%02d"]' % \
            (model.tags["Year"], model.tags["Month"], model.tags["Day"])
    print >> file, '[White "%s"]' % repr(model.players[WHITE])
    print >> file, '[Black "%s"]' % repr(model.players[BLACK])
    print >> file, '[Result "%s"]' % status

    if issubclass(model.variant, FischerRandomChess):
        print >> file, '[Variant "Fischerandom"]'
        
    if model.lowply > 0 or issubclass(model.variant, FischerRandomChess):
        print >> file, '[SetUp "1"]'
        print >> file, '[FEN "%s"]' % model.boards[0].asFen()
    
    print >> file
    
    result = []
    sanmvs = listToSan(model.boards[0], model.moves)
    for i in range(0, len(sanmvs)):
        ply = i + model.lowply
        if ply % 2 == 0:
            result.append("%d." % (ply/2+1))
        elif i == 0:
            result.append("%d..." % (ply/2+1))
        result.append(sanmvs[i])
    result = " ".join(result)
    result = wrap(result, 80)
    
    print >> file, result, status
    file.close()

def stripBrackets (string):
    brackets = 0
    end = 0
    result = ""
    for i, c in enumerate(string):
        if c == '(':
            if brackets == 0:
                result += string[end:i]
            brackets += 1
        elif c == ')':
            brackets -= 1
            if brackets == 0:
                end = i+1
    result += string[end:]
    return result


tagre = re.compile(r"\[([a-zA-Z]+)[ \t]+\"(.+?)\"\]")
movre = re.compile(r"([a-hxOoKQRBN0-8+#=-]{2,7})[\?!]*\s")
comre = re.compile(r"(?:\{.*?\})|(?:;.*?[\n\r])|(?:\$[0-9]+)", re.DOTALL)

def load (file):
    files = []
    inTags = False
    
    for line in file:
        line = line.lstrip()
        if not line: continue
        elif line.startswith("%"): continue
        
        if line.startswith("["):
            if not inTags:
                files.append(["",""])
                inTags = True
            files[-1][0] += line
        
        else:
            inTags = False
            if not files:
                # In rare cases there might not be any tags at all. It's not
                # legal, but we support it anyways.
                files.append(["",""])
            files[-1][1] += line
    
    return PGNFile (files)


class PGNFile (ChessFile):
    
    def __init__ (self, games):
        ChessFile.__init__(self, games)
        self.expect = None
        self.tagcache = {}
    
    def _getMoves (self, gameno):
        if not self.games:
            return []
        moves = comre.sub("", self.games[gameno][1])
        moves = stripBrackets(moves)
        moves = movre.findall(moves+" ")
        if moves and moves[-1] in ("*", "1/2-1/2", "1-0", "0-1"):
            del moves[-1]
        return moves
    
    def loadToModel (self, gameno, position, model=None):
        if not model: model = GameModel()

        variant = self._getTag(gameno, "Variant")
        if variant and ("fischer" in variant.lower() or "960" in variant):
            model.variant = FischerRandomChess
        
        fenstr = self._getTag(gameno, "FEN")
        if fenstr:
            model.boards = [Board(fenstr)]
        else:
            model.boards = [Board(setup=True)]

        del model.moves[:]
        model.status = WAITING_TO_START
        model.reason = UNKNOWN_REASON
        
        movstrs = self._getMoves (gameno)
        error = None
        for i, mstr in enumerate(movstrs):
            if position != -1 and model.ply >= position:
                break
            try:
                move = parseAny (model.boards[-1], mstr)
            except ParsingError, e:
                notation, reason, boardfen = e.args
                ply = model.boards[-1].ply
                if ply % 2 == 0:
                    moveno = "%d." % (i/2+1)
                else: moveno = "%d..." % (i/2+1)
                errstr1 = _("The game can't be read to end, because of an error parsing move %s '%s'.") % (moveno, notation)
                errstr2 = _("The move failed because %s.") % reason
                error = LoadingError (errstr1, errstr2)
                break
            model.moves.append(move)
            model.boards.append(model.boards[-1].move(move))
            
            # This is for the sidepanels
            model.emit("game_changed")
        
        if model.timemodel:
            blacks = len(movstrs)/2
            whites = len(movstrs)-blacks
            model.timemodel.intervals = [
                [model.timemodel.intervals[0][0]]*(whites+1),
                [model.timemodel.intervals[1][0]]*(blacks+1),
            ]
            log.debug("intervals %s" % model.timemodel.intervals)
        
        if model.status == WAITING_TO_START:
            model.status, model.reason = getStatus(model.boards[-1])
        
        if error:
            raise error
        
        return model
    
    def _getTag (self, gameno, tagkey):
        if gameno in self.tagcache:
            if tagkey in self.tagcache[gameno]:
                return self.tagcache[gameno][tagkey]
            else: return None
        else:
            if self.games:
                self.tagcache[gameno] = dict(tagre.findall(self.games[gameno][0]))
                return self._getTag(gameno, tagkey)
            else:
                return None
    
    def get_player_names (self, no):
        p1 = self._getTag(no,"White") and self._getTag(no,"White") or "Unknown"
        p2 = self._getTag(no,"Black") and self._getTag(no,"Black") or "Unknown"
        return (p1, p2)
    
    def get_elo (self, no):
        p1 = self._getTag(no,"WhiteElo") and self._getTag(no,"WhiteElo") or "1600"
        p2 = self._getTag(no,"BlackElo") and self._getTag(no,"BlackElo") or "1600"
        p1 = p1.isdigit() and int(p1) or 1600
        p2 = p2.isdigit() and int(p2) or 1600
        return (p1, p2)
    
    def get_date (self, no):
        date = self._getTag(no,"Date")
        today = datetime.date.today()
        if not date:
            return today.timetuple()[:3]
        return [ s.isdigit() and int(s) or today.timetuple()[i] \
                 for i,s in enumerate(date.split(".")) ]
    
    def get_site (self, no):
        return self._getTag(no,"Site") and self._getTag(no,"Site") or "?"
    
    def get_event (self, no):
        return self._getTag(no,"Event") and self._getTag(no,"Event") or "?"
    
    def get_round (self, no):
        round = self._getTag(no,"Round")
        if not round: return 1
        if round.find(".") >= 1:
            round = round[:round.find(".")]
        if not round.isdigit(): return 1
        return int(round)
        
    def get_result (self, no):
        pgn2Const = {"*":RUNNING, "1/2-1/2":DRAW, "1-0":WHITEWON, "0-1":BLACKWON}
        if self._getTag(no,"Result") in pgn2Const:
            return pgn2Const[self._getTag(no,"Result")]
        return RUNNING
