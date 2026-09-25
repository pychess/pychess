import unittest

try:
    from pychess.widgets.gamewidget import GameWidget
except Exception:  # pragma: no cover - requires a GTK display
    GameWidget = None

from pychess.Utils.GameModel import GameModel
from pychess.Utils.Offer import Offer
from pychess.Utils.const import (
    ABORT_OFFER,
    BLACK,
    DRAW_OFFER,
    LOCAL,
    RUNNING,
    WHITE,
)


class _MockPlayer:
    """A minimal stand-in for a pychess Player used to drive GameModel's
    offer bookkeeping without a real engine or network player."""

    __type__ = LOCAL

    def __init__(self, color):
        self.color = color
        self.name = "mock-%s" % ("white" if color == WHITE else "black")

    def offer(self, offer):
        pass

    def offerWithdrawn(self, offer):
        pass

    def offerDeclined(self, offer):
        pass

    def offerError(self, offer, error):
        pass

    def hurry(self):
        pass

    def putMessage(self, message):
        pass


class _MockMenuItem:
    def __init__(self):
        self.sensitive = True
        self.label = ""
        self.tooltip = ""


class _FakeWidget:
    """A stand-in for GameWidget exposing only the attributes the
    _update_menu_* methods read/write."""

    def __init__(self, gamemodel):
        self.gamemodel = gamemodel
        self.menuitems = {
            "draw": _MockMenuItem(),
            "abort": _MockMenuItem(),
            "adjourn": _MockMenuItem(),
            "pause1": _MockMenuItem(),
            "resume1": _MockMenuItem(),
            "undo1": _MockMenuItem(),
        }


class GameModelOfferSignalsTestCase(unittest.TestCase):
    def setUp(self):
        self.model = GameModel()
        self.white = _MockPlayer(WHITE)
        self.black = _MockPlayer(BLACK)
        self.model.players = [self.white, self.black]
        self.emitted = []
        self.model.connect("game_changed", self._on_changed)

    def _on_changed(self, *args):
        self.emitted.append(args)

    def test_offer_lifecycle_emits_game_changed(self):
        """Issue #797: offerReceived / withdrawReceived / declineReceived must
        emit 'game_changed' so the Actions menu can re-evaluate which 'Offer *'
        items are still available."""
        offer = Offer(DRAW_OFFER)
        before = len(self.emitted)

        self.model.offerReceived(self.white, offer)
        self.assertIn(offer, self.model.offers)
        self.assertEqual(len(self.emitted), before + 1)

        self.model.withdrawReceived(self.white, offer)
        self.assertNotIn(offer, self.model.offers)
        self.assertEqual(len(self.emitted), before + 2)

        offer2 = Offer(DRAW_OFFER)
        self.model.offerReceived(self.white, offer2)
        self.assertEqual(len(self.emitted), before + 3)

        self.model.declineReceived(self.black, offer2)
        self.assertNotIn(offer2, self.model.offers)
        self.assertEqual(len(self.emitted), before + 4)

    def test_abort_offer_is_tracked_and_emits(self):
        """The same signal machinery applies to non-draw offers (e.g. abort),
        confirming the fix is offer-type agnostic."""
        before = len(self.emitted)
        offer = Offer(ABORT_OFFER)
        self.model.offerReceived(self.white, offer)
        self.assertIn(offer, self.model.offers)
        self.assertEqual(len(self.emitted), before + 1)


@unittest.skipIf(GameWidget is None, "GameWidget/Gtk not importable in this env")
class OfferMenuSensitivityTestCase(unittest.TestCase):
    def setUp(self):
        self.model = GameModel()
        self.model.status = RUNNING
        self.model.timed = False
        self.white = _MockPlayer(WHITE)
        self.black = _MockPlayer(BLACK)
        self.model.players = [self.white, self.black]
        self.widget = _FakeWidget(self.model)

    def test_draw_enabled_then_disabled_while_offer_outstanding(self):
        """Issue #797: the Draw menu item is enabled when no draw has been
        offered, and becomes insensitive once a draw offer is outstanding (so a
        second draw offer cannot be sent)."""
        GameWidget._update_menu_draw(self.widget)
        self.assertTrue(self.widget.menuitems["draw"].sensitive)

        self.model.offerReceived(self.white, Offer(DRAW_OFFER))
        GameWidget._update_menu_draw(self.widget)
        self.assertFalse(self.widget.menuitems["draw"].sensitive)

    def test_draw_re_enabled_after_withdraw(self):
        """After the outstanding draw offer is withdrawn, the Draw item is
        enabled again."""
        self.model.offerReceived(self.white, Offer(DRAW_OFFER))
        GameWidget._update_menu_draw(self.widget)
        self.assertFalse(self.widget.menuitems["draw"].sensitive)

        self.model.withdrawReceived(self.white, Offer(DRAW_OFFER))
        GameWidget._update_menu_draw(self.widget)
        self.assertTrue(self.widget.menuitems["draw"].sensitive)


if __name__ == "__main__":
    unittest.main()
