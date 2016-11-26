from gi.repository import GObject

from pychess.ic import GAME_TYPES_BY_FICS_NAME
from pychess.ic.icc import DG_WHO_AM_I, CN_YFINGER
from pychess.ic.managers.FingerManager import FingerManager, FingerObject

ELO, DEVIATION, WINS, LOSSES, DRAWS, TOTAL, BESTELO, BESTTIME = range(8)

ICC_RATING_TYPE_MAP = {
    "Bul": "bullet",
    "Bli": "blitz",
    "Sta": "standard",
    "1-m": "1-minute",
    "3-m": "3-minute",
    "5-m": "5-minute",
    "15-": "15-minute",
    "45-": "45-minute",
    "Che": "chess960",
}


class ICCFingerManager(FingerManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_dg_line(DG_WHO_AM_I, self.on_icc_who_am_i)
        self.connection.expect_cn_line(CN_YFINGER, self.on_icc_yfinger)

        self.connection.client.run_command("set-2 %s 1" % DG_WHO_AM_I)

    def on_icc_yfinger(self, data):
        finger = FingerObject()
        lines = data.split("\n")
        rating_lines = {}
        for line in lines:
            key, value = line.split(" ", 1)
            prefix = key[:3]
            # print(key, value, prefix, key[3:])
            if prefix in ICC_RATING_TYPE_MAP:
                if prefix not in rating_lines:
                    rating_lines[prefix] = [0] * 8
                if key[3:] == "Rat":
                    value = int(value)
                    rating_lines[prefix][ELO] = value
                elif key[3:] == "Win":
                    value = int(value)
                    rating_lines[prefix][WINS] = value
                elif key[3:] == "Draw":
                    value = int(value)
                    rating_lines[prefix][DRAWS] = value
                elif key[3:] == "Loss":
                    value = int(value)
                    rating_lines[prefix][LOSSES] = value
                elif key[3:] == "Need":
                    value = int(value)
                    rating_lines[prefix][DEVIATION] = value
                elif key[3:] == "Best":
                    bestelo, besttime = value.split(" ", 1)
                    rating_lines[prefix][BESTELO] = int(bestelo)
                    rating_lines[prefix][BESTTIME] = besttime
            elif key == "Name":
                finger.setName(value)

        for prefix in rating_lines:
            gametype = GAME_TYPES_BY_FICS_NAME[ICC_RATING_TYPE_MAP[prefix]]
            finger.setRating(gametype.rating_type, rating_lines[prefix])

        self.emit("fingeringFinished", finger)

    def on_icc_who_am_i(self, data):
        name, titles = data.split(" ", 1)
        self.connection.username = name

    def finger(self, user):
        self.connection.client.run_command("yfinger %s" % user)
