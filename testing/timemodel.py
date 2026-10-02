import time
import unittest

from gi.repository import GLib

from pychess.Utils.TimeModel import TimeModel
from pychess.Utils.const import WHITE


def pump(seconds):
    """Run the default GLib main loop for a fixed wall clock time."""
    loop = GLib.MainLoop.new(None, False)
    GLib.timeout_add(int(seconds * 1000), loop.quit)
    loop.run()


class ZeroListenerTests(unittest.TestCase):
    """The zero listener fires once per flag and does not poll the clock."""

    def counting_model(self, secs):
        """A started model whose flag checks are recorded."""
        model = TimeModel(secs=secs, gain=0)
        checks = []
        real_checkzero = TimeModel._TimeModel__checkzero

        def spy(*args):
            checks.append(time.monotonic())
            return real_checkzero(model, *args)

        model._TimeModel__checkzero = spy
        model.start()
        # start() only sets the counter; the GUI marks the model as started
        # through tap(). getPlayerTime() needs both to count down.
        model.started = True
        model.counter = time.time()
        return model, checks

    def test_zero_reached_is_emitted_once(self):
        model, _checks = self.counting_model(1)
        events = []
        model.connect(
            "zero_reached", lambda m, color: events.append((color, time.monotonic()))
        )
        started_at = time.monotonic()
        model.emit("time_changed")

        pump(2.0)

        self.assertEqual(len(events), 1, "flag announced %d times" % len(events))
        color, when = events[0]
        self.assertEqual(color, WHITE)
        self.assertAlmostEqual(when - started_at, 1.0, delta=0.4)

    def test_no_busy_polling_while_time_remains(self):
        model, checks = self.counting_model(60)
        model.emit("time_changed")

        pump(1.0)

        # The old implementation re-checked every 10 ms, so this used to be
        # around 90 wakeups for a single second of a 60 s clock.
        self.assertLessEqual(len(checks), 3, "%d wakeups in one second" % len(checks))

    def test_flag_is_reannounced_when_time_comes_back(self):
        model, _checks = self.counting_model(1)
        events = []
        model.connect("zero_reached", lambda m, color: events.append(time.monotonic()))
        model.emit("time_changed")

        def give_time_back():
            model.updatePlayer(model.movingColor, 1)
            model.counter = time.time()
            return False

        GLib.timeout_add(1500, give_time_back)
        pump(3.0)

        self.assertEqual(len(events), 2, "got %d flag announcements" % len(events))
        # Time was handed back at 1.5 s, so the second flag falls one second
        # later -- roughly 1.5 s after the first one.
        gap = events[1] - events[0]
        self.assertTrue(1.0 < gap < 2.4, "re-announced after %.2fs" % gap)

    def test_end_cancels_the_pending_check(self):
        model, checks = self.counting_model(1)
        events = []
        model.connect("zero_reached", lambda m, color: events.append(color))

        model.end()
        pump(1.5)

        self.assertEqual(events, [])
        self.assertEqual(checks, [])
        self.assertIsNone(model.zero_listener_id)

    def test_no_check_is_armed_for_an_ended_model(self):
        model = TimeModel(secs=10, gain=0)
        model.ended = True
        model.emit("time_changed")
        self.assertIsNone(model.zero_listener_id)

    def test_pause_disarms_the_check_and_resume_rearms_it(self):
        model, checks = self.counting_model(1)
        model.emit("time_changed")
        self.assertIsNotNone(model.zero_listener_id)

        model.pause()
        self.assertIsNone(model.zero_listener_id, "paused clock still armed")

        # A paused clock is frozen, so it must never announce a flag.
        pump(1.5)
        self.assertEqual(checks, [])

        events = []
        model.connect("zero_reached", lambda m, color: events.append(color))
        model.resume()
        self.assertIsNotNone(model.zero_listener_id, "resumed clock not re-armed")
        pump(1.5)
        self.assertEqual(events, [WHITE])
