from pychess.perspectives import Perspective


class FICS(Perspective):
    def __init__(self):
        Perspective.__init__(self, "fics", _("ICS"))
