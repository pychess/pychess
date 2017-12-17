from io import StringIO
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gi.repository import Gdk, Gtk

from pychess.Utils.const import NAME, UNDOABLE_STATES
from pychess.Savers import pgn
from pychess.widgets import mainwindow

URL = "http://www.chesspastebin.com/api/add/"
APIKEY = "a137d919b75c8766b082367610189358cfb1ba70"


def paste(gamemodel):
    dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO)
    if gamemodel.status in UNDOABLE_STATES:
        text = _("The current game is over. First, please verify the properties of the game.")
    else:
        text = _("The current game is not terminated. Its export may have a limited interest.")
    text += "\n\n" + _("Should %s publicly publish your game as PGN on chesspastebin.com ?") % NAME
    dialog.set_markup(text)
    response = dialog.run()
    dialog.destroy()
    if response != Gtk.ResponseType.YES:
        return

    output = StringIO()
    text = pgn.save(output, gamemodel)
    values = {'apikey': APIKEY,
              'pgn': text,
              "name": "PyChess",
              'sandbox': 'false'}

    data = urlencode(values).encode('utf-8')
    req = Request(URL, data)
    try:
        response = urlopen(req, timeout=10)
    except URLError as err:
        if hasattr(err, 'reason'):
            print('We failed to reach the server.')
            print('Reason: ', err.reason)
        elif hasattr(err, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', err.code)
    else:
        ID = response.read()
        link = "http://www.chesspastebin.com/?p=%s" % int(ID)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(link, -1)
        # print(text)
        # print(clipboard.wait_for_text())
        msg_dialog = Gtk.MessageDialog(mainwindow(), type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.OK)
        msg = _(
            "Game shared at ") + '<a href="%s">chesspastebin.com</a>' % link
        msg_dialog.set_markup(msg)
        msg_dialog.format_secondary_text(_("(Link is available on clipboard.)"))
        msg_dialog.connect("response", lambda msg_dialog, a: msg_dialog.hide())
        msg_dialog.show()
