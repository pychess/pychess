# -*- coding: UTF-8 -*-

import re
from datetime import date

from pychess.System.Log import log
from pychess.Utils.Board import Board
from pychess.Utils.GameModel import GameModel
from pychess.Utils.Move import parseAny, toSAN, Move
from pychess.Utils.const import *
from pychess.Utils.logic import getStatus
from pychess.Utils.lutils.lmove import ParsingError
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

def msToClockTimeTag (ms):
    """ 
    Converts milliseconds to a chess clock time string in 'WhiteClock'/
    'BlackClock' PGN header format
    """
    msec = ms % 1000
    sec = ((ms - msec) % (1000 * 60)) / 1000
    min = ((ms - sec*1000 - msec) % (1000*60*60)) / (1000*60)
    hour = ((ms - min*1000*60 - sec*1000 - msec) % (1000*60*60*24)) / (1000*60*60)
    return "%01d:%02d:%02d.%03d" % (hour, min, sec, msec)

def parseClockTimeTag (tag):
    """ 
    Parses 'WhiteClock'/'BlackClock' PGN headers and returns the time the
    player playing that color has left on their clock in milliseconds
    """
    match = re.match("(\d{1,2}).(\d\d).(\d\d).(\d\d\d)", tag)
    if match:
        hour, min, sec, msec = match.groups()
        return int(msec) + int(sec)*1000 + int(min)*60*1000 + int(hour)*60*60*1000
    
def save (file, model):

    status = reprResult[model.status]

    print >> file, '[Event "%s"]' % model.tags["Event"]
    print >> file, '[Site "%s"]' % model.tags["Site"]
    print >> file, '[Date "%04d.%02d.%02d"]' % \
        (int(model.tags["Year"]), int(model.tags["Month"]), int(model.tags["Day"]))
    print >> file, '[Round "%s"]' % model.tags["Round"]
    print >> file, '[White "%s"]' % repr(model.players[WHITE])
    print >> file, '[Black "%s"]' % repr(model.players[BLACK])
    print >> file, '[Result "%s"]' % status
    if "ECO" in model.tags:
        print >> file, '[ECO "%s"]' % model.tags["ECO"]
    if "WhiteElo" in model.tags:
        print >> file, '[WhiteElo "%s"]' % model.tags["WhiteElo"]
    if "BlackElo" in model.tags:
        print >> file, '[BlackElo "%s"]' % model.tags["BlackElo"]
    if "TimeControl" in model.tags:
        print >> file, '[TimeControl "%s"]' % model.tags["TimeControl"]
    if "Time" in model.tags:
        print >> file, '[Time "%s"]' % str(model.tags["Time"])
    if model.timemodel:
        print >> file, '[WhiteClock "%s"]' % \
            msToClockTimeTag(int(model.timemodel.getPlayerTime(WHITE) * 1000))
        print >> file, '[BlackClock "%s"]' % \
            msToClockTimeTag(int(model.timemodel.getPlayerTime(BLACK) * 1000))
    if issubclass(model.variant, FischerRandomChess):
        print >> file, '[Variant "Fischerandom"]'
    if model.boards[0].asFen() != FEN_START:
        print >> file, '[SetUp "1"]'
        print >> file, '[FEN "%s"]' % model.boards[0].asFen()
    print >> file, '[PlyCount "%s"]' % (model.ply-model.lowply)
    if "EventDate" in model.tags:
        print >> file, '[EventDate "%s"]' % model.tags["EventDate"]
    if "Annotator" in model.tags:
        print >> file, '[Annotator "%s"]' % model.tags["Annotator"]
    print >> file

    result = []
    walk(model.boards[0], result)
            
    result = " ".join(result)
    result = wrap(result, 80)
    print >> file, result, status
    file.close()

