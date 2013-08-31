from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE
import re
from pychess.Utils.const import *
from pychess.ic import *
from pychess.ic.block_codes import BLKCMD_SEEK, BLKCMD_UNSEEK
from pychess.ic.FICSObjects import *
from pychess.ic.managers.BoardManager import parse_reason
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
        'addSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'clearSeeks' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'seek_updated' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        
        self.connection = connection
        
        self.connection.expect_line (self.on_seek_clear, "<sc>")
        self.connection.expect_line (self.on_seek_add, "<s(?:n?)> (.+)")
        self.connection.expect_line (self.on_seek_remove, "<sr> ([\d ]+)")
        self.connection.expect_n_lines (self.on_seek_updated,
            "Updating seek ad (\d+)(?:;?) (.*)\.",
            "",
            "<sr> (\d+)",
            "fics%\s*",
            "<sn> (.+)")
        self.connection.lvm.setVariable("seekinfo", 1)
        self.connection.lvm.setVariable("seekremove", 1)
        self.connection.lvm.setVariable("showownseek", 1)
        
    def seek (self, startmin, incsec, game_type, rated, ratings=(0, 9999),
              color=None, manual=False):
        log.debug("SeekManager.seek: %s %s %s %s %s %s %s\n" % \
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
        parts = match.groups()[0].split(" ")
        # The <s> message looks like:
        # <s> index w=name_from ti=titles rt=rating t=time i=increment
        #     r=rated('r')/unrated('u') tp=type("wild/fr", "wild/4","blitz")
        #     c=color rr=rating_range(lower-upper) a=automatic?('t'/'f')
        #     f=formula_checked('t'/f')
        
        seek = {"gameno": parts[0]}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            if key in ('w', 'r', 't', 'i'):
                seek[key] = value
            if key == "tp":
                try:
                    seek["gametype"] = GAME_TYPES[value]
                    if GAME_TYPES[value].variant_type in UNSUPPORTED:
                        return
                except KeyError:
                    if self.connection.FatICS and value == "chess":
                        # TODO: remove when fixed in FatICS
                        expected_time = int(seek["t"]) + int(seek["i"])*2/3
                        if expected_time == 0:
                            value = "untimed"
                        elif expected_time < 3:
                            value = "lightning"
                        elif expected_time < 15:
                            value = "blitz"
                        else:
                            value = "standard"
                        seek["gametype"] = GAME_TYPES[value]
                    else:
                        return
            if key == "rr":
                seek["rmin"], seek["rmax"] = value.split("-")
                seek["rmin"] = int(seek["rmin"])
                seek["rmax"] = int(seek["rmax"])                
            elif key == "ti":
                seek["cp"] = bool(int(value) & 2) # 0x2 - computer
                title = ""
                for hex in HEX_TO_TITLE.keys():
                    if int(value, 16) & hex:
                        title += "(" + \
                            TITLE_TYPE_DISPLAY_TEXTS_SHORT[HEX_TO_TITLE[hex]] + ")"
                seek["title"] = title
            elif key == "rt":
                if value[-1] in (" ", "P", "E"):
                    seek[key] = value[:-1]
                else: seek[key] = value
            elif key == "a":
                seek["manual"] = value == "f" # Must be accepted manually
        self.emit("addSeek", seek)
    on_seek_add.BLKCMD = BLKCMD_SEEK
    
    def on_seek_clear (self, *args):
        self.emit("clearSeeks")
    
    def on_seek_remove (self, match):
        for key in match.groups()[0].split(" "):
            if not key: continue
            self.emit("removeSeek", key)
    on_seek_remove.BLKCMD = BLKCMD_UNSEEK
    
    def on_seek_updated (self, matchlist):
        self.on_seek_remove(matchlist[2])
        self.on_seek_add(matchlist[4])
        self.emit("seek_updated", matchlist[0].groups()[1])
    on_seek_updated.BLKCMD = BLKCMD_SEEK
    
    def refresh_seeks (self):
        self.connection.lvm.setVariable("seekinfo", 1)
    
if __name__ == "__main__":
    assert type_to_display_text("Loaded from eco/a00") == type_to_display_text("eco/a00") == "Eco A00"
    assert type_to_display_text("wild/fr") == Variants.variants[FISCHERRANDOMCHESS].name
    assert type_to_display_text("blitz") == GAME_TYPES["blitz"].display_text
