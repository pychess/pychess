""" Giveaway Variant"""

from pychess.Utils.const import GIVEAWAYCHESS
from .suicide import SuicideBoard


class GiveawayBoard(SuicideBoard):
    """:Description: This is the international version of Losing chess used on ICC as Giveaway and on Lichess as Antichess
        You must capture if you can, and the object is to lose all your pieces or to have no moves left.
        But in Giveaway, the king is just like any other piece.
        It can move into check and be captured, and you can even promote pawns to kings.
    """
    variant = GIVEAWAYCHESS
    __desc__ = _(
        "ICC giveaway: https://www.chessclub.com/user/help/Giveaway")
    name = _("Giveaway")
    cecp_name = "giveaway"
