import re

from gi.repository import GObject

from pychess.ic import BLKCMD_NEWS

days = "(Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
months = "(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"

AMOUNT_OF_NEWSITEMS = 5
FICS_SENDS = 10


class NewsManager(GObject.GObject):

    __gsignals__ = {
        'readingNews': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
        'readNews': (GObject.SignalFlags.RUN_FIRST, None, (object, )),
    }

    def __init__(self, connection):
        GObject.GObject.__init__(self)
        self.connection = connection
        self.news = {}
        self.connection.expect_line(
            self.onNewsItem, "(\d+) \(%s, %s +(\d+)\) (.+)" % (days, months))
        self.connection.client.run_command("news")

    def onNewsItem(self, match):

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
            self.connection.unexpect(self.onNewsItem)

        def onFullNewsItem(matchlist):
            self.connection.unexpect(onFullNewsItem)
            details = ""
            for line in matchlist[1:-1]:
                if line.startswith("\\"):
                    line = " " + line[1:].strip()
                details += line.replace("  ", " ")
            self.news[no][4] = details
            self.emit("readNews", self.news[no])

        self.connection.expect_fromto(onFullNewsItem, re.escape(line),
                                      "Posted by.*")
        self.connection.client.run_command("news %s" % no)

    onNewsItem.BLKCMD = BLKCMD_NEWS
