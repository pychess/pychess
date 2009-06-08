# -*- coding: utf-8 -*-

from pychess.Utils.Cord import Cord
from pychess.Utils.Piece import Piece
from pychess.Utils.Move import *
from pychess.Utils.const import *
from pychess.Utils.lutils.leval import evaluateComplete
from pychess.Utils.logic import getStatus

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
 ('‡', '+'))
#{\rtf1\ansi{\fonttbl\f0\fswiss Helvetica;}\f0\pard
#This is some {\b bold} text.\par
#}


def save (file, model):
    """Saves the position as a diagram using chess fonts"""
    
    print >> file, "<meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>"
    print >> file, """<style type='text/css'>
                      table{display:inline-block; vertical-align:top; margin-right:2em;}
                      td.mov{margin:0;padding:0;font-size:10pt;font-family:"Chess Alpha 2"; padding-left:.5em}
                      td.numa, td.numb {width:0; padding:0; text-align:right}
                      td.numb {padding-left:1em}
                      pre{margin:0; padding:0}</style>"""
    print >> file, """<table cellspacing="0" cellpadding="0"><tr><td colspan='6'>
                      <pre style='font-family:"Chess Alpha 2"; font-size:16pt; text-align:center'>"""
    writeDiagram(file, model)
    print >> file, "</pre></td></tr>"
    
    sanmvs = map(toFAN, model.boards[:-1], model.moves)
    def conv(fan):
        for f,r in lisPieces:
            fan = fan.replace(f,r)
        return fan
    sanmvs = map(conv, sanmvs)
    sanmvs.extend(['']*((4-(len(sanmvs)%4))%4))
    sanmvs = [(sanmvs[i],sanmvs[i+1]) for i in xrange(0,len(sanmvs),2)]
    for i in xrange((len(sanmvs)+1)/2):
        writeMoves(file, str(i+1), sanmvs[i],
                         str(i+1+len(sanmvs)/2), sanmvs[i+len(sanmvs)/2])
    print >> file, "</table>"
    
    #<tr><td valign='top'><pre style='font-family:\"Chess Alpha 2\"'>"
    #print >> file, "1. >\tMb6+"
    #print >> file, "2. nc8\tMc6+"
    #print >> file, "3.\tnd8\tNg7"
    #print >> file, "4.\te5?\tMb6+"
    #print >> file, "</pre></td><td valign='top'><pre style='font-family:\"Chess Alpha 2\"'>"
    #print >> file, "5.\tne8\tMb8+"
    #print >> file, "6.\td8=m\tMb5+"
    #print >> file, "<div style='text-aling:center'>½-½</div>"
    #print >> file, "</pre></td></tr></table>"
    
    file.close()

def writeMoves2(file, m1, movepair1, m2, movepair2):
    preit = lambda s: "<td style='font-family:\"Chess Alpha 2\"; font-size:10pt'>%s</td>"%s
    preitr = lambda s: "<td style='font-family:\"Chess Alpha 2\"; font-size:10pt; text-align:right; width:0'>%s</td>"%s
    m1 += '.'; m2 += '.' 
    print >> file, "<tr>%s%s%s" %  (preitr(m1), preit(movepair1[0]), preit(movepair1[1]))
    if not movepair2[0]: m2 = ''
    print >> file, "%s%s%s</tr>" %  (preitr(m2), preit(movepair2[0]), preit(movepair2[1]))

def writeMoves(file, m1, movepair1, m2, movepair2):
    m1 += '.'; m2 += '.' 
    if not movepair2[0]: m2 = ''
    print >> file, """<tr><td class='mov numa'>%s</td><td class='mov'>%s</td><td class='mov'>%s</td>
                          <td class='mov numb'>%s</td><td class='mov'>%s</td><td class='mov'>%s</td></tr>""" % \
                          (m1, movepair1[0], movepair1[1], m2, movepair2[0], movepair2[1])


def writeDiagram(file, model, border = True, whitetop = False):
    data = model.boards[-1].data[:]
    if not whitetop: data.reverse()
    
    if border:
        print >> file, "[<<<<<<<<]"
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
            file.write(diaPieces[bg][color][piece])
        file.write('\\\n')
    if border:
        print >> file, "{ABCDEFGH}"

def load (file):
    assert False, "The format doesn't support opening yet"
