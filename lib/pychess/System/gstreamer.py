import io
import os
import sys
import subprocess
from urllib.request import url2pathname

from .Log import log


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
    class GstPlayer(Player):
        def __init__(self):
            PYTHONBIN = sys.executable.split("/")[-1]
            try:
                if getattr(sys, 'frozen', False):
                    gst_player = os.path.join(os.path.abspath(os.path.dirname(sys.executable)), "gst_player.py")
                else:
                    gst_player = os.path.join(os.path.abspath(os.path.dirname(__file__)), "gst_player.py")
                self.player = subprocess.Popen([PYTHONBIN, gst_player],
                                               stdin=subprocess.PIPE)

                self.stdin = io.TextIOWrapper(self.player.stdin, encoding='utf-8', line_buffering=True)
                self.ready = True
            except Exception:
                self.player = None
                log.error('ERROR: starting gst_player failed')
                raise

        def play(self, uri):
            if self.player is not None:
                try:
                    self.stdin.write(url2pathname(uri[5:]) + "\n")
                except BrokenPipeError:
                    pass

    sound_player = GstPlayer()
