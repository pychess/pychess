from pychess.perspectives import Perspective


class Games(Perspective):
    def __init__(self):
        Perspective.__init__(self, "games", _("Games"))
