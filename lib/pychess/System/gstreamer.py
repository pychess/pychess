import os
import sys
from pathlib import Path
from urllib.request import url2pathname

from pychess.System.Log import log


class Player:
    def __init__(self):
        self.ready = False

    def play(self, uri):
        pass


class WinsoundPlayer(Player):
    def __init__(self):
        super().__init__()
        try:
            import winsound
        except ImportError:
            return
        self.winsound = winsound
        self.ready = True

    def play(self, uri):
        path = url2pathname(uri[5:])
        try:
            self.winsound.PlaySound(None, 0)
            self.winsound.PlaySound(
                path,
                self.winsound.SND_FILENAME | self.winsound.SND_ASYNC,
            )
        except RuntimeError:
            log.error("ERROR: RuntimeError while playing %s." % path)


class GstPlayer(Player):
    def __init__(self):
        super().__init__()

        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
        except (ImportError, ValueError) as err:
            log.error("ERROR: Unable to import GStreamer: %s" % err)
            return

        init_result = Gst.init_check([])
        if isinstance(init_result, tuple):
            init_ok = init_result[0]
        else:
            init_ok = init_result
        if not init_ok:
            log.error("ERROR: Unable to initialize GStreamer.")
            return

        player = Gst.ElementFactory.make("playbin", "player")
        if player is None:
            log.error('ERROR: Gst.ElementFactory.make("playbin", "player") failed')
            return

        fakesink = Gst.ElementFactory.make("fakesink", "fakesink")
        if fakesink is not None:
            player.set_property("video-sink", fakesink)

        bus = player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

        self.Gst = Gst
        self.player = player
        self.bus = bus
        self.ready = True

    def _on_message(self, bus, message):
        if message.type == self.Gst.MessageType.ERROR:
            self.player.set_state(self.Gst.State.NULL)
            simple_message, advanced_message = message.parse_error()
            log.error(
                "GStreamer error '%s': %s" % (simple_message, advanced_message)
            )
        elif message.type == self.Gst.MessageType.EOS:
            self.player.set_state(self.Gst.State.NULL)
        return True

    def play(self, uri):
        if not self.ready:
            return

        path = url2pathname(uri[5:])
        if not os.path.isfile(path):
            log.warning("Sound file not found: %s" % path)
            self.player.set_state(self.Gst.State.NULL)
            return

        self.player.set_state(self.Gst.State.NULL)
        self.player.set_property("uri", Path(path).absolute().as_uri())
        result = self.player.set_state(self.Gst.State.PLAYING)
        if result == self.Gst.StateChangeReturn.FAILURE:
            log.error("ERROR: GStreamer failed to play %s" % path)


_sound_player = None


def get_player():
    """Return the platform sound player, creating it only when first needed."""
    global _sound_player

    if _sound_player is None:
        if os.environ.get("PYCHESS_UNITTEST"):
            _sound_player = Player()
        elif sys.platform == "win32":
            _sound_player = WinsoundPlayer()
        else:
            _sound_player = GstPlayer()
    return _sound_player