def walk(node, result):
    def store(text):
        if len(result) > 1 and result[-1] == "(":
            result[-1] = "(%s" % text
        elif text == ")":
            result[-1] = "%s)" % result[-1]
        else:
            result.append(text)

    while True: 
        if node is None:
            break
        
        # Initial game or variation comment
        if node.prev is None:
            for child in node.children:
                if isinstance(child, basestring):
                    store("{%s}" % child)
            node = node.next
            continue

        move = Move(node.board.history[-1][0])
        movestr = toSAN(node.prev, move)
        if node.movecount:
            store(node.movecount)
        store(movestr)

        for nag in node.nags:
            if nag:
                store(nag)

        for child in node.children:
            if isinstance(child, basestring):
                # comment
                store("{%s}" % child)
            else:
                # variations
                store("(")
                walk(child[0], result)
                store(")")

        if node.next:
            node = node.next
        else:
            break

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


tagre = re.compile(r"\[([a-zA-Z]+)[ \t]+\"(.*?)\"\]")
comre = re.compile(r"(?:\{.*?\})|(?:;.*?[\n\r])|(?:\$[0-9]+)", re.DOTALL)
movre = re.compile(r"""
    (                   # group start
    (?:                 # non grouping parenthesis start
    [KQRBN]?            # piece
    [a-h]?[1-8]?        # unambiguous column or line
    x?                  # capture
    [a-h][1-8]          # destination square
    =?[QRBN]?           # promotion
    |O\-O(?:\-O)?       # castling
    |0\-0(?:\-0)?       # castling
    )                   # non grouping parenthesis end
    [+#]?               # check/mate
    )                   # group end
    [\?!]*              # traditional suffix annotations
    \s*                 # any whitespace
    """, re.VERBOSE)

# token categories
COMMENT_REST, COMMENT_BRACE, COMMENT_NAG, \
VARIATION_START, VARIATION_END, \
RESULT, FULL_MOVE, MOVE_COUNT, MOVE, MOVE_COMMENT = range(1,11)

pattern = re.compile(r"""
    (\;.*?[\n\r])        # comment, rest of line style
    |(\{.*?\})           # comment, between {} 
    |(\$[0-9]+)          # comment, Numeric Annotation Glyph
    |(\()                # variation start
    |(\))                # variation end
    |(\*|1-0|0-1|1/2)    # result (spec requires 1/2-1/2 for draw, but we want to tolerate simple 1/2 too)
    |(
    ([0-9]{1,3}\s*[.]*\s*)?
    ([a-hxOoKQRBN1-8+#=]{2,7}
    |O\-O(?:\-O)?
    |0\-0(?:\-0)?)
    ([\?!]{1,2})*
    )    # move (full, count, move with ?!, ?!)
    """, re.VERBOSE | re.DOTALL)


def load (file):
    files = []
    inTags = False

    for line in file:
        line = line.lstrip()
        if not line: continue
        elif line.startswith("%"): continue

        if line.startswith("["):
            if tagre.match(line) is not None:
                if not inTags:
                    files.append(["",""])
                    inTags = True
                files[-1][0] += line.decode("latin_1")
            else:
                if not inTags:
                    files[-1][1] += line.decode('latin_1')
                else:
                    print "Warning: ignored invalid tag pair %s" % line
        else:
            inTags = False
            if not files:
                # In rare cases there might not be any tags at all. It's not
                # legal, but we support it anyways.
                files.append(["",""])
            files[-1][1] += line.decode('latin_1')
                
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
    
    def loadToModel (self, gameno, position=-1, model=None, quick_parse=True):
        if not model:
            model = GameModel()

        # the seven mandatory PGN headers
        model.tags['Event'] = self._getTag(gameno, 'Event')
        model.tags['Site'] = self._getTag(gameno, 'Site')
        model.tags['Date'] = self._getTag(gameno, 'Date')
        model.tags['Round'] = self.get_round(gameno)
        model.tags['White'], model.tags['Black'] = self.get_player_names(gameno)
        model.tags['Result'] = reprResult[self.get_result(gameno)]
        
        pgnHasYearMonthDay = True
        for tag in ('Year', 'Month', 'Day'):
            if not self._getTag(gameno, tag):
                pgnHasYearMonthDay = False
                break
        if model.tags['Date'] and not pgnHasYearMonthDay:
            date_match = re.match(".*(\d{4}).(\d{2}).(\d{2}).*", model.tags['Date'])
            if date_match:
                year, month, day = date_match.groups()
                model.tags['Year'] = year
                model.tags['Month'] = month
                model.tags['Day'] = day
                
        # non-mandatory headers
        for tag in ('Annotator', 'ECO', 'EventDate', 'Time', 'WhiteElo', 'BlackElo', 'TimeControl'):
            if self._getTag(gameno, tag):
                model.tags[tag] = self._getTag(gameno, tag)
        
        # TODO: enable this when NewGameDialog is altered to give user option of
        # whether to use PGN's clock time, or their own custom time. Also,
        # dialog should set+insensitize variant based on the variant of the
        # game selected in the dialog
