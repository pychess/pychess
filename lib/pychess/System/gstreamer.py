from threading import Lock
from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE
from Log import log

try:
    import pygst
    pygst.require('0.10')
    import gst

except ImportError, e:
    log.error("Unable to import gstreamer. All sound will be mute.\n%s" % e)
    class Player (GObject):
        __gsignals__ = {
            'end': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
            'error': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
        }
        def checkSound(self):
            self.emit("error", None)
        def play(self, uri):
            pass

else:
    class Player (GObject):
        __gsignals__ = {
            'end': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
            'error': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
        }
        
        def __init__(self):
            GObject.__init__(self)
            self.player = gst.element_factory_make("playbin")
            self.player.get_bus().add_watch(self.onMessage)
        
        def onMessage(self, bus, message):
            if message.type == gst.MESSAGE_ERROR:
                # Sound seams sometimes to work, even though errors are dropped.
                # Therefore we really can't do anything to test.
                # self.emit("error", message)
                simpleMessage, advMessage = message.parse_error()
                log.warn("Gstreamer error '%s': %s" % (simpleMessage, advMessage))
                self.__del__()
            elif message.type == gst.MESSAGE_EOS:
                self.emit("end")
            return True
        
        def play(self, uri):
            self.player.set_state(gst.STATE_READY)
            self.player.set_property("uri", uri)
            self.player.set_state(gst.STATE_PLAYING)
        
        def __del__ (self):
            self.player.set_state(gst.STATE_NULL)
