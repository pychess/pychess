from __future__ import print_function

from gi.repository import Gdk
from gi.repository import Gtk

from pychess.compat import Request, urlencode, urlopen, HTTPError, URLError

url = "http://www.chesspastebin.com/api/add/"
apikey = "a137d919b75c8766b082367610189358cfb1ba70"
pgn = "?"

values = {'apikey' : apikey,
          'pgn' : pgn,
          "name": "PyChess",
          'sandbox' : 'true' }

data = urlencode(values).encode('utf-8')
req = Request(url, data)
try:
    response = urlopen(req, timeout=10)
except URLError as e:
    if hasattr(e, 'reason'):
        print('We failed to reach a server.')
        print('Reason: ', e.reason)
    elif hasattr(e, 'code'):
        print('The server couldn\'t fulfill the request.')
        print('Error code: ', e.code)
else:
    ID = response.read()
    link = "http://www.chesspastebin.com/?p=%s" % int(ID)
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_text(link, -1)    
    print("Link was put on clipboard:", clipboard.wait_for_text())