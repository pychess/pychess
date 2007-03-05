from telnetlib import Telnet

IC_CONNECTED, IC_DISCONNECTED = range(2)

f = open("/home/thomas/ficslog", "w")
def log (data, header):
    f.write(data)
    f.flush()

client = None

def connect (host, port, username="guest", password=""):
    global client
    
    client = Telnet(host, port)
    
    log(client.read_until("login: "), host)
    print >> client, username
    
    if username != "guest":
        log(client.read_until("password: "), host)
        print >> client, password
        
    else:
        log(client.read_until("Press return"), host)
        print >> client
    
    # set seek 1
    
    log(client.read_until("Starting FICS session"), host)
    log(client.read_until("fics%"), host)
    
    for handler in connectHandlers:
        handler (client, IC_CONNECTED)
    
    while True:
        r = client.expect(regexps)
        log(r[2].replace("\r\n", "\n"), host)
        
        if r[0] < 0: break #EOF
        
        handler = handlers[r[0]]
        handler (client, r[1].groups())
    
    for handler in connectHandlers:
        # Give handlers a chance no discover that the connection is closed
        handler (client, IC_DISCONNECTED)

handlers = []
regexps = []
def expect (regexp, func):
    handlers.append(func)
    regexps.append(regexp)

connectHandlers = []
def connectStatus (func):
    connectHandlers.append(func)

types = "(blitz|lightning|standard)"
rated = "(rated|unrated)"
colors = "(?:\[(white|black)\]\s?)?"
ratings = "([\d\+\-]{1,4})"
names = "(\w+)(?:\(([CUHIFWM])\))?"
mf = "(?:([mf]{1,2})\s?)?"

from gobject import *

class GameListManager (GObject):
    
    __gsignals__ = {
        'addSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeSeek' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        'clearSeeks' : (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        
        'addGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removeGame' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,)),
        
        'addPlayer' : (SIGNAL_RUN_FIRST, TYPE_NONE, (object,)),
        'removePlayer' : (SIGNAL_RUN_FIRST, TYPE_NONE, (str,))
    }
    
    def __init__ (self):
        
        GObject.__init__(self)
        
        connectStatus (self.on_connection_change)
        
        ###
        
        expect ( "<sc>\n", self.on_seek_clear)
        
        expect ( "<s> (.*?)\n", self.on_seek_add)
        
        expect ( "<sr> (.*?)\n", self.on_seek_remove)
        
        ###
        
        expect ( "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(s|b|l)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d+):(\d+)\s*-\s*(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)" % (ratings, ratings), self.on_game_list)
        
        expect ( "{Game (\d+) \((\w+) vs\. (\w+)\) (.*?)}", self.on_game_addremove)
        
        ###
        
        expect ( "%s(\.| )%s\s+%s(\.| )%s\s+%s(\.| )%s" % (ratings, names, ratings, names, ratings, names), self.on_player_list)
        
        expect ( "%s is no longer available for matches." % names, self.on_player_remove)
        
        expect ( "%s Blitz \(%s\), Std \(%s\), Wild \(%s\), Light\(%s\), Bug\(%s\)\s+is now available for matches." % (names, ratings, ratings, ratings, ratings, ratings), self.on_player_add)
        
    ###
    
    def on_connection_change (self, client, signal):
        if signal == IC_CONNECTED:
            print >> client, "iset seekinfo 1"
            print >> client, "iset seekremove 1"
            print >> client, "set seek 1"
            
            print >> client, "set gin 1"
            print >> client, "games /sbl"
            
            print >> client, "who a"
            print >> client, "set availmax 0"
            print >> client, "set availmin 0"
            print >> client, "set availinfo 1"
    
    def on_seek_add (self, client, groups):
        parts = groups[0].split(" ")
        seek = {"gameno": parts[0]}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            if key == "rr":
                seek["rmin"], seek["rmax"] = value.split("-")
            elif key == "ti":
                seek["cp"] = int(value) & 2 # 0x2 - computer
            else: seek[key] = value
        
        self.emit("addSeek", seek)
    
    def on_seek_clear (self, client, groups):
        self.emit("clearSeeks")
    
    def on_seek_remove (self, client, groups):
        for key in groups[0].split(" "):
            if not key: continue
            self.emit("removeSeek", key)
    
    ###
    
    def on_game_list (self, client, groups):
        gameno, wr, wn, br, bn, private, type, rated, min, inc, wmin, wsec, bmin, bsec, wmat, bmat, color, movno = groups
        game = {"gameno":gameno, "wn":wn, "bn":bn}
        self.emit("addGame", game)
    
    def on_game_addremove (self, client, groups):
        gameno, wn, bn, comment = groups
        if "Creating" in comment:
            c, rated, type, m = comment.split()
            if not type in ("standard", "blitz", "lightning"):
                return
            game = {"gameno":gameno, "wn":wn, "bn":bn}
            self.emit("addGame", game)
        else:
            self.emit("removeGame", gameno)
    
    ###
    
    def on_player_list (self, client, groups):
        p0r, p0s, p0n, p0t, p1r, p1s, p1n, p1t, p2r, p2s, p2n, p2t = groups
        self.emit("addPlayer", {"r":p0r, "status":p0s, "name":p0n, "title":p0t})
        self.emit("addPlayer", {"r":p1r, "status":p1s, "name":p1n, "title":p1t})
        self.emit("addPlayer", {"r":p2r, "status":p2s, "name":p2n, "title":p2t})
    
    def on_player_remove (self, client, groups):
        name, title = groups
        self.emit("removePlayer", name)
    
    def on_player_add (self, client, groups):
        name, title, blitz, std, wild, light, bug = groups
        self.emit("addPlayer", \
            {"name":name, "title":title, "r":blitz, "status": " "})
    
