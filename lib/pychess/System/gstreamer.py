from threading import Lock

#from gobject import GObject, SIGNAL_RUN_FIRST, TYPE_NONE
from gi.repository import GObject

from Log import log

try:
    import pygst   
    pygst.require('0.10')
    from gi.repository import Gst

except ImportError as e:
    log.error("Unable to import gstreamer. All sound will be mute.\n%s" % e)
    class Player (GObject.GObject):
        #__gsignals__ = {
        #    'end': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
        #    'error': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
        #}
        __gsignals__ = {
            'end': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
            'error': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,))
        }
        def checkSound(self):
            self.emit("error", None)
        def play(self, uri):
            pass

else:
    class Player (GObject.GObject):
        __gsignals__ = {
            'end': (SIGNAL_RUN_FIRST, TYPE_NONE, ()),
            'error': (SIGNAL_RUN_FIRST, TYPE_NONE, (object,))
        }
        
        def __init__(self):
            GObject.GObject.__init__(self)
            self.player = Gst.ElementFactory.make("playbin")
            self.player.get_bus().add_watch(self.onMessage)
        
        def onMessage(self, bus, message):
            if message.type == Gst.MessageType.ERROR:
                # Sound seams sometimes to work, even though errors are dropped.
                # Therefore we really can't do anything to test.
                # self.emit("error", message)
                simpleMessage, advMessage = message.parse_error()
                log.warning("Gstreamer error '%s': %s" % (simpleMessage, advMessage))
                self._del()
            elif message.type == Gst.MessageType.EOS:
                self.emit("end")
            return True
        
        def play(self, uri):
            self.player.set_state(Gst.State.READY)
            self.player.set_property("uri", uri)
            self.player.set_state(Gst.State.PLAYING)
        
        def _del (self):
            self.player.set_state(Gst.State.NULL)
