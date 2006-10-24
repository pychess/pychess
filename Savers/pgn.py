from Utils.History import History
from Utils.Move import Move, parseSAN, toSAN
from Utils.validator import FINE, DRAW, WHITEWON, BLACKWON

__label__ = _("Chess Game")
__endings__ = "pgn",

import datetime

def save (file, history):
    today = datetime.date.today()

    # TODO: Create some kind of "match_param" (in knights) class to handle this kind of data. Might also be an expanded model class, instead of History
    from pwd import getpwuid
    from os import getuid
    userdata = getpwuid(getuid())
    name = userdata.pw_gecos
    if not name:
        name = userdata.pw_name
    
    result = {FINE:"*", DRAW:"1/2-1/2", WHITEWON:"1-0", BLACKWON:"0-1"}[history.status]
    
    # TODO: get some more calculated values here
    print >> file, '[Event "Local Game"]' #Event: the name of the tournament or match event.
    print >> file, '[Site "Local Game"]' #Site: the location of the event.
    print >> file, '[Date "%04d.%02d.%02d"]' % (today.year, today.month, today.day)
    print >> file, '[Round "?"]'
    print >> file, '[White "%s"]' % name
    print >> file, '[Black "Black Player"]'
    print >> file, '[Result "%s"]' % result
    print >> file

    halfMoves = 0
    nrOfCharsInLine = 0
    temphis = History()
    for move in history.moves:
        charsToBeWritten = ""
        # write movenr. every 2 halfmoves...
        if halfMoves % 2 == 0:
            charsToBeWritten += str( (halfMoves / 2)+1 ) + ". "

        # ...and the move
        temphis.add(move)
        charsToBeWritten += toSAN(temphis) + " "
        
        #wordwrap?
        if nrOfCharsInLine + len(charsToBeWritten) > 80:
            print >> file
            file.write(charsToBeWritten)
            nrOfCharsInLine = len(charsToBeWritten)
        else:
            file.write(charsToBeWritten)
            nrOfCharsInLine += len(charsToBeWritten)

        # increment halfmoves
        halfMoves += 1
    
    if history.status != FINE:
        #FIXME: This don't work with wordwrap
        file.write(result)
    
    file.close() # close the savegame

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
        #These tags won't be used for a lot atm.
        tags = tagre.findall(myFile[0])
        moves = comre.sub("", myFile[1])
        moves = stripBrackets(moves)
        moves = movre.findall(moves+" ")
        if moves[-1] in ("*", "1/2-1/2", "1-0", "0-1"):
            del moves[-1]
    except:
        import traceback
        log.error(traceback.format_exc())
        log.error("Couldn't parse pgn file: %s" % repr(file))
        log.debug("Part tried to parse: %s" % repr(myFile))
        return
    
    history.reset(False)
    for i, move in enumerate(moves):
        m = parseSAN(history, move)
        if i+1 < len(moves):
            history.add(m, False)
        else: history.add(m, True)
