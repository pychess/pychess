from pychess.Utils.Move import Move
from pychess.Utils.lutils.egtb_k4it import egtb_k4it
#from pychess.Utils.lutils.egtb_gaviota import egtb_gaviota
from pychess.Utils.lutils.bitboard import bitLength

class EndgameTable:
    
    """ Wrap the low-level providers of exact endgame knowledge. """
    
    def __init__ (self):
        #self.providers = [ egtb_gaviota(), egtb_k4it() ]
        self.providers = [ egtb_k4it() ]
    
    def _pieceCounts (self, board):
        return sorted([ bitLength(board.friends[i]) for i in range(2) ])
    
    def scoreGame (self, lBoard, omitDepth=False, probeSoft=False):
        """ Return result and depth to mate. (Intended for engine use.)
            
            lBoard: A low-level board structure
            omitDepth: Look up only the game's outcome (may save time)
            probeSoft: Fail if the probe would require disk or network access.
            Return value:
            game_result: Either WHITEWON, DRAW, BLACKWON, or (on failure) None
            depth: Depth to mate, or (if omitDepth or the game is drawn) None
        """
            
        pc = self._pieceCounts(lBoard)
        for provider in self.providers:
            if provider.supports(pc):
                result, depth = provider.scoreGame(lBoard, needDepth, probeSoft)
                if result is not None:
                    return result, depth
        return None, None
    
    def scoreAllMoves (self, board):
        """ Return each move's result and depth to mate.
            
            board: A high-level board structure
            Return value: a list, with best moves first, of:
            move: A high-level move structure
            game_result: Either WHITEWON, DRAW, BLACKWON, or (on failure) None
            depth: Depth to mate, or (if omitDepth or the game is drawn) None
        """
        pc = self._pieceCounts(board.board)
        for provider in self.providers:
            if provider.supports(pc):
                results = provider.scoreAllMoves(board.board)
                if results:
                    ret = []
                    for lMove, result, depth in results:
                        ret.append( (Move(lMove), result, depth) )
                    return results
        return []
