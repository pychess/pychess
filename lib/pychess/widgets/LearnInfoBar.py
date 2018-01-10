from gi.repository import Gtk

from pychess.Utils.const import UNDOABLE_STATES
from pychess.Utils.Cord import Cord
from pychess.Utils.logic import getStatus

HINT, MOVE, RETRY, NEXT = 0, 1, 2, 3


class LearnInfoBar(Gtk.InfoBar):
    def __init__(self, gamemodel, boardview):
        Gtk.InfoBar.__init__(self)

        self.content_area = self.get_content_area()
        self.action_area = self.get_action_area()

        self.gamemodel = gamemodel
        self.boardview = boardview

        self.gamemodel.connect("game_changed", self.game_changed)
        self.connect("response", self.on_response)
        self.clear()
        self.reset()

    def clear(self):
        for item in self.content_area:
            self.content_area.remove(item)

        for item in self.action_area:
            self.action_area.remove(item)

    def reset(self):
        self.set_message_type(Gtk.MessageType.QUESTION)
        label = Gtk.Label(_("Your turn."))
        self.content_area.add(label)

        self.add_button(_("Hint"), HINT)
        self.add_button(_("Move"), MOVE)

    def on_response(self, widget, response):
        if response in (HINT, MOVE):
            if self.gamemodel.hint:
                if self.boardview.arrows:
                    self.boardview.arrows.clear()
                if self.boardview.circles:
                    self.boardview.circles.clear()

                hint = self.gamemodel.hint
                cord0 = Cord(hint[0], int(hint[1]), "G")
                cord1 = Cord(hint[2], int(hint[3]), "G")
                if response == HINT:
                    self.boardview.circles.add(cord0)
                    self.boardview.redrawCanvas()
                else:
                    self.boardview.arrows.add((cord0, cord1))
                    self.boardview.redrawCanvas()
            else:
                hint = _("No hint available.")
        elif response == RETRY:
            self.gamemodel.undoMoves(2)
            self.clear()
            self.reset()
        elif response == NEXT:
            # TODO:
            print("start next puzzle")

    def game_changed(self, gamemodel, ply):
        if gamemodel.practice_game and gamemodel.hint:
            if len(gamemodel.moves) % 2 == 0:
                # engine moved, we can enable retry
                self.set_response_sensitive(RETRY, True)
                return

            print(gamemodel.hint, repr(gamemodel.moves[-1]))
            status, reason = getStatus(gamemodel.boards[-1])

            self.clear()
            if status in UNDOABLE_STATES:
                self.set_message_type(Gtk.MessageType.INFO)
                label = Gtk.Label(_("Well done!"))
                self.content_area.add(label)
                self.add_button(_("Next"), NEXT)

            elif gamemodel.hint != repr(gamemodel.moves[-1]):
                self.set_message_type(Gtk.MessageType.ERROR)
                label = Gtk.Label(_("Not the best!"))
                self.content_area.add(label)
                self.add_button(_("Retry"), RETRY)
                # disable retry button until engine thinking on next move
                self.set_response_sensitive(RETRY, False)

            else:
                self.reset()

            self.show_all()
