
from threading import Lock
from Queue import Queue

from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE
import pygst
pygst.require('0.10')
import gst

from Log import log

class Player (GObject):
    __gsignals__ = {
        'end': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        'error': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
    }
    
    def __init__(self):
        GObject.__init__(self)
        self.player = gst.element_factory_make("playbin")
        self.player.get_bus().add_watch(self.onMessage)
        self.playLock = Lock()
    
    def onMessage(self, bus, message):
        if message.type == gst.MESSAGE_ERROR:
            # Sound seams sometimes to work, even though errors are dropped.
            # Therefore we really can't do anything to test.
            # self.emit("error", message)
            simpleMessage, advMessage = message.parse_error()
            log.warn("Gstreamer error '%s': %s" % (simpleMessage, advMessage))
        elif message.type == gst.MESSAGE_EOS:
            self.emit("end")
        return True
    
    def checkSound(self):
        self.player.set_state(gst.STATE_PLAYING)
    
    def play(self, uri):
        self.playLock.acquire()
        try:
            self.player.set_state(gst.STATE_NULL)
            self.player.set_property("uri", uri)
            self.player.set_state(gst.STATE_PLAYING)
        finally:
            self.playLock.release()
