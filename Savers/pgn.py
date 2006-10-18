from Utils import History

__label__ = _("Chess Game (.pgn)")
__endings__ = "pgn",

import datetime

def save (file, game):
        
    # TODO: get some more calculated values here
    file.write("[Event \"" + game.event + "\"]" + "\n")
    file.write("[Site \"" + game.site + "\"]" + "\n")
    file.write("[Date \"" + game.year + "." + game.month + "." + game.day + "\"]" + "\n")
    file.write("[Round \"" + str(game.round) + "\"]" + "\n")
    file.write("[White \"" + str(game.player1) + "\"]" + "\n")
    file.write("[Black \"" + str(game.player2) + "\"]" + "\n")
    file.write("[Result \"?\"]" + "\n")
    file.write("\n")
    
    halfMoves = 0
    nrOfCharsInLine = 0
    for move in game.history.moves:
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
