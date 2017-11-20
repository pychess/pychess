#!/usr/bin/python3
import os
import sys

try:
    import gi
except ImportError:
    print("ERROR: gst_player requires pygobject to be installed.")
    sys.exit(1)

from gi.repository import GLib

try:
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst
except (ImportError, ValueError) as err:
    print("ERROR: Unable to import gstreamer.\n%s" % err)
    sys.exit(1)

if not Gst.init_check(None):
    print("ERROR: Unable to initialize gstreamer.")
    sys.exit(1)

player = Gst.ElementFactory.make("playbin", "player")
if player is None:
    print('ERROR: Gst.ElementFactory.make("playbin", "player") failed')
    sys.exit(1)


def on_message(bus, message):
    if message.type == Gst.MessageType.ERROR:
        player.set_state(Gst.State.NULL)
        simpleMessage, advMessage = message.parse_error()
        print("Gstreamer error '%s': %s" % (simpleMessage, advMessage))
    elif message.type == Gst.MessageType.EOS:
        player.set_state(Gst.State.NULL)
    return True


fakesink = Gst.ElementFactory.make("fakesink", "fakesink")
player.set_property("video-sink", fakesink)
bus = player.get_bus()
bus.add_signal_watch()
bus.connect("message", on_message)


def play(loop):
    line = sys.stdin.readline().strip()
    if not line:
        loop.quit()
        return

    if os.path.isfile(line):
        player.set_state(Gst.State.NULL)
        player.set_property("uri", "file://" + line)
        player.set_state(Gst.State.PLAYING)
    else:
        print("file not found:", line)
        player.set_state(Gst.State.NULL)
    return True


loop = GLib.MainLoop()
GLib.idle_add(play, loop)
loop.run()
