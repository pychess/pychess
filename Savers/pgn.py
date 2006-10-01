from Utils import History

__label__ = _("Chess Game (.pgn)")
__endings__ = "pgn",

import datetime

def save (file, history):
    today = datetime.date.today()
    year = str(today.year)
    month = str(today.month)
    if len(month) == 1:
        month = "0" + month
    day = str(today.day)
    if len(day) == 1:
        day = "0" + day
        
    # TODO: get some more calculated values here
    file.write("[Event \"Local Game\"]" + "\n")
    file.write("[Site \"Local Game\"]" + "\n")
    file.write("[Date \"" + year + "." + month + "." + day + "\"]" + "\n")
    file.write("[Round \"?\"]" + "\n")
    file.write("[White \"Human Player\"]" + "\n")
    file.write("[Black \"Human Player\"]" + "\n")
    file.write("[Result \"?\"]" + "\n")
    file.write("\n")
    
    halfMoves = 0
    nrOfCharsInLine = 0
    for move in history.moves:
        charsToBeWritten = ""
        # write movenr. every 2 halfmoves...
        if halfMoves % 2 == 0:
            charsToBeWritten += str( (halfMoves / 2)+1 ) + "."

        # ...and the move
        charsToBeWritten += str(move) + " "
        
        #wordwrap?
        if nrOfCharsInLine + len(charsToBeWritten) > 80:
            file.write("\n")
            file.write(charsToBeWritten)
            nrOfCharsInLine = len(charsToBeWritten)
        else:
            file.write(charsToBeWritten)
            nrOfCharsInLine += len(charsToBeWritten)

        # increment halfmoves
        halfMoves += 1
        
    file.close() # close the savegame
    
    
def load (file):
    return None
