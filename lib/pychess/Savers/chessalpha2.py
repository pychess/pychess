# -*- coding: utf-8 -*-

from htmlentitydefs import entitydefs
from pychess.Utils.Move import toFAN
from pychess.Utils.const import *


group = lambda l, s: [l[i:i+s] for i in xrange(0,len(l),s)]

__label__ = _("Chess Alpha 2 Diagram")
__ending__ = "html"
__append__ = True


#table[background][color][piece]
diaPieces = ((('\'','Ê','Â','À','Ä','Æ','È'),
              ('\'','ê','â','à','ä','æ','è')),
             (('#','Ë','Ã','Á','Å','Ç','É'),
              ('#','ë','ã','á','å','ç','é')))
borderNums = ('¬','"','£','$','%','^','&','*')
lisPieces = ((FAN_PIECES[BLACK][KNIGHT],'K'),
 (FAN_PIECES[BLACK][BISHOP],u'J'),
 (FAN_PIECES[BLACK][ROOK],u'L'),
 (FAN_PIECES[BLACK][QUEEN],u'M'),
 (FAN_PIECES[BLACK][KING],u'N'),
 (FAN_PIECES[WHITE][KNIGHT],u'k'),
 (FAN_PIECES[WHITE][BISHOP],u'j'),
 (FAN_PIECES[WHITE][ROOK],u'l'),
 (FAN_PIECES[WHITE][QUEEN],u'm'),
 (FAN_PIECES[WHITE][KING],u'n'),
 (u'†', u'+'),
 (u'‡', u'+'),
 (u'1/2', u'Z'))

def fanconv(fan):
    for f,r in lisPieces:
        fan = fan.replace(f,r)
    return fan

# Dictionaries and expressions for parsing diagrams
entitydefs = dict(("&%s;"%a,unichr(ord(b)).encode('utf-8'))
                  for a,b in entitydefs.iteritems() if len(b)==1)
def2entity = dict((b, a) for a,b in entitydefs.iteritems())
    

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
table.pychess pre {margin:0; padding:0; font-family:"Chess Alpha 2"; font-size:16pt; text-align:center; line-height:1}"""

def save (file, model, position=None):
    """Saves the position as a diagram using chess fonts"""
    
    print >> file, "<meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>"
    print >> file, "<style type='text/css'>%s</style>"%style
    print >> file, "<table cellspacing='0' cellpadding='0' class='pychess'><tr><td colspan='6'><pre>"
    writeDiagram(file, model)
    print >> file, "</pre></td></tr>"
    
    sanmvs = map(toFAN, model.boards[:-1], model.moves)
    sanmvs = map(fanconv, sanmvs)
    if model.lowply & 1: sanmvs = ["&gt;"]+sanmvs
    if model.status in (DRAW, WHITEWON, BLACKWON):
        sanmvs.extend(['']*(-len(sanmvs)%2))
        sanmvs.append(fanconv(reprResult[model.status]))
    sanmvs.extend(['']*(-len(sanmvs)%4))
    sanmvs = group(sanmvs, 2)
    for i in xrange((len(sanmvs)+1)/2):
        left = i+1+model.lowply/2
        writeMoves(file, str(i+1+model.lowply/2), sanmvs[i],
                         str(left+len(sanmvs)/2), sanmvs[i+len(sanmvs)/2])
    print >> file, "</table>"
    
    file.close()

def writeMoves(file, m1, movepair1, m2, movepair2):
    m1 += '.'; m2 += '.' 
    if not movepair2[0]:
        m2 = ''
    print >> file, "<tr><td class='numa'>%s</td><td>%s</td><td>%s</td>" % (m1, movepair1[0], movepair1[1])
    if not movepair2[1] and movepair2[0] in map(fanconv, reprResult):
        print >> file, "<td class='status' colspan='3'>%s</td></tr>" % movepair2[0] 
    else:
        print >> file, "<td class='numb'>%s</td><td>%s</td><td>%s</td></tr>" % (m2, movepair2[0], movepair2[1])

def writeDiagram(file, model, border = True, whitetop = False):
    data = model.boards[-1].data[:]
    if not whitetop: data.reverse()
    
    if border:
        print >> file, "[&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;]"

    for y,row in enumerate(data):
        if whitetop:
            file.write(borderNums(y))
        else:
            file.write(borderNums[7-y])
        for x,piece in sorted(row.items()):
            # exclude captured pieces in holding
            if x>=0 and x<=7:
                bg = y%2==x%2
                if piece == None:
                    color = WHITE
                    piece = EMPTY
                else:
                    color = piece.color
                    piece = piece.piece
                c = diaPieces[bg][color][piece]
                if c in def2entity:
                    c = def2entity[c]
                file.write(c)
        file.write('\\\n')

    if border:
        print >> file, "{ABCDEFGH}"
