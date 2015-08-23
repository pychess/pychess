from __future__ import absolute_import

from threading import Lock
from gi.repository import GObject
from .Log import log


class Player (GObject.GObject):
    __gsignals__ = {
        'end': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'error': (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }
    def checkSound(self):
        self.emit("error", None)
    def play(self, uri):
        pass


try:
    from gi.repository import Gst
except ImportError as e:
    log.error("Unable to import gstreamer. All sound will be mute.\n%s" % e)
else:
    if not Gst.init_check(None):
        log.error("Unable to initialize gstreamer. All sound will be mute.")
    else:
        class Player (GObject.GObject):
            __gsignals__ = {
                'end': (GObject.SignalFlags.RUN_FIRST, None, ()),
                'error': (GObject.SignalFlags.RUN_FIRST, None, (object,))
            }
            
            def __init__(self):
                GObject.GObject.__init__(self)
                self.player = None#Gst.ElementFactory.make("playbin", "player")
                fakesink = Gst.ElementFactory.make("fakesink", "fakesink")
                self.player.set_property("video-sink", fakesink)
                bus = self.player.get_bus()
                bus.connect("message", self.onMessage)
            
            def onMessage(self, bus, message):
                if message.type == Gst.MessageType.ERROR:
                    # Sound seams sometimes to work, even though errors are dropped.
                    # Therefore we really can't do anything to test.
                    # self.emit("error", message)
                    self.player.set_state(Gst.State.NULL)
                    simpleMessage, advMessage = message.parse_error()
                    log.warning("Gstreamer error '%s': %s" % (simpleMessage, advMessage))
                    self._del()
                elif message.type == Gst.MessageType.EOS:
                    self.player.set_state(Gst.State.NULL)
                    self.emit("end")
                return True
            
            def play(self, uri):
                self.player.set_state(Gst.State.READY)
                self.player.set_property("uri", uri)
                self.player.set_state(Gst.State.PLAYING)
