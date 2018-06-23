
from pychess.Utils.const import NORMALCHESS, CORNERCHESS, SHUFFLECHESS, FISCHERRANDOMCHESS, \
    RANDOMCHESS, ASYMMETRICRANDOMCHESS, UPSIDEDOWNCHESS, PAWNSPUSHEDCHESS, THEBANCHESS, \
    BUGHOUSECHESS, PAWNSPASSEDCHESS, ATOMICCHESS, CRAZYHOUSECHESS, LOSERSCHESS, SUICIDECHESS, \
    PAWNODDSCHESS, KNIGHTODDSCHESS, ROOKODDSCHESS, QUEENODDSCHESS, ALLWHITECHESS, BLINDFOLDCHESS, \
    HIDDENPIECESCHESS, HIDDENPAWNSCHESS, WILDCASTLECHESS, WILDCASTLESHUFFLECHESS, THREECHECKCHESS, \
    AIWOKCHESS, KINGOFTHEHILLCHESS, ASEANCHESS, CAMBODIANCHESS, SITTUYINCHESS, EUROSHOGICHESS, \
    RACINGKINGSCHESS, MAKRUKCHESS, SETUPCHESS, GIVEAWAYCHESS, HORDECHESS, PLACEMENTCHESS

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
from .horde import HordeBoard
from .giveaway import GiveawayBoard
from .pawnodds import PawnOddsBoard
from .knightodds import KnightOddsBoard
from .rookodds import RookOddsBoard
from .queenodds import QueenOddsBoard
from .wildcastle import WildcastleBoard
from .wildcastleshuffle import WildcastleShuffleBoard
from .blindfold import BlindfoldBoard, HiddenPawnsBoard, HiddenPiecesBoard, AllWhiteBoard
from .kingofthehill import KingOfTheHillBoard
from .threecheck import ThreeCheckBoard
from .racingkings import RacingKingsBoard
from .asean import AiWokBoard, AseanBoard, CambodianBoard, MakrukBoard, SittuyinBoard
from .euroshogi import EuroShogiBoard
from .setupposition import SetupBoard
from .placement import PlacementBoard


variants = {NORMALCHESS: NormalBoard,
            CORNERCHESS: CornerBoard,
            SHUFFLECHESS: ShuffleBoard,
            FISCHERRANDOMCHESS: FischerandomBoard,
            RANDOMCHESS: RandomBoard,
            ASYMMETRICRANDOMCHESS: AsymmetricRandomBoard,
            UPSIDEDOWNCHESS: UpsideDownBoard,
            PAWNSPUSHEDCHESS: PawnsPushedBoard,
            PAWNSPASSEDCHESS: PawnsPassedBoard,
            THEBANCHESS: ThebanBoard,
            ATOMICCHESS: AtomicBoard,
            BUGHOUSECHESS: BughouseBoard,
            CRAZYHOUSECHESS: CrazyhouseBoard,
            LOSERSCHESS: LosersBoard,
            SUICIDECHESS: SuicideBoard,
            GIVEAWAYCHESS: GiveawayBoard,
            HORDECHESS: HordeBoard,
            PAWNODDSCHESS: PawnOddsBoard,
            KNIGHTODDSCHESS: KnightOddsBoard,
            ROOKODDSCHESS: RookOddsBoard,
            QUEENODDSCHESS: QueenOddsBoard,
            ALLWHITECHESS: AllWhiteBoard,
            BLINDFOLDCHESS: BlindfoldBoard,
            HIDDENPAWNSCHESS: HiddenPawnsBoard,
            HIDDENPIECESCHESS: HiddenPiecesBoard,
            WILDCASTLECHESS: WildcastleBoard,
            WILDCASTLESHUFFLECHESS: WildcastleShuffleBoard,
            KINGOFTHEHILLCHESS: KingOfTheHillBoard,
            THREECHECKCHESS: ThreeCheckBoard,
            RACINGKINGSCHESS: RacingKingsBoard,
            AIWOKCHESS: AiWokBoard,
            ASEANCHESS: AseanBoard,
            CAMBODIANCHESS: CambodianBoard,
            MAKRUKCHESS: MakrukBoard,
            SITTUYINCHESS: SittuyinBoard,
            EUROSHOGICHESS: EuroShogiBoard,
            SETUPCHESS: SetupBoard,
            PLACEMENTCHESS: PlacementBoard,
            }

name2variant = dict([(v.cecp_name.capitalize(), v) for v in variants.values()])

# FICS pgn export names
name2variant["Wild/0"] = WildcastleBoard
name2variant["Wild/1"] = WildcastleShuffleBoard
name2variant["Wild/2"] = ShuffleBoard
name2variant["Wild/3"] = RandomBoard
name2variant["Wild/4"] = AsymmetricRandomBoard
name2variant["Wild/5"] = UpsideDownBoard
name2variant["Wild/fr"] = FischerandomBoard
name2variant["Wild/8"] = PawnsPushedBoard
name2variant["Wild/8a"] = PawnsPassedBoard

# Lichess pgn export names
name2variant["Standard"] = NormalBoard
name2variant["Antichess"] = SuicideBoard
name2variant["King of the hill"] = KingOfTheHillBoard
name2variant["Three-check"] = ThreeCheckBoard
name2variant["Racing kings"] = RacingKingsBoard
name2variant["Horde"] = HordeBoard
