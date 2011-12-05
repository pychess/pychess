from pychess.Utils.const import *
from normal import NormalChess
from corner import CornerChess
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
from blindfold import BlindfoldChess, HiddenPawnsChess, \
                      HiddenPiecesChess, AllWhiteChess

variants = {NORMALCHESS : NormalChess,
            CORNERCHESS : CornerChess,
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
            ALLWHITECHESS : AllWhiteChess,
            BLINDFOLDCHESS : BlindfoldChess,
            HIDDENPAWNSCHESS : HiddenPawnsChess,
            HIDDENPIECESCHESS : HiddenPiecesChess,
            }
