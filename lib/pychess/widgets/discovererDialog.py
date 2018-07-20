import asyncio

from gi.repository import Gtk

from pychess.compat import create_task
from pychess.Utils import wait_signal
from pychess.System import uistuff


class DiscovererDialog:
    def __init__(self, discoverer):
        self.discoverer = discoverer
        self.widgets = uistuff.GladeWidgets("discovererDialog.glade")

        # =======================================================================
        # Clear glade defaults
        # =======================================================================
        for child in self.widgets["enginesTable"].get_children():
            self.widgets["enginesTable"].remove(child)

        self.finished = False
        self.throbber = None
        self.nameToBar = {}

        discoverer.pre_discover()
        binnames = self.discoverer.toBeRechecked.keys()
        if len(binnames) == 0:
            self.finished = True
        # ======================================================================
        # Insert the names to be discovered
        # ======================================================================
        for i, name in enumerate(binnames):
            label = Gtk.Label(label=name + ":")
            label.props.xalign = 1
            self.widgets["enginesTable"].attach(label, 0, 1, i, i + 1)
            bar = Gtk.ProgressBar()
            self.widgets["enginesTable"].attach(bar, 1, 2, i, i + 1)
            self.nameToBar[name] = bar

        # =======================================================================
        # Add throbber
        # =======================================================================

        self.throbber = Gtk.Spinner()
        self.throbber.set_size_request(50, 50)
        self.widgets["throbberDock"].add(self.throbber)

        # =======================================================================
        # Show the window
        # =======================================================================
        self.widgets["discovererDialog"].set_position(
            Gtk.WindowPosition.CENTER_ON_PARENT)
        self.widgets["discovererDialog"].show_all()
        self.throbber.start()

    @asyncio.coroutine
    def start(self):
        if self.finished:
            self.close()

        # let dialog window draw itself
        yield from asyncio.sleep(0.1)

        create_task(self.all_whatcher())
        create_task(self.discovered_whatcher())

        self.discoverer.discover()

    @asyncio.coroutine
    def discovered_whatcher(self):
        while True:
            if self.finished:
                return

            _discoverer, binname, _xmlenginevalue = yield from wait_signal(self.discoverer, "engine_discovered")

            if binname in self.nameToBar:
                bar = self.nameToBar[binname]
                bar.props.fraction = 1

    @asyncio.coroutine
    def all_whatcher(self):
        while True:
            yield from wait_signal(self.discoverer, "all_engines_discovered")
            break

        self.finished = True
        self.close()

    def close(self):
        if self.throbber:
            self.throbber.stop()
        self.widgets["discovererDialog"].hide()
