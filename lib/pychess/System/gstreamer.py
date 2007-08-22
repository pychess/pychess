
from threading import Lock

import pygst
pygst.require('0.10')
import gst
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE

class Player (GObject):
    __gsignals__ = {'end': (SIGNAL_RUN_FIRST, TYPE_NONE, ())}
    
    def __init__(self):
        GObject.__init__(self)
        self.player = gst.element_factory_make("playbin")
        self.player.get_bus().add_watch(self.on_message)
    
    def on_message(self, bus, message):
        if message.type == gst.MESSAGE_ERROR:
            gsterror, message = message.parse_error()
            print message
        elif message.type == gst.MESSAGE_EOS:
            self.emit("end")
        return True
    
    def play(self, uri):
        self.player.set_state(gst.STATE_NULL)
        self.player.set_property("uri", uri)
        self.player.set_state(gst.STATE_PLAYING)

player = Player()
lock = Lock()
def playSound (uri):
    lock.acquire()
    try:
        player.play(uri)
    finally:
        lock.release()
