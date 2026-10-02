import unittest

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib

from pychess.System import conf
from pychess.Utils.TimeModel import TimeModel
from pychess.widgets.ChessClock import ChessClock


class ChessClockLifecycleTests(unittest.TestCase):
    """ChessClock must not outlive the game tab it belongs to.

    Its 100 ms repaint timer and its config listener both keep a reference to
    the widget, so without an explicit teardown a closed game stays alive.
    """

    def test_del_stops_the_repaint_timer(self):
        clock = ChessClock()
        try:
            model = TimeModel(secs=60, gain=0)
            clock.setModel(model)
            self.assertIsNotNone(clock.update_source_id)
            source_id = clock.update_source_id

            clock._del()

            self.assertIsNone(clock.update_source_id)
            context = GLib.main_context_default()
            if hasattr(context, "find_source_by_id"):
                self.assertIsNone(context.find_source_by_id(source_id))
        finally:
            clock._del()

    def test_del_removes_the_config_listener(self):
        listeners_before = len(conf.idkeyfuncs)

        clock = ChessClock()
        self.assertEqual(len(conf.idkeyfuncs), listeners_before + 1)

        clock._del()
        self.assertEqual(len(conf.idkeyfuncs), listeners_before)

    def test_del_disconnects_the_model(self):
        clock = ChessClock()
        model = TimeModel(secs=60, gain=0)
        clock.setModel(model)
        time_changed_cid = clock.time_changed_cid
        player_changed_cid = clock.player_changed_cid

        clock._del()

        self.assertFalse(model.handler_is_connected(time_changed_cid))
        self.assertFalse(model.handler_is_connected(player_changed_cid))
        self.assertIsNone(clock.model)

    def test_setting_a_model_twice_replaces_the_first_one(self):
        clock = ChessClock()
        try:
            first = TimeModel(secs=60, gain=0)
            clock.setModel(first)
            first_time_changed_cid = clock.time_changed_cid
            first_source_id = clock.update_source_id

            second = TimeModel(secs=60, gain=0)
            clock.setModel(second)

            self.assertFalse(first.handler_is_connected(first_time_changed_cid))
            self.assertNotEqual(clock.update_source_id, first_source_id)
            self.assertIs(clock.model, second)

            context = GLib.main_context_default()
            if hasattr(context, "find_source_by_id"):
                self.assertIsNone(context.find_source_by_id(first_source_id))
        finally:
            clock._del()

    def test_del_is_idempotent(self):
        clock = ChessClock()
        clock.setModel(TimeModel(secs=60, gain=0))
        clock._del()
        clock._del()
        self.assertIsNone(clock.update_source_id)
        self.assertIsNone(clock.model)
