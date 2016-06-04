from __future__ import absolute_import

import sys

import gi

from .Log import log
from pychess.compat import url2pathname


class Player():
    def __init__(self):
        self.ready = False

    def play(self, uri):
        pass


sound_player = Player()

if sys.platform == "win32":
    import winsound

    class WinsoundPlayer(Player):
        def __init__(self):
            self.ready = True

        def play(self, uri):
            try:
                winsound.PlaySound(None, 0)
                winsound.PlaySound(
                    url2pathname(uri[5:]), winsound.SND_FILENAME | winsound.SND_ASYNC)
            except RuntimeError:
                log.error("ERROR: RuntimeError while playing %s." %
                          url2pathname(uri[5:]))

    sound_player = WinsoundPlayer()
else:
    try:
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except (ImportError, ValueError) as err:
            log.error(
                "ERROR: Unable to import gstreamer. All sound will be mute.\n%s" %
                err)
    else:
        if not Gst.init_check(None):
            log.error(
                "ERROR: Unable to initialize gstreamer. All sound will be mute.")
        else:

            class GstPlayer(Player):
                def __init__(self):
                    self.player = Gst.ElementFactory.make("playbin", "player")
                    if self.player is None:
                        log.error(
                            'ERROR: Gst.ElementFactory.make("playbin", "player") failed')
                    else:
                        self.ready = True
                        fakesink = Gst.ElementFactory.make("fakesink",
                                                           "fakesink")
                        self.player.set_property("video-sink", fakesink)
                        bus = self.player.get_bus()
                        bus.connect("message", self.onMessage)

                def onMessage(self, bus, message):
                    if message.type == Gst.MessageType.ERROR:
                        # Sound seams sometimes to work, even though errors are dropped.
                        # Therefore we really can't do anything to test.
                        self.player.set_state(Gst.State.NULL)
                        simpleMessage, advMessage = message.parse_error()
                        log.warning("Gstreamer error '%s': %s" %
                                    (simpleMessage, advMessage))
                    elif message.type == Gst.MessageType.EOS:
                        self.player.set_state(Gst.State.NULL)
                    return True

                def play(self, uri):
                    if self.player is not None:
                        self.player.set_state(Gst.State.READY)
                        self.player.set_property("uri", uri)
                        self.player.set_state(Gst.State.PLAYING)

            sound_player = GstPlayer()
