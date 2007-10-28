
import re
from gobject import *

types = "(Blitz|Lightning|Standard)"
days = "(Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
months = "(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"

AMOUNT_OF_NEWSITEMS = 5
FICS_SENDS = 10

class NewsManager (GObject):
    
    __gsignals__ = {
        'readingNews' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'readNews' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
    }
    
    def __init__ (self, connection):
        GObject.__init__(self)
        self.connection = connection
        self.news = {}
        self.connection.expect_line (self.onNewsItem,
                "(\d+) \(%s, %s +(\d+)\) (.+)" % (days, months))
        print >> self.connection.client, "news"
    
    def onNewsItem (self, match):
        
        no, weekday, month, day, title = match.groups()
        line = match.group()
        self.news[no] = [_(weekday), _(month), day, title, ""]
        self.emit("readingNews", self.news[no])
        
        if len(self.news) <= AMOUNT_OF_NEWSITEMS:
            # the "news" command, gives us the latest 10 news items from the
            # oldest to the newest.
            # We only want the 5 newest, so we skip the first 5 entries.
            return
        elif len(self.news) == FICS_SENDS:
            # No need to check the expression any more
            self.connection.unexpect (self.onNewsItem)
        
        def callback (matchlist):
            self.connection.unexpect(callback)
            details = ""
            for line in matchlist[1:-1]:
                if line.startswith(r"\   "):
                    line = line[4:]
                details += line.replace("  ", " ")
            self.news[no][4] = details
            self.emit("readNews", self.news[no])
        
        self.connection.expect_fromto (callback, re.escape(line), "Posted by.*")
        print >> self.connection.client, "news", no
