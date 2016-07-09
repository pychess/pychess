from pychess.perspectives import Perspective


class Database(Perspective):
    def __init__(self):
        Perspective.__init__(self, "database", _("Database"))
