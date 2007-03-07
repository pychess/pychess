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
    }
    
    def __init__ (self):
        
        GObject.__init__(self)
        #self.seeks = {}
        
        connectStatus (self.on_connection_change)
        
        #expect ( '%s \(%s\) seeking (\d+) (\d+) %s %s %s\("play (\d+)" to respond\)' % (names, ratings, rated, types, mf), self.on_seek)
        
        #expect ( "(\d+)\s+%s\s+%s\s+(\d+)\s+(\d+)\s+%s\s+%s\s+%s\s+(\d{1,4})-(\d{1,4}) %s" % (ratings, names, rated, types, colors, mf), self.on_sought_line)
        
        expect ( "<sc>\n", self.on_seek_clear)
        
        expect ( "<s> (.*?)\n", self.on_seek_add)
        
        expect ( "<sr> (.*?)\n", self.on_seek_remove)
        
        expect ( "(\d+) %s (\w+)\s+%s (\w+)\s+\[(p| )(s|b|l)(u|r)\s*(\d+)\s+(\d+)\]\s*(\d+):(\d+)\s*-\s*(\d+):(\d+) \(\s*(\d+)-\s*(\d+)\) (W|B):\s*(\d+)" % (ratings, ratings), self.on_game_add)
        
        expect ( "{Game (\d+) (.*?)}", self.on_game_addremove)
        
        #expect ("\d+ ads displayed.", self.on_sought_end)
    
    ###
    
    def on_connection_change (self, client, signal):
        if signal == IC_CONNECTED:
            print >> client, "iset seekinfo 1"
            print >> client, "iset seekremove 1"
            print >> client, "set seek 1"
            
            print >> client, "set gin 1"
            print >> client, "games /sbl"
    
    #def on_seek (self, client, groups):
    #    name, title, rating, min, sec, rated, type, mf, game = groups
    #    print "%s with rating %s invites you to a %s %s game %s" % \
    #        (name, rating, rated, type, game)
    
    #def on_sought_line (self, client, groups):
    #    if groups[0] in self.seeks:
    #        return
    #    colmap = {None:"?", "white":"W", "black": "B"}
    #    seek = {
    #        "gameno": groups[0],
    #        "rt": groups[1] not in ("----", "++++") and groups[1] or "0",
    #       "w": groups[2],
    #       "cp": groups[3] and "C" in groups[3],
    #       "t": groups[4],
    #       "i": groups[5],
    #       "r": groups[6] == "rated" and "r" or "u",
    #       "tp": groups[7],
    #       "c": colmap[groups[8]],
    #       "rmin": groups[9],
    #       "rmax": groups[10]
    #   }
    #   self.seeks[groups[0]] = seek
    #   self.emit("addGame", seek)
    
    def on_seek_add (self, client, groups):
        parts = groups[0].split(" ")
        seek = {"gameno": parts[0]}
        for key, value in [p.split("=") for p in parts[1:] if p]:
            if key == "rr":
                seek["rmin"], seek["rmax"] = value.split("-")
            elif key == "ti":
                seek["cp"] = int(value) & 2 # 0x2 - computer
            else: seek[key] = value
        
        #if not parts[0] in self.seeks:
            #self.seeks[parts[0]] = seek
        self.emit("addSeek", seek)
    
    #def on_sought_end (self, client, groups):
    #    pass
    
    def on_seek_clear (self, client, groups):
        self.emit("clearSeeks")
        #self.seeks.clear()
        #print >> client, "sought"
    
    def on_seek_remove (self, client, groups):
        for key in groups[0].split(" "):
            if not key: continue
            #if not key in self.seeks: continue
            self.emit("removeSeek", key)
            #del self.seeks[key]
    
    def on_game_add (self, client, groups):
        gameno, wr, wn, br, bn, private, type, rated, wmin, winc, bmin, binc, wmat, bmat, color, movno = groups
        game = {"gameno":gameno, "wn":wn, "bn":bn}
        self.emit("addGame", game)
    
    ###

from threading import RLock

if __name__ == "__main__":
    
    import gtk
    tv = gtk.TreeView()
    store = gtk.ListStore(str, str, str)
    tv.set_model(store)
    tv.append_column(gtk.TreeViewColumn(
            "Name", gtk.CellRendererText(), text=0))
    tv.append_column(gtk.TreeViewColumn(
            "Rated", gtk.CellRendererText(), text=1))
    tv.append_column(gtk.TreeViewColumn(
            "Type", gtk.CellRendererText(), text=2))
    
    lock = RLock()
    
    glm = GameListManager()
    seeks = {}
    
    def on_seek_add (manager, seek):
        def idle ():
            #lock.acquire()
            ti = store.append ([ seek["w"], seek["r"], seek["tp"] ])
            seeks [seek["gameno"]] = ti
            #lock.release()
        idle_add(idle)
    glm.connect("addSeek", on_seek_add)
    
    def on_seek_remove (manager, gameno):
        if not gameno in seeks: return
        def idle ():
            #lock.acquire()
            if not gameno in seeks:
                keys = seeks.keys()
                keys.sort()
                print "CANNOT REMOVE", gameno, keys
                return
            ti = seeks [gameno]
            if not store.iter_is_valid(ti):
                keys = seeks.keys()
                keys.sort()
                print "CANNOT REMOVE", gameno, keys
                return
            store.remove (ti)
            del seeks[gameno]
            #lock.release()
        idle_add(idle)
    glm.connect("removeSeek", on_seek_remove)
    
    def on_seek_clear (manager):
        def idle ():
            #lock.acquire()
            store.clear()
            seeks.clear()
            #lock.release()
        idle_add(idle)
    glm.connect("clearSeeks", on_seek_clear)
    
    w = gtk.Window()
    w.add(tv)
    w.show_all()
    
    print "start_thread"
    
    import thread
    #thread.start_new (connect, ("freechess.org", 5000, "guest"))
    thread.start_new (connect, ("freechess.org", 5000, "Lobais", "1001010"))
    
    print "init"
    
    gtk.gdk.threads_init()
    print "gtk.main"
    gtk.main()
    print "/gtk.main"
    
