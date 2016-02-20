# -*- coding: UTF-8 -*-

from __future__ import print_function

import re
import datetime

from pychess.Utils.const import RUNNING, DRAW, WHITEWON, BLACKWON
from pychess.Utils.lutils.LBoard import LBoard
from pychess.Utils.lutils.lmove import parseSAN, ParsingError
from pychess.Savers.ChessFile import ChessFile, LoadingError

# token categories
COMMENT_REST, COMMENT_BRACE, COMMENT_NAG, \
    VARIATION_START, VARIATION_END, \
    RESULT, FULL_MOVE, MOVE, MOVE_COMMENT = range(1, 10)

pattern = re.compile(r"""
    (\;.*?[\n\r])        # comment, rest of line style
    |(\{.*?\})           # comment, between {}
    |(\$[0-9]+)          # comment, Numeric Annotation Glyph
    |(\()                # variation start
    |(\))                # variation end
    |(\*|1-0|0-1|1/2)    # result (spec requires 1/2-1/2 for draw, but we want to tolerate simple 1/2 too)
    |(
    ([a-hKQRBNMSF][a-hxKQRBNMSF1-8+#=\-]{1,6}
    |[PNBRQMSFK]@[a-h][1-8][+#]?  # drop move
    |o\-o(?:\-o)?
    |O\-O(?:\-O)?
    |0\-0(?:\-0)?
    |\-\-)               # non standard '--' is used for null move inside variations
    ([\?!]{1,2})*
    )    # move (full, count, move with ?!, ?!)
    """, re.VERBOSE | re.DOTALL)


