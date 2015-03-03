from __future__ import absolute_import

from pychess.Utils.const import *
from .normal import NormalBoard
from .corner import CornerBoard
from .shuffle import ShuffleBoard
from .fischerandom import FischerandomBoard
from .randomchess import RandomBoard
from .asymmetricrandom import AsymmetricRandomBoard
from .upsidedown import UpsideDownBoard
from .pawnspushed import PawnsPushedBoard
from .pawnspassed import PawnsPassedBoard
from .theban import ThebanBoard
from .atomic import AtomicBoard
from .bughouse import BughouseBoard
from .crazyhouse import CrazyhouseBoard
from .losers import LosersBoard
from .suicide import SuicideBoard
from .pawnodds import PawnOddsBoard
from .knightodds import KnightOddsBoard
from .rookodds import RookOddsBoard
from .queenodds import QueenOddsBoard
from .wildcastle import WildcastleBoard
from .wildcastleshuffle import WildcastleShuffleBoard
from .blindfold import BlindfoldBoard, HiddenPawnsBoard, \
                    HiddenPiecesBoard, AllWhiteBoard
from .kingofthehill import KingOfTheHillBoard
from .asean import AiWokBoard, AseanBoard, KambodianBoard, \
                    MakrukBoard, SittuyinBoard
from .euroshogi import EuroShogiBoard


variants = {NORMALCHESS : NormalBoard,
            CORNERCHESS : CornerBoard,
            SHUFFLECHESS : ShuffleBoard,
            FISCHERRANDOMCHESS : FischerandomBoard,
            RANDOMCHESS: RandomBoard,
            ASYMMETRICRANDOMCHESS: AsymmetricRandomBoard,
            UPSIDEDOWNCHESS : UpsideDownBoard,
            PAWNSPUSHEDCHESS : PawnsPushedBoard,
            PAWNSPASSEDCHESS : PawnsPassedBoard,
            THEBANCHESS : ThebanBoard,
            ATOMICCHESS: AtomicBoard,
            BUGHOUSECHESS: BughouseBoard,
            CRAZYHOUSECHESS: CrazyhouseBoard,
            LOSERSCHESS : LosersBoard,
            SUICIDECHESS: SuicideBoard,
            PAWNODDSCHESS : PawnOddsBoard,
            KNIGHTODDSCHESS : KnightOddsBoard,
            ROOKODDSCHESS : RookOddsBoard,
            QUEENODDSCHESS : QueenOddsBoard,
            ALLWHITECHESS : AllWhiteBoard,
            BLINDFOLDCHESS : BlindfoldBoard,
            HIDDENPAWNSCHESS : HiddenPawnsBoard,
            HIDDENPIECESCHESS : HiddenPiecesBoard,
            WILDCASTLECHESS: WildcastleBoard,
            WILDCASTLESHUFFLECHESS: WildcastleShuffleBoard,
            KINGOFTHEHILLCHESS: KingOfTheHillBoard,
            AIWOKCHESS: AiWokBoard,
            ASEANCHESS: AseanBoard,
            KAMBODIANCHESS: KambodianBoard,
            MAKRUKCHESS: MakrukBoard,
            SITTUYINCHESS: SittuyinBoard,
            EUROSHOGICHESS: EuroShogiBoard,
            }

name2variant = dict([(v.cecp_name.capitalize(), v) for v in variants.values()])
