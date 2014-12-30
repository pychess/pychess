from __future__ import absolute_import
from pychess.Utils.const import *
from .normal import NormalChess
from .corner import CornerChess
from .shuffle import ShuffleChess
from .fischerandom import FischerRandomChess
from .randomchess import RandomChess
from .asymmetricrandom import AsymmetricRandomChess
from .upsidedown import UpsideDownChess
from .pawnspushed import PawnsPushedChess
from .pawnspassed import PawnsPassedChess
from .theban import ThebanChess
from .atomic import AtomicChess
from .bughouse import BughouseChess
from .crazyhouse import CrazyhouseChess
from .losers import LosersChess
from .suicide import SuicideChess
from .pawnodds import PawnOddsChess
from .knightodds import KnightOddsChess
from .rookodds import RookOddsChess
from .queenodds import QueenOddsChess
from .wildcastle import WildcastleChess
from .wildcastleshuffle import WildcastleShuffleChess
from .blindfold import BlindfoldChess, HiddenPawnsChess, \
                      HiddenPiecesChess, AllWhiteChess
from .kingofthehill import KingOfTheHillChess

variants = {NORMALCHESS : NormalChess,
            CORNERCHESS : CornerChess,
            SHUFFLECHESS : ShuffleChess,
            FISCHERRANDOMCHESS : FischerRandomChess,
            RANDOMCHESS: RandomChess,
            ASYMMETRICRANDOMCHESS: AsymmetricRandomChess,
            UPSIDEDOWNCHESS : UpsideDownChess,
            PAWNSPUSHEDCHESS : PawnsPushedChess,
            PAWNSPASSEDCHESS : PawnsPassedChess,
            THEBANCHESS : ThebanChess,
            ATOMICCHESS: AtomicChess,
            BUGHOUSECHESS: BughouseChess,
            CRAZYHOUSECHESS: CrazyhouseChess,
            LOSERSCHESS : LosersChess,
            SUICIDECHESS: SuicideChess,
            PAWNODDSCHESS : PawnOddsChess,
            KNIGHTODDSCHESS : KnightOddsChess,
            ROOKODDSCHESS : RookOddsChess,
            QUEENODDSCHESS : QueenOddsChess,
            ALLWHITECHESS : AllWhiteChess,
            BLINDFOLDCHESS : BlindfoldChess,
            HIDDENPAWNSCHESS : HiddenPawnsChess,
            HIDDENPIECESCHESS : HiddenPiecesChess,
            WILDCASTLECHESS: WildcastleChess,
            WILDCASTLESHUFFLECHESS: WildcastleShuffleChess,
            KINGOFTHEHILLCHESS: KingOfTheHillChess,
            }
