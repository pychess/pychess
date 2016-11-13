import re

from gi.repository import GObject

from pychess.Utils.const import WHITE, FISCHERRANDOMCHESS, UNSUPPORTED
from pychess.ic import BLKCMD_ASSESS, VariantGameType, DEVIATION, GAME_TYPES, \
    parse_title_hex, BLKCMD_UNSEEK, BLKCMD_SEEK, type_to_display_text, \
    Variants, RATING_TYPES
from pychess.ic.FICSObjects import FICSSeek
from pychess.System.Log import log

rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\- ]{1,4})"
titleslist = "(?:GM|IM|FM|WGM|WIM|WFM|TM|SR|TD|CA|C|U|D|B|T|\*)"
titleslist_re = re.compile(titleslist)
titles = "((?:\(%s\))+)?" % titleslist
names = "([a-zA-Z]+)%s" % titles
mf = "(?:([mf]{1,2})\s?)?"
whomatch = "(?:(?:([-0-9+]{1,4})([\^~:\#. &])%s))" % names
whomatch_re = re.compile(whomatch)
rating_re = re.compile("[0-9]{2,}")
type_re = "(Lightning|Blitz|Standard|Suicide|Wild|Crazyhouse|Bughouse|Losers|Atomic)"


class SeekManager(GObject.GObject):

    __gsignals__ = {
        'addSeek': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'removeSeek': (GObject.SignalFlags.RUN_FIRST, None, (int, )),
        'clearSeeks': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'our_seeks_removed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'seek_updated': (GObject.SignalFlags.RUN_FIRST, None, (str, )),
        'assessReceived': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection

        self.connection.expect_line(self.on_seek_clear, "<sc>")
        self.connection.expect_line(self.on_seek_add, "<s(?:n?)> (.+)")
        self.connection.expect_line(self.on_seek_remove, "<sr> ([\d ]+)")
        self.connection.expect_n_lines(self.on_our_seeks_removed,
                                       "<sr> ([\d ]+)",
                                       "Your seeks have been removed\.")
        self.connection.expect_n_lines(self.on_seek_updated,
                                       "Updating seek ad (\d+)(?:;?) (.*)\.",
                                       "", "<sr> (\d+)", "", "<sn> (.+)")
        self.connection.expect_n_lines(self.on_seek_updated,
                                       "Updating seek ad (\d+)(?:;?) (.*)\.",
                                       "Updating seek ad \d+(?:;?) (.*)\.", "",
                                       "<sr> (\d+)", "", "<sn> (.+)")

        self.connection.expect_n_lines(
            self.on_assess, "\s*%s\s*" % type_re, "\s*(\w+)\s+(\w+)\s*",
            "\s*(\(.+\))\s+(\(.+\))\s*", "\s*Win: .+", "\s*Draw: .+",
            "\s*Loss: .+", "\s*New RD: .+")

        self.connection.client.run_command("iset seekinfo 1")
        self.connection.client.run_command("iset seekremove 1")
        self.connection.client.run_command("iset showownseek 1")

    def seek(self,
             startmin,
             incsec,
             game_type,
             rated,
             ratings=(0, 9999),
             color=None,
             manual=False):
        log.debug("SeekManager.seek: %s %s %s %s %s %s %s" %
                  (startmin, incsec, game_type, rated, str(ratings), color, manual))
        rchar = "r" if rated else "u"
        if color is not None:
            cchar = color == WHITE and "w" or "b"
        else:
            cchar = ""
        manual = "m" if manual else ""
        s = "seek %d %d %s %s %s" % (startmin, incsec, rchar, cchar, manual)
        if isinstance(game_type, VariantGameType):
            s += " " + game_type.seek_text
        if not self.connection.FatICS:
            s += " %d-%d" % (ratings[0], ratings[1])

        self.connection.client.run_command(s, show_reply=True)

    def assess(self, player1, player2, type):
        self.connection.client.run_command("assess %s %s /%s" %
                                           (player1, player2, type))

    def on_assess(self, matchlist):
        assess = {}
        assess["type"] = matchlist[0].groups()[0]
        assess["names"] = matchlist[1].groups()[0], matchlist[1].groups()[1]
        assess["oldRD"] = matchlist[2].groups()[0], matchlist[2].groups()[1]
        assess["win"] = matchlist[3].string.split()[1:]
        assess["draw"] = matchlist[4].string.split()[1:]
        assess["loss"] = matchlist[5].string.split()[1:]
        assess["newRD"] = matchlist[6].string.split()[2:]
        self.emit("assessReceived", assess)

    on_assess.BLKCMD = BLKCMD_ASSESS

    def on_seek_add(self, match):
        # The <s> message looks like:
        # <s> index w=name_from ti=titles rt=rating t=time i=increment
        #     r=rated('r')/unrated('u') tp=type("wild/fr", "wild/4","blitz")
        #     c=color rr=rating_range(lower-upper) a=automatic?('t'/'f')
        #     f=formula_checked('t'/f')
        parts = match.groups()[0].split()
        seek = {}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            seek[key] = value

        try:
            index = int(parts[0])
            player = self.connection.players.get(seek['w'])
            player.titles |= parse_title_hex(seek['ti'])
            rated = seek['r'] == 'r'
            minutes = int(seek['t'])
            increment = int(seek['i'])
            rmin, rmax = [int(r) for r in seek['rr'].split("-")]
            rating = seek['rt']
            if rating[-1] in (" ", "P", "E"):
                deviation = DEVIATION[rating[-1]]
                rating = rating[:-1]
            rating = int(rating)
            deviation = None
            automatic = seek['a'] == 't'
            color = None
            if seek['c'] == "W":
                color = "white"
            elif seek['c'] == "B":
                color = "black"
        except KeyError as e:
            log.warning("on_seek_add: KeyError: %s %s" % (repr(e), repr(seek)))
            return

        try:
            gametype = GAME_TYPES[seek["tp"]]
        except KeyError:
            if self.connection.FatICS and seek["tp"] == "chess":
                # TODO: remove when fixed in FatICS
                expected_time = minutes + increment * 2 / 3
                if expected_time == 0:
                    gametype = "untimed"
                elif expected_time < 3:
                    gametype = "lightning"
                elif expected_time < 15:
                    gametype = "blitz"
                else:
                    gametype = "standard"
                gametype = GAME_TYPES[gametype]
            else:
                return
        if gametype.variant_type in UNSUPPORTED:
            return

        if gametype.rating_type in RATING_TYPES and player.ratings[gametype.rating_type] != rating:
            player.ratings[gametype.rating_type] = rating
            player.deviations[gametype.rating_type] = deviation
            player.emit("ratings_changed", gametype.rating_type, player)

        seek = FICSSeek(index,
                        player,
                        minutes,
                        increment,
                        rated,
                        color,
                        gametype,
                        rmin=rmin,
                        rmax=rmax,
                        automatic=automatic)
        self.emit("addSeek", seek)

    on_seek_add.BLKCMD = BLKCMD_SEEK

    def on_seek_clear(self, *args):
        self.emit("clearSeeks")

    def on_seek_remove(self, match):
        for key in match.groups()[0].split():
            if not key:
                continue
            self.emit("removeSeek", int(key))

    on_seek_remove.BLKCMD = BLKCMD_UNSEEK

    def on_our_seeks_removed(self, matchlist):
        self.on_seek_remove(matchlist[0])
        self.emit("our_seeks_removed")

    on_our_seeks_removed.BLKCMD = BLKCMD_UNSEEK

    def on_seek_updated(self, matchlist):
        text = matchlist[0].groups()[1]
        i = 0
        if "Updating seek ad" in matchlist[1].string:
            text += '; ' + matchlist[1].groups()[0]
            i = 1
        self.on_seek_remove(matchlist[i + 2])
        self.on_seek_add(matchlist[i + 4])
        self.emit("seek_updated", text)

    on_seek_updated.BLKCMD = BLKCMD_SEEK

    def refresh_seeks(self):
        self.connection.client.run_command("iset seekinfo 1")


if __name__ == "__main__":
    assert type_to_display_text("Loaded from eco/a00") == type_to_display_text(
        "eco/a00") == "Eco A00"
    assert type_to_display_text("wild/fr") == Variants.variants[
        FISCHERRANDOMCHESS].name
    assert type_to_display_text("blitz") == GAME_TYPES["blitz"].display_text
