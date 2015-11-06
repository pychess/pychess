from __future__ import print_function

from gi.repository import Gdk
from gi.repository import Gtk

from pychess.Savers import pgn
from pychess.compat import Request, urlencode, urlopen, HTTPError, URLError, StringIO

URL = "http://www.chesspastebin.com/api/add/"
APIKEY = "a137d919b75c8766b082367610189358cfb1ba70"

def paste(gamemodel):
    output = StringIO()
    text = pgn.save(output, gamemodel)
    values = {'apikey' : APIKEY,
              'pgn' : text,
              "name": "PyChess",
              'sandbox' : 'false' }

    data = urlencode(values).encode('utf-8')
    req = Request(URL, data)
    try:
        response = urlopen(req, timeout=10)
    except URLError as e:
        if hasattr(e, 'reason'):
            print('We failed to reach the server.')
            print('Reason: ', e.reason)
        elif hasattr(e, 'code'):
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
    else:
        ID = response.read()
        link = "http://www.chesspastebin.com/?p=%s" % int(ID)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(link, -1)
        #print(text)
        #print(clipboard.wait_for_text())
        d = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK)
        msg = _("Game shared at ") + '<a href="%s">chesspastebin.com</a>' % link
        d.set_markup(msg)
        d.format_secondary_text(_("(Link is available on clipboard.)"))
        d.connect("response", lambda d,a: d.hide())
        d.show()
