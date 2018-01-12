# -*- coding: utf-8 -*-

# TODO: fix it

from html.entities import entitydefs

from pychess.Utils.Move import toFAN
from pychess.Utils.const import FAN_PIECES, BLACK, ROOK, WHITE, KING, BISHOP, \
    KNIGHT, QUEEN, DRAW, EMPTY, reprResult, WHITEWON, BLACKWON


def group(l, s):
    return [l[i:i + s] for i in range(0, len(l), s)]


__label__ = _("Chess Alpha 2 Diagram")
__ending__ = "html"
__append__ = True

# table[background][color][piece]
diaPieces = ((('\'', 'Ê', 'Â', 'À', 'Ä', 'Æ', 'È'),
              ('\'', 'ê', 'â', 'à', 'ä', 'æ', 'è')),
             (('#', 'Ë', 'Ã', 'Á', 'Å', 'Ç', 'É'),
              ('#', 'ë', 'ã', 'á', 'å', 'ç', 'é')))
borderNums = ('¬', '"', '£', '$', '%', '^', '&', '*')
lisPieces = ((FAN_PIECES[BLACK][KNIGHT], 'K'),
             (FAN_PIECES[BLACK][BISHOP], 'J'), (FAN_PIECES[BLACK][ROOK], 'L'),
             (FAN_PIECES[BLACK][QUEEN], 'M'), (FAN_PIECES[BLACK][KING], 'N'),
             (FAN_PIECES[WHITE][KNIGHT], 'k'),
             (FAN_PIECES[WHITE][BISHOP], 'j'), (FAN_PIECES[WHITE][ROOK], 'l'),
             (FAN_PIECES[WHITE][QUEEN], 'm'), (FAN_PIECES[WHITE][KING], 'n'),
             ('†', '+'), ('‡', '+'), ('1/2', 'Z'))


def fanconv(fan):
    for f, r in lisPieces:
        fan = fan.replace(f, r)
    return fan


# Dictionaries and expressions for parsing diagrams
entitydefs = dict(("&%s;" % a, chr(ord(b)).encode('utf-8'))
                  for a, b in entitydefs.items() if len(b) == 1)
def2entity = dict((b, a) for a, b in entitydefs.items())

style = """
    @font-face {font-family: "Chess Alpha 2"; src: local("Chess Alpha 2"),
    url("http://pychess.org/fonts/ChessAlpha2.eot?") format("eot"),
    url("http://pychess.org/fonts/ChessAlpha2.woff") format("woff"),
    url("http://pychess.org/fonts/ChessAlpha2.ttf") format("truetype"),
    url("http://pychess.org/fonts/ChessAlpha2.svg#ChessAlpha2") format("svg"); font-weight:"normal"; font-style:"normal";}
    table.pychess {display:inline-block; vertical-align:top}
    table.pychess td {margin:0; padding:0; font-size:10pt; font-family:"Chess Alpha 2"; padding-left:.5em}
    table.pychess td.numa {width:0; text-align:right}
    table.pychess td.numa {width:0; text-align:right; padding-left:1em}
    table.pychess td.status {text-align:center; font-size:12pt; padding-right:2em}
    table.pychess pre {margin:0; padding:0; font-family:"Chess Alpha 2"; font-size:16pt; text-align:center; line-height:1}
"""


def save(file, model, position=None):
    """Saves the position as a diagram using chess fonts"""

    print("<meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>",
          file=file)
    print("<style type='text/css'>%s</style>" % style, file=file)
    print(
        "<table cellspacing='0' cellpadding='0' class='pychess'><tr><td colspan='6'><pre>",
        file=file)
    writeDiagram(file, model)
    print("</pre></td></tr>", file=file)

    sanmvs = map(toFAN, model.boards[:-1], model.moves)
    sanmvs = list(map(fanconv, sanmvs))
    if model.lowply & 1:
        sanmvs = ["&gt;"] + list(sanmvs)
    if model.status in (DRAW, WHITEWON, BLACKWON):
        sanmvs.extend([''] * (-len(sanmvs) % 2))
        sanmvs.append(fanconv(reprResult[model.status]))
    sanmvs.extend([''] * (-len(sanmvs) % 4))
    sanmvs = group(sanmvs, 2)
    for i in range((len(sanmvs) + 1) // 2):
        left = i + 1 + model.lowply // 2
        writeMoves(file, str(i + 1 + model.lowply // 2), sanmvs[i],
                   str(left + len(sanmvs) // 2), sanmvs[i + len(sanmvs) // 2])
    print("</table>", file=file)

    file.close()


def writeMoves(file, move1, movepair1, move2, movepair2):
    move1 += '.'
    move2 += '.'
    if not movepair2[0]:
        move2 = ''
    print("<tr><td class='numa'>%s</td><td>%s</td><td>%s</td>" %
          (move1, movepair1[0], movepair1[1]),
          file=file)
    if not movepair2[1] and movepair2[0] in map(fanconv, reprResult):
        print("<td class='status' colspan='3'>%s</td></tr>" % movepair2[0],
              file=file)
    else:
        print("<td class='numb'>%s</td><td>%s</td><td>%s</td></tr>" %
              (move2, movepair2[0], movepair2[1]),
              file=file)


def writeDiagram(file, model, border=True, whitetop=False):
    data = model.boards[-1].data[:]
    if not whitetop:
        data.reverse()

    if border:
        print("[&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;]", file=file)

    for y_loc, row in enumerate(data):
        if whitetop:
            file.write("%s" % borderNums(y_loc))
        else:
            file.write("%s" % borderNums[7 - y_loc])
        for x_loc, piece in sorted(row.items()):
            # exclude captured pieces in holding
            if x_loc >= 0 and x_loc <= 7:
                bg_colour = y_loc % 2 == x_loc % 2
                if piece is None:
                    color = WHITE
                    piece = EMPTY
                else:
                    color = piece.color
                    piece = piece.piece
                dia_color = diaPieces[bg_colour][color][piece]
                if dia_color in def2entity:
                    dia_color = def2entity[dia_color]
                file.write("%s" % dia_color)
        file.write('\\\n')

    if border:
        print("{ABCDEFGH}", file=file)
