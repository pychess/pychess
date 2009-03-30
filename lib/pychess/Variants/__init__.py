from pychess.Utils.const import *
from normal import NormalChess
from shuffle import ShuffleChess
from fischerandom import FischerRandomChess
from randomchess import RandomChess
from asymmetricrandom import AsymmetricRandomChess
from upsidedown import UpsideDownChess
from pawnspushed import PawnsPushedChess
from pawnspassed import PawnsPassedChess
from losers import LosersChess
from pawnodds import PawnOddsChess
from knightodds import KnightOddsChess
from rookodds import RookOddsChess
from queenodds import QueenOddsChess

variants = {NORMALCHESS : NormalChess,
            SHUFFLECHESS : ShuffleChess,
            FISCHERRANDOMCHESS : FischerRandomChess,
            RANDOMCHESS: RandomChess,
            ASYMMETRICRANDOMCHESS: AsymmetricRandomChess,
            UPSIDEDOWNCHESS : UpsideDownChess,
            PAWNSPUSHEDCHESS : PawnsPushedChess,
            PAWNSPASSEDCHESS : PawnsPassedChess,
            LOSERSCHESS : LosersChess,
            PAWNODDSCHESS : PawnOddsChess,
            KNIGHTODDSCHESS : KnightOddsChess,
            ROOKODDSCHESS : RookOddsChess,
            QUEENODDSCHESS : QueenOddsChess,
            }