import gtk
from Queue import Queue
from Queue import Empty as EmptyError
from time import sleep

if __name__ == "__main__":
    
    queue = Queue()
    
    tv = gtk.TreeView()
    store = gtk.ListStore(str, str, str)
    tv.set_model(store)
    tv.append_column(gtk.TreeViewColumn(
            "Name", gtk.CellRendererText(), text=0))
    tv.append_column(gtk.TreeViewColumn(
            "Rated", gtk.CellRendererText(), text=1))
    tv.append_column(gtk.TreeViewColumn(
            "Type", gtk.CellRendererText(), text=2))
    
    glm = GameListManager()
    seeks = {}
    
    def on_seek_add (manager, seek):
        def call ():
            ti = store.append ([ seek["w"], seek["r"], seek["tp"] ])
            seeks [seek["gameno"]] = ti
        queue.put(call)
    glm.connect("addSeek", on_seek_add)
    
    def on_seek_remove (manager, gameno):
        def call ():
            if not gameno in seeks:
                # We ignore removes we haven't added, as it seams fics sends a
                # lot of removes for games it has never told us about
                return
            ti = seeks [gameno]
            if not store.iter_is_valid(ti):
                return
            store.remove (ti)
            del seeks[gameno]
        queue.put(call)
    glm.connect("removeSeek", on_seek_remove)
    
    def on_seek_clear (manager):
        def call ():
            store.clear()
            seeks.clear()
        queue.put(call)
    glm.connect("clearSeeks", on_seek_clear)
    
    w = gtk.Window()
    w.connect("delete_event", gtk.main_quit)
    w.add(tv)
    w.show_all()
    
    ######
    
    gtv = gtk.TreeView()
    gstore = gtk.ListStore(str, str)
    gtv.set_model(gstore)
    gtv.append_column(gtk.TreeViewColumn(
            "White", gtk.CellRendererText(), text=0))
    gtv.append_column(gtk.TreeViewColumn(
            "Black", gtk.CellRendererText(), text=1))
    
    games = {}
    
    def on_game_add (manager, game):
        def call ():
            ti = gstore.append ([ game["wn"], game["bn"] ])
            games [game["gameno"]] = ti
        queue.put(call)
    glm.connect("addGame", on_game_add)
    
    def on_game_remove (manager, gameno):
        def call ():
            if not gameno in games:
                return
            ti = games [gameno]
            if not gstore.iter_is_valid(ti):
                return
            gstore.remove (ti)
            del games[gameno]
        queue.put(call)
    glm.connect("removeGame", on_game_remove)
    
    gw = gtk.Window()
    gw.connect("delete_event", gtk.main_quit)
    sw = gtk.ScrolledWindow()
    sw.add(gtv)
    gw.add(sw)
    gw.show_all()
    
    ######
    
    ptv = gtk.TreeView()
    pstore = gtk.ListStore(str, str)
    ptv.set_model(pstore)
    ptv.append_column(gtk.TreeViewColumn(
            "Name", gtk.CellRendererText(), text=0))
    ptv.append_column(gtk.TreeViewColumn(
            "Rating", gtk.CellRendererText(), text=1))
    
    players = {}
    
    def on_player_add (manager, player):
        def call ():
            ti = pstore.append ([ player["name"], player["r"] ])
            players [player["name"]] = ti
        queue.put(call)
    glm.connect("addPlayer", on_player_add)
    
    def on_player_remove (manager, name):
        def call ():
            if not name in players:
                return
            ti = players [name]
            if not pstore.iter_is_valid(ti):
                return
            pstore.remove (ti)
            del players[name]
        queue.put(call)
    glm.connect("removePlayer", on_player_remove)
    
    pw = gtk.Window()
    pw.connect("delete_event", gtk.main_quit)
    sw = gtk.ScrolledWindow()
    sw.add(ptv)
    pw.add(sw)
    pw.show_all()
    
    ######
    
    def executeQueue ():
        try:
            func = queue.get(block=False)
            func()
        except EmptyError:
            sleep(0.01) # Make sure we have no empty loops
        return True
    idle_add(executeQueue)
    
    import thread
    thread.start_new (connect, ("freechess.org", 5000, "guest"))
    #thread.start_new (connect, ("freechess.org", 5000, "Username", "password"))
    
    gtk.gdk.threads_init()
    gtk.main()
