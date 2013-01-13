from gobject import GObject, SIGNAL_RUN_FIRST

from Move import Move
from lutils.egtb_k4it import egtb_k4it
from lutils.egtb_gaviota import egtb_gaviota
from lutils.bitboard import bitLength

providers = []

class EndgameTable(GObject):
    
    """ Wrap the low-level providers of exact endgame knowledge. """

    __gsignals__ = {
        "scored":  (SIGNAL_RUN_FIRST, None, (object,)),
    }
    
    def __init__ (self):
        GObject.__init__(self)

        global providers
        if not providers:
            providers = [ egtb_gaviota(), egtb_k4it() ]
        self.providers = providers
    
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
    
    def scoreAllMoves (self, lBoard):
        """ Return each move's result and depth to mate.
            
            lBoard: A low-level board structure
            Return value: a list, with best moves first, of:
            move: A high-level move structure
            game_result: Either WHITEWON, DRAW, BLACKWON
            depth: Depth to mate
        """
        
        pc = self._pieceCounts(lBoard)
        for provider in self.providers:
            if provider.supports(pc):
                results = provider.scoreAllMoves(lBoard)
                if results:
                    ret = []
                    for lMove, result, depth in results:
                        ret.append( (Move(lMove), result, depth) )
                    self.emit("scored", (lBoard, ret))
                    return ret
        return []
