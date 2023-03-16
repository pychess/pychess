from gi.repository import GObject

from pychess.System.Log import log
from pychess.Utils.const import UNSUPPORTED
from pychess.ic import GAME_TYPES, TITLES, RATING_TYPES
from pychess.ic.FICSObjects import FICSSeek
from pychess.ic.icc import DG_SEEK, DG_SEEK_REMOVED
from pychess.ic.managers.SeekManager import SeekManager


class ICCSeekManager(SeekManager):
    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_dg_line(DG_SEEK, self.on_icc_seek_add)
        self.connection.expect_dg_line(DG_SEEK_REMOVED, self.on_icc_seek_removed)

        self.connection.client.run_command("set-2 %s 1" % DG_SEEK)
        self.connection.client.run_command("set-2 %s 1" % DG_SEEK_REMOVED)

    def on_icc_seek_add(self, data):
        log.debug("DG_SEEK_ADD %s" % data)
        # index name titles rating provisional-status wild rating-type time
        # inc rated color minrating maxrating autoaccept formula fancy-time-control
        # 195 Tinker {C} 2402 2 0 Blitz 5 3 1 -1 0 9999 1 1 {}

        parts = data.split(" ", 2)
        index = int(parts[0])
        player = self.connection.players.get(parts[1])

        titles_end = parts[2].find("}")
        titles = parts[2][1:titles_end]
        tit = set()
        for title in titles.split():
            tit.add(TITLES[title])
        player.titles |= tit

        parts = parts[2][titles_end + 1 :].split()
        rating = int(parts[0])
        deviation = None  # parts[1]
        # wild = parts[2]
        try:
            gametype = GAME_TYPES[parts[3].lower()]
        except KeyError:
            return
        minutes = int(parts[4])
        increment = int(parts[5])
        rated = parts[6] == "1"
        color = parts[7]
        if color == "-1":
            color = None
        else:
            color = "white" if color == "1" else "black"
        rmin = int(parts[8])
        rmax = int(parts[9])
        automatic = parts[10] == "1"
        # formula = parts[11]
        # fancy_tc = parts[12]

        if gametype.variant_type in UNSUPPORTED:
            log.debug("!!! unsupported variant in seek: %s" % data)
            return

        if (
            gametype.rating_type in RATING_TYPES
            and player.ratings[gametype.rating_type] != rating
        ):
            player.ratings[gametype.rating_type] = rating
            player.deviations[gametype.rating_type] = deviation
            player.emit("ratings_changed", gametype.rating_type, player)

        seek = FICSSeek(
            index,
            player,
            minutes,
            increment,
            rated,
            color,
            gametype,
            rmin=rmin,
            rmax=rmax,
            automatic=automatic,
        )
        self.emit("addSeek", seek)

    def on_icc_seek_removed(self, data):
        log.debug("DG_SEEK_REMOVED %s" % data)
        key = data.split()[0]
        self.emit("removeSeek", int(key))
