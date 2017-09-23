import sys

from gi.repository import Gtk

from pychess.ic import GAME_TYPES_BY_RATING_TYPE, TYPE_WILD, WildGameType
from pychess.System.ping import Pinger
from pychess.System.Log import log
from pychess.widgets import mainwindow


class UserInfoSection():

    def __init__(self, widgets, connection, host, lounge):
        self.widgets = widgets
        self.connection = connection
        self.host = host
        self.lounge = lounge
        self.pinger = None
        self.ping_label = None

        self.dock = self.widgets["fingerTableDock"]

        self.connection.fm.connect("fingeringFinished", self.onFinger)
        self.connection.fm.finger(self.connection.getUsername())
        self.connection.bm.connect(
            "curGameEnded",
            lambda *args: self.connection.fm.finger(self.connection.getUsername()))

        self.widgets["usernameLabel"].set_markup("<b>%s</b>" %
                                                 self.connection.getUsername())

    def _del(self):
        if self.pinger is not None:
            self.pinger.stop()

    def onFinger(self, fm, finger):
        # print(finger.getName(), self.connection.getUsername())
        my_finger = finger.getName().lower() == self.connection.getUsername().lower()
        if my_finger:
            self.widgets["usernameLabel"].set_markup("<b>%s</b>" % finger.getName())
        rows = 1
        if finger.getRatingsLen() > 0:
            rows += finger.getRatingsLen() + 1
        if finger.getEmail():
            rows += 1
        if finger.getCreated():
            rows += 1

        cols = 6 if my_finger else 9
        table = Gtk.Table(cols, rows)
        table.props.column_spacing = 12
        table.props.row_spacing = 4

        def label(value, xalign=0, is_error=False):
            if is_error:
                label = Gtk.Label()
                label.set_markup('<span size="larger" foreground="red">' +
                                 value + "</span>")
            else:
                label = Gtk.Label(label=value)
            label.props.xalign = xalign
            return label

        row = 0

        ELO, DEVIATION, WINS, LOSSES, DRAWS, TOTAL, BESTELO, BESTTIME = range(8)
        if finger.getRatingsLen() > 0:
            if my_finger:
                headers = (_("Rating"), _("Win"), _("Draw"), _("Loss"))
            else:
                headers = (_("Rating"), _("Need") if self.connection.ICC else "RD", _("Win"), _("Draw"), _("Loss"), _("Best"))
            for i, item in enumerate(headers):
                table.attach(label(item, xalign=1), i + 1, i + 2, 0, 1)
            row += 1
            for rating_type, rating in finger.getRatings().items():
                col = 0
                ratinglabel = label(GAME_TYPES_BY_RATING_TYPE[
                                    rating_type].display_text + ":")
                table.attach(ratinglabel, col, col + 1, row, row + 1)
                col += 1
                if rating_type is TYPE_WILD:
                    ratinglabel.set_tooltip_text(_(
                        "On FICS, your \"Wild\" rating encompasses all of the \
                        following variants at all time controls:\n") +
                        ", ".join([gt.display_text for gt in WildGameType.instances()]))
                table.attach(label(rating[ELO], xalign=1), col, col + 1, row, row + 1)
                col += 1
                if not my_finger:
                    table.attach(label(rating[DEVIATION], xalign=1), col, col + 1, row, row + 1)
                    col += 1
                table.attach(label(rating[WINS], xalign=1), col, col + 1, row, row + 1)
                col += 1
                table.attach(label(rating[DRAWS], xalign=1), col, col + 1, row, row + 1)
                col += 1
                table.attach(label(rating[LOSSES], xalign=1), col, col + 1, row, row + 1)
                col += 1
                if not my_finger and len(rating) > BESTELO:
                    best = rating[BESTELO] if int(rating[BESTELO]) > 0 else ""
                    table.attach(label(best, xalign=1), col, col + 1, row, row + 1)
                    col += 1
                    table.attach(label(rating[BESTTIME], xalign=1), col, col + 1, row, row + 1)
                    col += 1
                row += 1

            table.attach(Gtk.HSeparator(), 0, cols, row, row + 1, ypadding=2)
            row += 1

        if finger.getSanctions() != "":
            table.attach(label(_("Sanctions") + ":", is_error=True), 0, 1, row, row + 1)
            table.attach(label(finger.getSanctions()), 1, cols, row, row + 1)
            row += 1

        if finger.getEmail():
            table.attach(label(_("Email") + ":"), 0, 1, row, row + 1)
            table.attach(label(finger.getEmail()), 1, cols, row, row + 1)
            row += 1

        player = self.connection.players.get(finger.getName())
        if not self.connection.ICC and not player.isGuest():
            table.attach(label(_("Games") + ":"), 0, 1, row, row + 1)
            llabel = Gtk.Label()
            llabel.props.xalign = 0
            link = "http://ficsgames.org/cgi-bin/search.cgi?player=%s" % finger.getName()
            llabel.set_markup('<a href="%s">%s</a>' % (link, link))
            table.attach(llabel, 1, cols, row, row + 1)
            row += 1

        if finger.getCreated():
            table.attach(label(_("Spent") + ":"), 0, 1, row, row + 1)
            string = "%s %s" % (finger.getTotalTimeOnline(), _("online in total"))
            table.attach(label(string), 1, cols, row, row + 1)
            row += 1

        # TODO: ping causes random crashes on Windows
        if my_finger and sys.platform != "win32":
            table.attach(label(_("Ping") + ":"), 0, 1, row, row + 1)
            if self.ping_label:
                if self.dock.get_children():
                    self.dock.get_children()[0].remove(self.ping_label)
            else:
                if self.connection.ICC:
                    self.ping_label = Gtk.Label(label="")  # TODO
                else:
                    self.ping_label = Gtk.Label(label=_("Connecting") + "...")
                self.ping_label.props.xalign = 0

            def callback(pinger, pingtime):
                log.debug("'%s' '%s'" % (str(self.pinger), str(pingtime)),
                          extra={"task": (self.connection.username,
                                          "UIS.oF.callback")})
                if isinstance(pingtime, str):
                    self.ping_label.set_text(pingtime)
                elif pingtime == -1:
                    self.ping_label.set_text(_("Unknown"))
                else:
                    self.ping_label.set_text("%.0f ms" % pingtime)

            if (not self.pinger) and (not self.connection.ICC):
                self.pinger = Pinger(self.host)
                self.pinger.start()
                self.pinger.connect("received", callback)
                self.pinger.connect("error", callback)
            table.attach(self.ping_label, 1, cols, row, row + 1)
            row += 1

        if not my_finger:
            if self.lounge.finger_sent:
                dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.INFO,
                                           buttons=Gtk.ButtonsType.OK)
                dialog.set_title(_("Finger"))
                dialog.set_markup("<b>%s</b>" % finger.getName())
                table.show_all()
                dialog.get_message_area().add(table)
                dialog.run()
                dialog.destroy()
            self.lounge.finger_sent = False
            return

        if not self.connection.isRegistred():
            vbox = Gtk.VBox()
            table.attach(vbox, 0, cols, row, row + 1)
            label0 = Gtk.Label()
            label0.props.xalign = 0
            label0.props.wrap = True
            label0.props.width_request = 300
            if self.connection.ICC:
                reg = "https://store.chessclub.com/customer/account/create/"
                txt = _("You are currently logged in as a guest but " +
                        "there is a completely free trial for 30 days, " +
                        "and beyond that, there is no charge and " +
                        "the account would remain active with the ability to play games. " +
                        "(With some restrictions. For example, no premium videos, " +
                        "some limitations in channels, and so on.) " +
                        "To register an account, go to ")
            else:
                reg = "http://www.freechess.org/Register/index.html"
                txt = _("You are currently logged in as a guest. " +
                        "A guest can't play rated games and therefore isn't " +
                        "able to play as many of the types of matches offered as " +
                        "a registered user. To register an account, go to ")

            label0.set_markup('%s <a href="%s">%s</a>.' % (txt, reg, reg))
            vbox.add(label0)

        if self.dock.get_children():
            self.dock.remove(self.dock.get_children()[0])
        self.dock.add(table)
        self.dock.show_all()