#        if model.timemodel:
#            for tag, color in (('WhiteClock', WHITE), ('BlackClock', BLACK)):
#                if self._getTag(gameno, tag):
#                    try:
#                        ms = parseClockTimeTag(self._getTag(gameno, tag))
#                        model.timemodel.intervals[color][0] = ms / 1000
#                    except ValueError: 
#                        raise LoadingError( \
#                            "Error parsing '%s' Header for gameno %s" % (tag, gameno))
#            if model.tags['TimeControl']:
#                minutes, gain = parseTimeControlTag(model.tags['TimeControl'])
#                model.timemodel.minutes = minutes
#                model.timemodel.gain = gain
        
        fenstr = self._getTag(gameno, "FEN")
        if self.get_variant(gameno):
            from pychess.Variants.fischerandom import FRCBoard
            model.variant = FischerRandomChess
            model.boards = [FRCBoard(fenstr)]
        else:
            if fenstr:
                model.boards = [Board(fenstr)]
            else:
                model.boards = [Board(setup=True)]

        del model.moves[:]
        del model.variations[:]
        
        error = None
        if quick_parse:
            movstrs = self._getMoves (gameno)
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
                    errstr1 = _("The game can't be read to end, because of an error parsing move %(moveno)s '%(notation)s'.") % {
                                'moveno': moveno, 'notation': notation}
                    errstr2 = _("The move failed because %s.") % reason
                    error = LoadingError (errstr1, errstr2)
                    break
                model.moves.append(move)
                model.boards.append(model.boards[-1].move(move))
        else:
            movetext = self.get_movetext(gameno)
            model.boards = self.parse_string(movetext, model, model.boards[-1], position)
            
            def walk(node, path):
                if node.next is None:
                    model.variations.append(path+[node])
                else:
                    walk(node.next, path+[node])

                if node.children: 
                    for child in node.children:
                        if isinstance(child, list):
                            if len(child) > 1:
                                walk(child[1], list(path))
            
            # Collect all variation paths into a list of board lists
            # where the first one will be the boards of mainline game.
            # model.boards will allways point to the current shown variation
            # which will be model.variations[0] when we are in the mainline.
            walk(model.boards[0], [])

        if model.timemodel:
            if quick_parse:
                blacks = len(movstrs)/2
                whites = len(movstrs)-blacks
            else:
                blacks = len(model.moves)/2
                whites = len(model.moves)-blacks

            model.timemodel.intervals = [
                [model.timemodel.intervals[0][0]]*(whites+1),
                [model.timemodel.intervals[1][0]]*(blacks+1),
            ]
            log.debug("pgn.loadToModel: intervals %s\n" % model.timemodel.intervals)
        
        
        # Find the physical status of the game
        model.status, model.reason = getStatus(model.boards[-1])
        
        # Apply result from .pgn if the last position was loaded
        if position == -1 or len(model.moves) == position - model.lowply:
            status = self.get_result(gameno)
            if status in (WHITEWON, BLACKWON) and status != model.status:
                model.status = status
                model.reason = WON_RESIGN
            elif status == DRAW:
                model.status = DRAW
                model.reason = DRAW_AGREE
        
        # If parsing gave an error we throw it now, to enlarge our possibility
        # of being able to continue the game from where it failed.
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

    def get_movetext(self, no):
        return self.games[no][1]

    def get_variant(self, no):
        variant = self._getTag(no, "Variant")
        return 1 if variant and ("fischer" in variant.lower() or "960" in variant) else 0

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
        the_date = self._getTag(no,"Date")
        today = date.today()
        if not the_date:
            return today.timetuple()[:3]
        return [ s.isdigit() and int(s) or today.timetuple()[i] \
                 for i,s in enumerate(the_date.split(".")) ]

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
        pgn2Const = {"*":RUNNING, "1/2-1/2":DRAW, "1/2":DRAW, "1-0":WHITEWON, "0-1":BLACKWON}
        if self._getTag(no,"Result") in pgn2Const:
            return pgn2Const[self._getTag(no,"Result")]
        return RUNNING

    def parse_string(self, string, model, board, position, variation=False):
        boards = []

        board = board.clone()
        last_board = board
        boards.append(board)

        error = None
        parenthesis = 0
        v_string = ""
        prev_group = -1
        for i, m in enumerate(re.finditer(pattern, string)):
            group, text = m.lastindex, m.group(m.lastindex)
            if parenthesis > 0:
                v_string += ' '+text

            if group == VARIATION_END:
                parenthesis -= 1
                if parenthesis == 0:
                    v_last_board.children.append(self.parse_string(v_string[:-1], model, board.prev, position, variation=True))
                    v_string = ""
                    prev_group = VARIATION_END
                    continue

            elif group == VARIATION_START:
                parenthesis += 1
                if parenthesis == 1:
                    v_last_board = last_board

            if parenthesis == 0:
                if group == FULL_MOVE:
                    if not variation:
                        if position != -1 and board.ply >= position:
                            break

                    mstr = m.group(MOVE)
                    try:
                        move = parseAny (boards[-1], mstr)
                    except ParsingError, e:
                        notation, reason, boardfen = e.args
                        ply = boards[-1].ply
                        if ply % 2 == 0:
                            moveno = "%d." % (ply/2+1)
                        else: moveno = "%d..." % (ply/2+1)
                        errstr1 = _("The game can't be read to end, because of an error parsing move %(moveno)s '%(notation)s'.") % {
                                    'moveno': moveno, 'notation': notation}
                        errstr2 = _("The move failed because %s.") % reason
                        error = LoadingError (errstr1, errstr2)
                        break

                    board = boards[-1].move(move)

                    ply = boards[-1].ply
                    if ply % 2 == 0:
                        mvcount = "%d." % (ply/2+1)
                    elif prev_group != FULL_MOVE:
                        mvcount = "%d..." % (ply/2+1)
                    else:
                        mvcount = ""        
                    board.movecount = mvcount

                    if m.group(MOVE_COMMENT):
                        board.nags.append(symbol2nag(m.group(MOVE_COMMENT)))

                    if last_board:
                        board.prev = last_board
                        last_board.next = board

                    boards.append(board)
                    last_board = board

                    if not variation:
                        model.moves.append(move)

                elif group == COMMENT_REST:
                    last_board.children.append(text[1:])

                elif group == COMMENT_BRACE:
                    comm = text.replace('{\r\n', '{').replace('\r\n}', '}')
                    comm = comm[1:-1].splitlines()
                    comment = ' '.join([line.strip() for line in comm])
                    last_board.children.append(comment)

                elif group == COMMENT_NAG:
                    board.nags.append(text)

                elif group == RESULT:
                    if text == "1/2":
                        model.status = reprResult.index("1/2-1/2")
                    else:
                        model.status = reprResult.index(text)
                    break

                else:
                    print "Unknown:",text

            if group != COMMENT_NAG:
                prev_group = group

            if error:
                raise error

        return boards


nag2symbolDict = {
    "$0": "",
    "$1": "!",
    "$2": "?",
    "$3": "!!",
    "$4": "??",
    "$5": "!?",
    "$6": "?!",
    "$7": "□",
    "$8": "□",
    "$9": "??",
    "$10": "=",
    "$11": "=",
    "$12": "=",
    "$13": "∞",
    "$14": "+=",
    "$15": "=+",
    "$16": "±",
    "$17": "∓",
    "$18": "+-",
    "$19": "-+",
    "$20": "+--",
    "$21": "--+",
    "$22": "⨀",
    "$23": "⨀",
}

symbol2nagDict = {}
for k, v in nag2symbolDict.iteritems():
    if v not in symbol2nagDict:
        symbol2nagDict[v] = k

def nag2symbol(nag):
    return nag2symbolDict.get(nag, nag)

def symbol2nag(symbol):
    return symbol2nagDict[symbol]