class PgnBase(ChessFile):
    def __init__(self, games):
        ChessFile.__init__(self, games)
        self.tagcache = {}

    def parse_string(self, string, board, position, variation=False):
        """Recursive parses a movelist part of one game.

           Arguments:
           srting - str (movelist)
           board - lboard (initial position)
           position - int (maximum ply to parse)
           variation- boolean (True if the string is a variation)"""

        boards = []
        boards_append = boards.append

        last_board = board
        if variation:
            # this board used only to hold initial variation comments
            boards_append(LBoard(board.variant))
        else:
            # initial game board
            boards_append(board)

        # status = None
        parenthesis = 0
        v_string = ""
        v_last_board = None
        for m in re.finditer(pattern, string):
            group, text = m.lastindex, m.group(m.lastindex)
            if parenthesis > 0:
                v_string += ' ' + text

            if group == VARIATION_END:
                parenthesis -= 1
                if parenthesis == 0:
                    v_last_board.children.append(
                        self.parse_string(v_string[:-1],
                                          last_board.prev,
                                          position,
                                          variation=True))
                    v_string = ""
                    continue

            elif group == VARIATION_START:
                parenthesis += 1
                if parenthesis == 1:
                    v_last_board = last_board

            if parenthesis == 0:
                if group == FULL_MOVE:
                    if not variation:
                        if position != -1 and last_board.plyCount >= position:
                            break

                    mstr = m.group(MOVE)
                    try:
                        lmove = parseSAN(last_board, mstr)
                    except ParsingError as err:
                        # TODO: save the rest as comment
                        # last_board.children.append(string[m.start():])
                        notation, reason, boardfen = err.args
                        ply = last_board.plyCount
                        if ply % 2 == 0:
                            moveno = "%d." % (ply // 2 + 1)
                        else:
                            moveno = "%d..." % (ply // 2 + 1)
                        errstr1 = _(
                            "The game can't be read to end, because of an error parsing move %(moveno)s '%(notation)s'.") % {
                                'moveno': moveno,
                                'notation': notation}
                        errstr2 = _("The move failed because %s.") % reason
                        self.error = LoadingError(errstr1, errstr2)
                        break
                    except:
                        ply = last_board.plyCount
                        if ply % 2 == 0:
                            moveno = "%d." % (ply // 2 + 1)
                        else:
                            moveno = "%d..." % (ply // 2 + 1)
                        errstr1 = _(
                            "Error parsing move %(moveno)s %(mstr)s") % {
                                "moveno": moveno,
                                "mstr": mstr}
                        self.error = LoadingError(errstr1, "")
                        break

                    new_board = last_board.clone()
                    new_board.applyMove(lmove)

                    if m.group(MOVE_COMMENT):
                        new_board.nags.append(symbol2nag(m.group(
                            MOVE_COMMENT)))

                    new_board.prev = last_board

                    # set last_board next, except starting a new variation
                    if variation and last_board == board:
                        boards[0].next = new_board
                    else:
                        last_board.next = new_board

                    boards_append(new_board)
                    last_board = new_board

                elif group == COMMENT_REST:
                    last_board.children.append(text[1:])

                elif group == COMMENT_BRACE:
                    comm = text.replace('{\r\n', '{').replace('\r\n}', '}')
                    comm = comm[1:-1].splitlines()
                    comment = ' '.join([line.strip() for line in comm])
                    if variation and last_board == board:
                        # initial variation comment
                        boards[0].children.append(comment)
                    else:
                        last_board.children.append(comment)

                elif group == COMMENT_NAG:
                    last_board.nags.append(text)

                # TODO
                elif group == RESULT:
                    # if text == "1/2":
                    #    status = reprResult.index("1/2-1/2")
                    # else:
                    #    status = reprResult.index(text)
                    break

                else:
                    print("Unknown:", text)

        return boards  # , status

    def _getTag(self, gameno, tagkey):
        if gameno in self.tagcache:
            if tagkey in self.tagcache[gameno]:
                return self.tagcache[gameno][tagkey]
            else:
                return ""
        else:
            if self.games:
                self.tagcache[gameno] = dict(tagre.findall(self.games[gameno][
                    0]))
                return self._getTag(gameno, tagkey)
            else:
                return ""

    def get_movetext(self, no):
        return self.games[no][1]

    def get_variant(self, no):
        variant = self._getTag(no, "Variant")
        if variant:
            if "fischer" in variant.lower() or "960" in variant:
                return "Fischerandom"
            else:
                return variant.lower().capitalize()
        else:
            # FICS saves variant names in event tag
            event = self.get_event(no)
            if "Chess960" in event:
                return "Fischerandom"
            elif "atomic" in event.lower():
                return "Atomic"
            elif "crazyhouse" in event.lower():
                return "Crazyhouse"
            elif "wildcastle" in event.lower():
                return "Wildcastle"
            elif "suicide" in event.lower():
                return "Suicide"
            elif "losers" in event.lower():
                return "Losers"
            else:
                return ""

    def get_player_names(self, no):
        player1 = self._getTag(no, "White") and \
            self._getTag(no, "White") or "Unknown"
        player2 = self._getTag(no, "Black") and \
            self._getTag(no, "Black") or "Unknown"
        return (player1, player2)

    def get_elo(self, no):
        player1 = self._getTag(no, "WhiteElo") and self._getTag(
            no, "WhiteElo") or "1600"
        player2 = self._getTag(no, "BlackElo") and self._getTag(
            no, "BlackElo") or "1600"
        player1 = player1.isdigit() and int(player1) or 1600
        player2 = player2.isdigit() and int(player2) or 1600
        return (player1, player2)

    def get_date(self, no):
        the_date = self._getTag(no, "Date")
        today = datetime.date.today()
        if not the_date:
            return today.timetuple()[:3]
        return [s.isdigit() and int(s) or today.timetuple()[i]
                for i, s in enumerate(the_date.split("."))]

    def get_site(self, no):
        return self._getTag(no, "Site") and self._getTag(no, "Site") or "?"

    def get_event(self, no):
        return self._getTag(no, "Event") and self._getTag(no, "Event") or "?"

    def get_round(self, no):
        round = self._getTag(no, "Round")
        if not round:
            return 1
        if round.find(".") >= 1:
            round = round[:round.find(".")]
        if not round.isdigit():
            return 1
        return int(round)

    def get_result(self, no):
        pgn2Const = {"*": RUNNING,
                     "1/2-1/2": DRAW,
                     "1/2": DRAW,
                     "1-0": WHITEWON,
                     "0-1": BLACKWON}
        if self._getTag(no, "Result") in pgn2Const:
            return pgn2Const[self._getTag(no, "Result")]
        return RUNNING


tagre = re.compile(r"\[([a-zA-Z]+)[ \t]+['\"](.*?)['\"]\]")


def pgn_load(file, klass=PgnBase):
    files = []
    in_tags = False

    for line in file:
        line = line.lstrip()
        if not line:
            continue
        elif line.startswith("%"):
            continue

        if line.startswith("["):
            if tagre.match(line) is not None:
                if not in_tags:
                    files.append(["", ""])
                    in_tags = True
                files[-1][0] += line
            else:
                if not in_tags:
                    files[-1][1] += line
                else:
                    print("Warning: ignored invalid tag pair %s" % line)
        else:
            in_tags = False
            if not files:
                # In rare cases there might not be any tags at all. It's not
                # legal, but we support it anyways.
                files.append(["", ""])
            files[-1][1] += line

    return klass(files)


nag2symbolDict = {
    "$0": "",
    "$1": "!",
    "$2": "?",
    "$3": "!!",
    "$4": "??",
    "$5": "!?",
    "$6": "?!",
    "$7": "□",  # forced move
    "$8": "□",
    "$9": "??",
    "$10": "=",
    "$11": "=",
    "$12": "=",
    "$13": "∞",  # unclear
    "$14": "+=",
    "$15": "=+",
    "$16": "±",
    "$17": "∓",
    "$18": "+-",
    "$19": "-+",
    "$20": "+--",
    "$21": "--+",
    "$22": "⨀",  # zugzwang
    "$23": "⨀",
    "$24": "◯",  # space
    "$25": "◯",
    "$26": "◯",
    "$27": "◯",
    "$28": "◯",
    "$29": "◯",
    "$32": "⟳",  # development
    "$33": "⟳",
    "$36": "↑",  # initiative
    "$37": "↑",
    "$40": "→",  # attack
    "$41": "→",
    "$44": "~=",  # compensation
    "$45": "=~",
    "$132": "⇆",  # counterplay
    "$133": "⇆",
    "$136": "⨁",  # time
    "$137": "⨁",
    "$138": "⨁",
    "$139": "⨁",
    "$140": "∆",  # with the idea
    "$141": "∇",  # aimed against
    "$142": "⌓",  # better is
    "$146": "N",  # novelty
}

symbol2nagDict = {}
for k, v in nag2symbolDict.items():
    if v not in symbol2nagDict:
        symbol2nagDict[v] = k


def nag2symbol(nag):
    return nag2symbolDict.get(nag, nag)


def symbol2nag(symbol):
    return symbol2nagDict[symbol]
