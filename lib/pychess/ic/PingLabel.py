
from urllib import urlopen
from time import time, sleep
import gtk
import gobject
import thread

class PingLabel (gtk.Label):
    def __init__ (self):
        gtk.Label.__init__(self)
        thread.start_new(self.run, ())
    
    def run (self):
        while True:
            t = time()
            urlopen("http://freechess.org")
            gobject.idle_add(self.set_text, (str(int(round((time()-t)*1000)))))
            sleep(5)
