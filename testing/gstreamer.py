import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from pychess.System import gstreamer


class _FakeBus:
    def __init__(self):
        self.watched = False
        self.callback = None

    def add_signal_watch(self):
        self.watched = True

    def connect(self, signal, callback):
        assert signal == "message"
        self.callback = callback


class _FakeElement:
    def __init__(self):
        self.properties = {}
        self.states = []
        self.bus = _FakeBus()

    def set_property(self, name, value):
        self.properties[name] = value

    def get_bus(self):
        return self.bus

    def set_state(self, state):
        self.states.append(state)
        return _FakeGst.StateChangeReturn.SUCCESS


class _FakeElementFactory:
    @staticmethod
    def make(kind, name):
        if kind == "playbin":
            _FakeGst.player = _FakeElement()
            return _FakeGst.player
        if kind == "fakesink":
            _FakeGst.fakesink = _FakeElement()
            return _FakeGst.fakesink
        raise AssertionError(kind)


class _FakeGst:
    class MessageType:
        ERROR = "error"
        EOS = "eos"

    class State:
        NULL = "null"
        PLAYING = "playing"

    class StateChangeReturn:
        SUCCESS = "success"
        FAILURE = "failure"

    ElementFactory = _FakeElementFactory
    init_args = None
    player = None
    fakesink = None

    @staticmethod
    def init_check(args):
        _FakeGst.init_args = args
        return True


class _FakeMessage:
    def __init__(self, message_type):
        self.type = message_type

    def parse_error(self):
        return RuntimeError("broken"), "debug details"


def _fake_gi_modules():
    gi = types.ModuleType("gi")
    repository = types.ModuleType("gi.repository")
    repository.Gst = _FakeGst
    gi.repository = repository
    gi.require_version = lambda *args: None
    return {
        "gi": gi,
        "gi.repository": repository,
    }


class GStreamerPlayerTestCase(unittest.TestCase):
    def tearDown(self):
        gstreamer._sound_player = None

    def test_get_player_is_lazy_singleton(self):
        sentinel = object()
        with (
            patch.dict(os.environ, {"PYCHESS_UNITTEST": ""}),
            patch.object(gstreamer.sys, "platform", "linux"),
            patch.object(gstreamer, "GstPlayer", return_value=sentinel) as gst_player,
        ):
            gstreamer._sound_player = None
            self.assertIs(gstreamer.get_player(), sentinel)
            self.assertIs(gstreamer.get_player(), sentinel)

        gst_player.assert_called_once_with()

    def test_unittest_mode_never_initializes_gstreamer(self):
        with (
            patch.dict(os.environ, {"PYCHESS_UNITTEST": "true"}),
            patch.object(gstreamer, "GstPlayer") as gst_player,
        ):
            gstreamer._sound_player = None
            player = gstreamer.get_player()

        self.assertIsInstance(player, gstreamer.Player)
        self.assertFalse(player.ready)
        gst_player.assert_not_called()

    def test_gstreamer_uses_gtk_glib_main_loop_bus_watch(self):
        _FakeGst.init_args = None
        with patch.dict(sys.modules, _fake_gi_modules()):
            player = gstreamer.GstPlayer()

        self.assertTrue(player.ready)
        self.assertEqual(_FakeGst.init_args, [])
        self.assertTrue(player.bus.watched)
        self.assertIsNotNone(player.bus.callback)
        self.assertIs(_FakeGst.player.properties["video-sink"], _FakeGst.fakesink)

    def test_play_sets_file_uri_and_starts_playback(self):
        with patch.dict(sys.modules, _fake_gi_modules()):
            player = gstreamer.GstPlayer()

        with tempfile.NamedTemporaryFile() as sound_file:
            uri = Path(sound_file.name).as_uri()
            player.play(uri)

            self.assertEqual(player.player.properties["uri"], uri)

        self.assertEqual(
            player.player.states[-2:],
            [_FakeGst.State.NULL, _FakeGst.State.PLAYING],
        )

    def test_bus_error_stops_playback(self):
        with patch.dict(sys.modules, _fake_gi_modules()):
            player = gstreamer.GstPlayer()

        with patch.object(gstreamer.log, "error") as log_error:
            result = player._on_message(
                player.bus,
                _FakeMessage(_FakeGst.MessageType.ERROR),
            )

        self.assertTrue(result)
        self.assertEqual(player.player.states[-1], _FakeGst.State.NULL)
        log_error.assert_called_once()
