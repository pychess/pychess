
from urllib import urlopen
from time import time, sleep
import gtk
import gobject
import thread
import pango

class PingLabel (gtk.Label):
    def __init__ (self):
        gtk.Label.__init__(self)
        thread.start_new(self.run, ())
        self.set_ellipsize(pango.ELLIPSIZE_END)
        
    def run (self):
        while True:
            t = time()
            try:
                urlopen("http://freechess.org")
                s = str(int(round((time()-t)*1000)))
            except IOError, e:
                s = e.args[1]
            gobject.idle_add(self.set_text, (s))
            sleep(5)
