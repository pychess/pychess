# -*- coding: utf-8 -*-

import re
from htmlentitydefs import *

from pychess.Utils.Cord import Cord
from pychess.Utils.Piece import Piece
from pychess.Utils.Move import *
from pychess.Utils.const import *
from pychess.Utils.lutils.leval import evaluateComplete
from pychess.Utils.logic import getStatus

from ChessFile import ChessFile, LoadingError
group = lambda l, s: [l[i:i+s] for i in xrange(0,len(l),s)]

__label__ = _("Chess Alpha 2 Diagram")
__endings__ = "html",
__append__ = True


#table[background][color][piece]
diaPieces = ((('\'','Ê','Â','À','Ä','Æ','È'),
              ('\'','ê','â','à','ä','æ','è')),
             (('#','Ë','Ã','Á','Å','Ç','É'),
              ('#','ë','ã','á','å','ç','é')))
borderNums = ('¬','"','£','$','%','^','&','*')
lisPieces = ((FAN_PIECES[BLACK][KNIGHT],'K'),
 (FAN_PIECES[BLACK][BISHOP],'J'),
 (FAN_PIECES[BLACK][ROOK],'L'),
 (FAN_PIECES[BLACK][QUEEN],'M'),
 (FAN_PIECES[BLACK][KING],'N'),
 (FAN_PIECES[WHITE][KNIGHT],'k'),
 (FAN_PIECES[WHITE][BISHOP],'j'),
 (FAN_PIECES[WHITE][ROOK],'l'),
 (FAN_PIECES[WHITE][QUEEN],'m'),
 (FAN_PIECES[WHITE][KING],'n'),
 ('†', '+'),
 ('‡', '+'),
 ('1/2', 'Z'))
def fanconv(fan):
    for f,r in lisPieces:
        fan = fan.replace(f,r)
    return fan

# Dictionaries and expressions for parsing diagrams
entitydefs = dict(("&%s;"%a,unichr(ord(b)).encode('utf-8'))
                  for a,b in entitydefs.iteritems() if len(b)==1)
def2entity = dict((b, a) for a,b in entitydefs.iteritems())
flatPieces = [c for a in diaPieces for b in a for c in b]
piecesDia = dict((c,(col,pie)) for a in diaPieces for col,b in enumerate(a) for pie,c in enumerate(b))
pat = "%s|%s" % ("|".join(flatPieces), "|".join(def2entity[a] for a in flatPieces if a in def2entity))
reg1 = re.compile("(?:%s){8}"%pat, re.IGNORECASE)
reg2 = re.compile(pat, re.IGNORECASE)

    

style = """
table.pychess {display:inline-block; vertical-align:top}
table.pychess td {margin:0; padding:0; font-size:10pt; font-family:"Chess Alpha 2"; padding-left:.5em}
table.pychess td.numa {width:0; text-align:right}
table.pychess td.numa {width:0; text-align:right; padding-left:1em}
table.pychess td.status {text-align:center; font-size:12pt; padding-right:2em}
table.pychess pre {margin:0; padding:0; font-family:"Chess Alpha 2"; font-size:16pt; text-align:center; line-height:1}"""

def save (file, model):
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
    if not movepair2[0]: m2 = ''
    print >> file, "<tr><td class='numa'>%s</td><td>%s</td><td>%s</td>" % (m1, movepair1[0], movepair1[1])
    if not movepair2[1] and movepair2[0] in map(fanconv, reprResult):
        print >> file, "<td class='status' colspan='3'>%s</td></tr>" % movepair2[0] 
    else: print >> file, "<td class='numb'>%s</td><td>%s</td><td>%s</td></tr>" % (m2, movepair2[0], movepair2[1])

def writeDiagram(file, model, border = True, whitetop = False):
    data = model.boards[-1].data[:]
    if not whitetop: data.reverse()
    
    if border:
        print >> file, "[&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;]"
    for y,row in enumerate(data):
        if whitetop:
            file.write(borderNums(y))
        else: file.write(borderNums[7-y])
        for x,piece in enumerate(row):
            bg = y%2==x%2
            if piece == None:
                color = WHITE
                piece = EMPTY
            else:
                color = piece.color
                piece = piece.piece
            c = diaPieces[bg][color][piece]
            if c in def2entity: c = def2entity[c]
            file.write(c)
        file.write('\\\n')
    if border:
        print >> file, "{ABCDEFGH}"

def load (file):
    lines = reg1.findall(file.read().encode('utf-8'))
    return AlphaFile(group(lines, 8))

class AlphaFile (ChessFile):
    
    def loadToModel (self, gameno, position, model=None):
        if not model: model = GameModel()
        
        board = model.variant.board()
        for y,row in enumerate(self.games[gameno]):
            for x,letter in enumerate(reg2.findall(row)):
                if letter in entitydefs:
                    letter = entitydefs[letter]
                if letter not in piecesDia:
                    raise LoadingError (_("Couldn't load the diagram '%s'")%repr(letter))
                col, pie = piecesDia[letter]
                if pie != EMPTY:
                    board.addPiece(Cord(x,7-y), Piece(col,pie))
        
        model.boards = [board]
        if model.status == WAITING_TO_START:
            model.status, model.reason = getStatus(model.boards[-1])
        
        return model
