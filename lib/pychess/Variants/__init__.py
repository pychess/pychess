from pychess.Utils.const import *
from normal import NormalChess
from shuffle import ShuffleChess
from fischerandom import FischerRandomChess
from upsidedown import UpsideDownChess
from losers import LosersChess
from pawnodds import PawnOddsChess
from knightodds import KnightOddsChess
from rookodds import RookOddsChess
from queenodds import QueenOddsChess

variants = {NORMALCHESS : NormalChess,
            SHUFFLECHESS : ShuffleChess,
            FISCHERRANDOMCHESS : FischerRandomChess,
            UPSIDEDOWNCHESS : UpsideDownChess,
            LOSERSCHESS : LosersChess,
            PAWNODDSCHESS : PawnOddsChess,
            KNIGHTODDSCHESS : KnightOddsChess,
            ROOKODDSCHESS : RookOddsChess,
            QUEENODDSCHESS : QueenOddsChess,
            }
