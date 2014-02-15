from gobject import GObject, SIGNAL_RUN_FIRST
import re
from pychess.Utils.const import *
from pychess.ic import *
from pychess.ic.FICSObjects import *
from pychess.ic.managers.HelperManager import HelperManager
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
deviation_estimated_re = re.compile("E")
deviation_provisional_re = re.compile("P")

class SeekManager (GObject):
    
    __gsignals__ = {
        'addSeek' : (SIGNAL_RUN_FIRST, None, (object,)),
        'removeSeek' : (SIGNAL_RUN_FIRST, None, (int,)),
        'clearSeeks' : (SIGNAL_RUN_FIRST, None, ()),
        'our_seeks_removed' : (SIGNAL_RUN_FIRST, None, ()),
        'seek_updated' : (SIGNAL_RUN_FIRST, None, (str,)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        
        self.connection.expect_line (self.on_seek_clear, "<sc>")
        self.connection.expect_line (self.on_seek_add, "<s(?:n?)> (.+)")
        self.connection.expect_line (self.on_seek_remove, "<sr> ([\d ]+)")
        self.connection.expect_n_lines (self.on_our_seeks_removed,
            "<sr> ([\d ]+)",
            "Your seeks have been removed\.")
        self.connection.expect_n_lines (self.on_seek_updated,
            "Updating seek ad (\d+)(?:;?) (.*)\.",
            "",
            "<sr> (\d+)",
            "",
            "<sn> (.+)")
        self.connection.expect_n_lines (self.on_seek_updated,
            "Updating seek ad (\d+)(?:;?) (.*)\.",
            "Updating seek ad \d+(?:;?) (.*)\.",
            "",
            "<sr> (\d+)",
            "",
            "<sn> (.+)")
        self.connection.lvm.setVariable("seekinfo", 1)
        self.connection.lvm.setVariable("seekremove", 1)
        self.connection.lvm.setVariable("showownseek", 1)
        
    def seek (self, startmin, incsec, game_type, rated, ratings=(0, 9999),
              color=None, manual=False):
        log.debug("SeekManager.seek: %s %s %s %s %s %s %s" % \
            (startmin, incsec, game_type, rated, str(ratings), color, manual))
        rchar = "r" if rated else "u"
        if color != None:
            cchar = color == WHITE and "w" or "b"
        else: cchar = ""
        manual = "m" if manual else ""
        s = "seek %d %d %s %s %s" % (startmin, incsec, rchar, cchar, manual)
        if isinstance(game_type, VariantGameType):
            s += " " + game_type.seek_text
        if not self.connection.FatICS:
            s += " %d-%d" % (ratings[0], ratings[1])
        
        #print s        
        self.connection.client.run_command(s)
    
    ###
    
    def on_seek_add (self, match):
        # The <s> message looks like:
        # <s> index w=name_from ti=titles rt=rating t=time i=increment
        #     r=rated('r')/unrated('u') tp=type("wild/fr", "wild/4","blitz")
        #     c=color rr=rating_range(lower-upper) a=automatic?('t'/'f')
        #     f=formula_checked('t'/f')
        parts = match.groups()[0].split(" ")
        seek = {}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            seek[key] = value
        
        try:
            index = int(parts[0])
            player = self.connection.players.get(FICSPlayer(seek['w']))
            player.titles |= parse_title_hex(seek['ti'])
            rated = seek['r'] == 'r'
            minutes = int(seek['t'])
            increment = int(seek['i'])
            rmin, rmax = [int(r) for r in seek['rr'].split("-")]
            rating = seek['rt']
            deviation = None
            if rating[-1] in (" ", "P", "E"):
                deviation = DEVIATION[rating[-1]]
                rating = rating[:-1]
            rating = int(rating)
            automatic = seek['a'] == 't'
            color = None
            if seek['c'] == "W":
                color = "white"
            elif seek['c'] == "B":
                color = "black"
        except KeyError, e:
            log.warning("on_seek_add: KeyError: %s %s" % (repr(e), repr(seek)))
            return
        
        try:
            gametype = GAME_TYPES[seek["tp"]]
        except KeyError:
            if self.connection.FatICS and seek["tp"] == "chess":
                # TODO: remove when fixed in FatICS
                expected_time = minutes + increment*2/3
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
        player.ratings[gametype.rating_type].elo = rating
        player.ratings[gametype.rating_type].deviation = deviation
        
        seek = FICSSeek(index, player, minutes, increment, rated, color,
                        gametype, rmin=rmin, rmax=rmax, automatic=automatic)
        self.emit("addSeek", seek)
    on_seek_add.BLKCMD = BLKCMD_SEEK
    
    def on_seek_clear (self, *args):
        self.emit("clearSeeks")
    
    def on_seek_remove (self, match):
        for key in match.groups()[0].split(" "):
            if not key: continue
            self.emit("removeSeek", int(key))
    on_seek_remove.BLKCMD = BLKCMD_UNSEEK
    
    def on_our_seeks_removed (self, matchlist):
        self.on_seek_remove(matchlist[0])
        self.emit("our_seeks_removed")
    on_our_seeks_removed.BLKCMD = BLKCMD_UNSEEK
    
    def on_seek_updated (self, matchlist):
        text = matchlist[0].groups()[1]
        i = 0
        if "Updating seek ad" in matchlist[1].string:
            text += '; ' + matchlist[1].groups()[0]
            i = 1
        self.on_seek_remove(matchlist[i+2])
        self.on_seek_add(matchlist[i+4])
        self.emit("seek_updated", text)
    on_seek_updated.BLKCMD = BLKCMD_SEEK
    
    def refresh_seeks (self):
        self.connection.lvm.setVariable("seekinfo", 1)
    
if __name__ == "__main__":
    assert type_to_display_text("Loaded from eco/a00") == type_to_display_text("eco/a00") == "Eco A00"
    assert type_to_display_text("wild/fr") == Variants.variants[FISCHERRANDOMCHESS].name
    assert type_to_display_text("blitz") == GAME_TYPES["blitz"].display_text
