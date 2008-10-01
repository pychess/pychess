from pychess.Utils.const import *
from normal import NormalChess
from shuffle import ShuffleChess
from fischerandom import FischerRandomChess
from upsidedown import UpsideDownChess
from losers import LosersChess

variants = {NORMALCHESS : NormalChess,
            SHUFFLECHESS : ShuffleChess,
            FISCHERRANDOMCHESS : FischerRandomChess,
            UPSIDEDOWNCHESS : UpsideDownChess,
            LOSERSCHESS : LosersChess
            }
