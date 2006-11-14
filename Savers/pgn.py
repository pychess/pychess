from Utils.History import History
from Utils.Move import Move, parseSAN, toSAN
from Utils.const import *
from System.Log import log

__label__ = _("Chess Game")
__endings__ = "pgn",

def save (file, game):
    history = game.history

    #from pwd import getpwuid
    #from os import getuid
    #userdata = getpwuid(getuid())
    #name = userdata.pw_gecos
    #if not name:
    #    name = userdata.pw_name
    
    #result = reprResult[history.status]
    game_status = reprResult[game.history.boards[-1].status]

    print >> file, '[Event "%s"]' % game.event 
    print >> file, '[Site "%s"]' % game.site
    print >> file, '[Date "%04d.%02d.%02d"]' % (game.year, game.month, game.day)
    print >> file, '[Round "%d"]' % game.round
    print >> file, '[White "White Player"]'
    print >> file, '[Black "Black Player"]'
    print >> file, '[Result "%s"]' % game_status
    print >> file

    halfMoves = 0
    temphis = History()
    result = ''
    for move in history.moves:
        if halfMoves % 2 == 0:
            result += str((halfMoves / 2) + 1)
            result += '. '
        temphis.add(move)
        result += toSAN(temphis[-2], temphis[-1], temphis.moves[-1])
        result += ' '
        if len(result) >= 80:
            result += '\n'
            file.write(result)
            result = ''
        halfMoves += 1
    result += game_status + '\n'
    file.write(result)
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

import re
tagre = re.compile(r"\[([a-zA-Z]+)[ \t]+\"(.+?)\"\]")
movre = re.compile(r"([a-hxOoKQRBN0-8+#=-]{2,7})\s")
comre = re.compile(r"(?:\{.*?\})|(?:;.*?[\n\r])|(?:\$[0-9]+)", re.DOTALL)
def load (file, history):
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
            files[-1][1] += line

    myFile = files[0]
    
    try:
        tags = dict(tagre.findall(myFile[0]))
        moves = comre.sub("", myFile[1])
        moves = stripBrackets(moves)
        moves = movre.findall(moves+" ")
        if moves and moves[-1] in ("*", "1/2-1/2", "1-0", "0-1"):
            #TODO Save this result
            del moves[-1]
    except:
        log.error("Couldn't parse pgn file: %s" % repr(file))
        log.debug("Part tried to parse: %s" % repr(myFile))
        raise
    
    history.reset(False)
    for i, move in enumerate(moves):
        m = parseSAN(history[-1], move)
        if i+1 < len(moves):
            history.add(m, False)
        else: history.add(m, True)
    return tags
